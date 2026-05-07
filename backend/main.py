import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import (
    Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from sqlalchemy import func, text
from sqlalchemy.orm import Session

import auth
import cache
import database
import metrics
import models
import schemas
from inference import (
    load_ml_system,
    run_live_inference,
    run_inference_with_uncertainty,
    extract_embedding,
)
from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Warm the ML model at startup so the first request isn't slow."""
    logger.info("CrediRisk API starting up...")
    models.Base.metadata.create_all(bind=database.engine)
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, load_ml_system)
    logger.info("CrediRisk API ready")
    yield
    logger.info("CrediRisk API shutting down")


app = FastAPI(title="CrediRisk API", version="2.0.0", lifespan=lifespan)

_allowed_origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Rate limiting (graceful degradation if slowapi not installed)
# ---------------------------------------------------------------------------
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.errors import RateLimitExceeded
    from slowapi.util import get_remote_address

    limiter = Limiter(key_func=get_remote_address)
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
    _LIMITER_AVAILABLE = True
except ImportError:
    _LIMITER_AVAILABLE = False
    limiter = None

# ---------------------------------------------------------------------------
# Sentry (graceful degradation)
# ---------------------------------------------------------------------------
_sentry_dsn = os.getenv("SENTRY_DSN", "")
if _sentry_dsn:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        sentry_sdk.init(dsn=_sentry_dsn, traces_sample_rate=0.1, integrations=[FastApiIntegration()])
        logger.info("Sentry error tracking enabled")
    except ImportError:
        logger.warning("sentry-sdk not installed; Sentry disabled")


# ---------------------------------------------------------------------------
# Helper: run inference off the event loop (CPU-bound)
# ---------------------------------------------------------------------------
async def _run_inference_async(income, loan_amount, age, credit_score):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, run_live_inference, income, loan_amount, age, credit_score)


async def _run_uncertainty_async(income, loan_amount, age, credit_score):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, run_inference_with_uncertainty, income, loan_amount, age, credit_score
    )


# ---------------------------------------------------------------------------
# Customer endpoints
# ---------------------------------------------------------------------------

@app.get("/customers", response_model=list[schemas.Customer])
def read_customers(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(database.get_db),
):
    return db.query(models.Customer).offset(skip).limit(limit).all()


@app.get("/customers/{customer_id}", response_model=schemas.CustomerDetail)
def read_customer(customer_id: int, db: Session = Depends(database.get_db)):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return customer


@app.post("/customers", response_model=schemas.CustomerDetail, status_code=201)
async def create_customer(
    payload: schemas.CustomerCreate,
    db: Session = Depends(database.get_db),
    _user=Depends(auth.get_current_user),
):
    prob, shap_vals = await _run_inference_async(
        income=payload.income,
        loan_amount=payload.loan_amount,
        age=float(payload.age),
        credit_score=payload.credit_score,
    )
    prob = max(0.0, min(1.0, prob))
    risk_tier = "High" if prob > 0.6 else "Medium" if prob > 0.3 else "Low"

    db_customer = models.Customer(
        name=payload.name,
        age=payload.age,
        income=payload.income,
        loan_amount=payload.loan_amount,
        employment_type=payload.employment_type,
        credit_score=payload.credit_score,
        risk_tier=risk_tier,
        default_probability=prob,
        notes=payload.notes,
    )
    db.add(db_customer)
    db.flush()

    feature_names = ["Income", "Loan Amount", "Age", "Credit Score"]
    for i, fname in enumerate(feature_names):
        db.add(models.SHAPValue(
            customer_id=db_customer.id,
            feature_name=fname,
            contribution=float(shap_vals[i]) if i < len(shap_vals) else 0.0,
        ))

    # Store embedding for similarity search
    try:
        emb = extract_embedding(payload.income, payload.loan_amount, float(payload.age), payload.credit_score)
        if emb is not None and hasattr(models.Customer, "embedding"):
            db_customer.embedding = emb.tolist()
    except Exception as e:
        logger.debug("Embedding extraction skipped: %s", e)

    db.commit()
    db.refresh(db_customer)
    logger.info("Created customer id=%d risk_tier=%s prob=%.3f", db_customer.id, risk_tier, prob)
    return db_customer


# ---------------------------------------------------------------------------
# Prediction endpoint (HTTP, cached, async)
# ---------------------------------------------------------------------------

@app.post("/predict/whatif")
async def predict_whatif(request: schemas.PredictionRequest, db: Session = Depends(database.get_db)):
    customer = db.query(models.Customer).filter(models.Customer.id == request.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    inc = request.income if request.income is not None else customer.income
    loan = request.loan_amount if request.loan_amount is not None else customer.loan_amount
    age = float(customer.age)
    cs = customer.credit_score

    cache_key = {"income": inc, "loan_amount": loan, "age": age, "credit_score": cs}
    cached = await cache.get_cached_prediction(cache_key)
    if cached:
        return cached

    t0 = time.perf_counter()
    try:
        if request.model_type == "uncertainty":
            unc = await _run_uncertainty_async(inc, loan, age, cs)
            prob = unc["mean"]
        else:
            prob, shap_vals_raw = await _run_inference_async(inc, loan, age, cs)

        elapsed = time.perf_counter() - t0
        metrics.prediction_latency_seconds.labels(model_type=request.model_type).observe(elapsed)
    except Exception as e:
        metrics.inference_errors_total.inc()
        logger.error("Inference failed: %s", e)
        raise HTTPException(status_code=500, detail="Inference error")

    prob = max(0.0, min(1.0, prob))
    risk_tier = "High" if prob > 0.6 else "Medium" if prob > 0.3 else "Low"

    shap_list = [
        {"feature_name": "Income", "contribution": float(shap_vals_raw[0])},
        {"feature_name": "Loan Amount", "contribution": float(shap_vals_raw[1])},
        {"feature_name": "Age", "contribution": float(shap_vals_raw[2])},
        {"feature_name": "Credit Score", "contribution": float(shap_vals_raw[3])},
    ] if request.model_type != "uncertainty" else []

    result = {
        "new_default_probability": prob,
        "delta": prob - customer.default_probability,
        "mock_shap_values": shap_list,
        "model_type": request.model_type,
    }
    if request.model_type == "uncertainty":
        result["confidence_lower"] = unc["p5"]
        result["confidence_upper"] = unc["p95"]

    await cache.set_cached_prediction(cache_key, result)
    metrics.prediction_requests_total.labels(model_type=request.model_type, risk_tier=risk_tier).inc()
    return result


# ---------------------------------------------------------------------------
# WebSocket: real-time predictions (replaces polling for the what-if sliders)
# ---------------------------------------------------------------------------

@app.websocket("/ws/predict/{customer_id}")
async def ws_predict(websocket: WebSocket, customer_id: int, db: Session = Depends(database.get_db)):
    await websocket.accept()
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        await websocket.close(code=1008)
        return

    logger.info("WebSocket connected for customer_id=%d", customer_id)
    try:
        while True:
            data = await websocket.receive_json()
            inc = float(data.get("income", customer.income))
            loan = float(data.get("loan_amount", customer.loan_amount))
            age = float(customer.age)
            cs = customer.credit_score

            cache_key = {"income": inc, "loan_amount": loan, "age": age, "credit_score": cs}
            result = await cache.get_cached_prediction(cache_key)

            if result is None:
                try:
                    prob, shap_vals_raw = await _run_inference_async(inc, loan, age, cs)
                    prob = max(0.0, min(1.0, prob))
                    result = {
                        "new_default_probability": prob,
                        "delta": prob - customer.default_probability,
                        "mock_shap_values": [
                            {"feature_name": "Income", "contribution": float(shap_vals_raw[0])},
                            {"feature_name": "Loan Amount", "contribution": float(shap_vals_raw[1])},
                            {"feature_name": "Age", "contribution": float(shap_vals_raw[2])},
                            {"feature_name": "Credit Score", "contribution": float(shap_vals_raw[3])},
                        ],
                    }
                    await cache.set_cached_prediction(cache_key, result)
                except Exception as e:
                    logger.error("WS inference error: %s", e)
                    await websocket.send_json({"error": "Inference failed"})
                    continue

            await websocket.send_json(result)

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for customer_id=%d", customer_id)


# ---------------------------------------------------------------------------
# Chat / GPT-4 explanation endpoint
# ---------------------------------------------------------------------------

@app.post("/chat")
def chat(request: schemas.ChatRequest, db: Session = Depends(database.get_db)):
    customer = db.query(models.Customer).filter(models.Customer.id == request.customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    metrics.chat_requests_total.inc()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return {"reply": (
            f"Based on analysis of {customer.name}: income ${customer.income:,.0f}, "
            f"loan ${customer.loan_amount:,.0f}, risk tier {customer.risk_tier} "
            f"({customer.default_probability*100:.1f}% default probability). "
            "The primary risk drivers are high loan-to-income ratio and credit score."
        )}

    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are a risk analyst explainability engine. Explain the customer's risk in clear, concise language for a loan officer."},
                {"role": "user", "content": (
                    f"Customer: {customer.name}, Age: {customer.age}, "
                    f"Income: ${customer.income:,.0f}, Loan: ${customer.loan_amount:,.0f}, "
                    f"Credit Score: {customer.credit_score:.0f}, "
                    f"Default Probability: {customer.default_probability*100:.1f}%, "
                    f"Risk Tier: {customer.risk_tier}. Query: {request.query}"
                )},
            ],
        )
        return {"reply": response.choices[0].message.content}
    except Exception as e:
        logger.error("OpenAI API error: %s", e)
        return {"reply": f"AI service temporarily unavailable. Base default probability: {customer.default_probability*100:.1f}%."}


# ---------------------------------------------------------------------------
# Similar customers (pgvector)
# ---------------------------------------------------------------------------

@app.get("/customers/{customer_id}/similar")
def similar_customers(
    customer_id: int,
    limit: int = Query(default=5, ge=1, le=20),
    db: Session = Depends(database.get_db),
):
    customer = db.query(models.Customer).filter(models.Customer.id == customer_id).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    try:
        emb = extract_embedding(customer.income, customer.loan_amount, float(customer.age), customer.credit_score)
        if emb is None:
            raise ValueError("Embedding unavailable")

        results = db.execute(
            text("SELECT id, name, risk_tier, default_probability FROM customers "
                 "WHERE id != :cid AND embedding IS NOT NULL "
                 "ORDER BY embedding <=> CAST(:emb AS vector) LIMIT :lim"),
            {"cid": customer_id, "emb": str(emb.tolist()), "lim": limit},
        ).fetchall()

        return [{"id": r.id, "name": r.name, "risk_tier": r.risk_tier, "default_probability": r.default_probability} for r in results]
    except Exception as e:
        logger.warning("Similarity search failed: %s", e)
        raise HTTPException(status_code=503, detail="Similarity search requires pgvector and embeddings to be populated.")


# ---------------------------------------------------------------------------
# Portfolio analytics
# ---------------------------------------------------------------------------

@app.get("/analytics/portfolio", response_model=schemas.PortfolioAnalytics)
def portfolio_analytics(db: Session = Depends(database.get_db)):
    total = db.query(func.count(models.Customer.id)).scalar() or 0
    avg_prob = db.query(func.avg(models.Customer.default_probability)).scalar() or 0.0

    risk_dist_rows = (
        db.query(models.Customer.risk_tier, func.count(models.Customer.id))
        .group_by(models.Customer.risk_tier)
        .all()
    )
    risk_distribution = [{"tier": r[0], "count": r[1]} for r in risk_dist_rows]

    high_risk_count = next((r["count"] for r in risk_distribution if r["tier"] == "High"), 0)
    high_risk_pct = high_risk_count / total if total else 0.0

    # Income histogram (5 buckets)
    income_buckets = [
        ("< $30k", 0, 30_000),
        ("$30k–$60k", 30_000, 60_000),
        ("$60k–$100k", 60_000, 100_000),
        ("$100k–$200k", 100_000, 200_000),
        ("> $200k", 200_000, 1e10),
    ]
    income_histogram = []
    for label, lo, hi in income_buckets:
        count = db.query(func.count(models.Customer.id)).filter(
            models.Customer.income >= lo, models.Customer.income < hi
        ).scalar() or 0
        income_histogram.append({"bucket": label, "count": count})

    # Default probability distribution (5 buckets)
    prob_buckets = [
        ("0–20%", 0.0, 0.2),
        ("20–40%", 0.2, 0.4),
        ("40–60%", 0.4, 0.6),
        ("60–80%", 0.6, 0.8),
        ("80–100%", 0.8, 1.01),
    ]
    prob_distribution = []
    for label, lo, hi in prob_buckets:
        count = db.query(func.count(models.Customer.id)).filter(
            models.Customer.default_probability >= lo, models.Customer.default_probability < hi
        ).scalar() or 0
        prob_distribution.append({"bucket": label, "count": count})

    return schemas.PortfolioAnalytics(
        risk_distribution=risk_distribution,
        income_histogram=income_histogram,
        default_probability_distribution=prob_distribution,
        avg_default_probability=float(avg_prob),
        total_customers=total,
        high_risk_percentage=float(high_risk_pct),
    )


# ---------------------------------------------------------------------------
# Auth endpoints
# ---------------------------------------------------------------------------

@app.post("/auth/login")
def login(
    form_data: schemas.LoginRequest,
    db: Session = Depends(database.get_db),
):
    user = db.query(models.User).filter(models.User.email == form_data.email).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth.create_access_token({"sub": user.email, "role": user.role, "id": user.id})
    return {"access_token": token, "token_type": "bearer"}


@app.post("/auth/register", status_code=201)
def register(
    payload: schemas.RegisterRequest,
    db: Session = Depends(database.get_db),
    _admin=Depends(auth.require_role("admin")),
):
    if db.query(models.User).filter(models.User.email == payload.email).first():
        raise HTTPException(status_code=409, detail="Email already registered")
    user = models.User(
        email=payload.email,
        hashed_password=auth.hash_password(payload.password),
        role=payload.role or "analyst",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"id": user.id, "email": user.email, "role": user.role}


@app.get("/auth/me")
def me(current_user=Depends(auth.get_current_user)):
    return current_user


# ---------------------------------------------------------------------------
# Observability
# ---------------------------------------------------------------------------

@app.get("/health")
def health_check(db: Session = Depends(database.get_db)):
    from inference import model as _model
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception as e:
        logger.error("Health check DB error: %s", e)

    return {
        "status": "ok" if db_ok else "degraded",
        "db": "ok" if db_ok else "error",
        "model": "ok" if _model is not None else "not_loaded",
    }


@app.get("/metrics")
def prometheus_metrics():
    if not metrics.PROMETHEUS_AVAILABLE:
        raise HTTPException(status_code=503, detail="prometheus_client not installed")
    return Response(metrics.generate_latest(), media_type=metrics.CONTENT_TYPE_LATEST)
