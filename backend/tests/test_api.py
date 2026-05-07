"""Integration tests for FastAPI endpoints."""
import pytest


def test_health_check(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "db" in data
    assert "model" in data


def test_get_customers_returns_list(client, sample_customer):
    resp = client.get("/customers")
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)
    assert any(c["id"] == sample_customer.id for c in resp.json())


def test_get_customers_pagination(client):
    resp = client.get("/customers?skip=0&limit=5")
    assert resp.status_code == 200
    assert len(resp.json()) <= 5


def test_get_customer_found(client, sample_customer):
    resp = client.get(f"/customers/{sample_customer.id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["id"] == sample_customer.id
    assert data["name"] == "Test User"


def test_get_customer_not_found(client):
    resp = client.get("/customers/99999")
    assert resp.status_code == 404


def test_predict_whatif_valid(client, sample_customer):
    resp = client.post("/predict/whatif", json={
        "customer_id": sample_customer.id,
        "income": 80000.0,
        "loan_amount": 300000.0,
    })
    assert resp.status_code == 200
    data = resp.json()
    assert 0.0 <= data["new_default_probability"] <= 1.0
    assert "delta" in data
    assert "mock_shap_values" in data
    assert len(data["mock_shap_values"]) == 4


def test_predict_whatif_customer_not_found(client):
    resp = client.post("/predict/whatif", json={"customer_id": 99999})
    assert resp.status_code == 404


def test_predict_whatif_invalid_income_rejected(client, sample_customer):
    resp = client.post("/predict/whatif", json={
        "customer_id": sample_customer.id,
        "income": -1000.0,
    })
    assert resp.status_code == 422


def test_predict_whatif_income_too_large_rejected(client, sample_customer):
    resp = client.post("/predict/whatif", json={
        "customer_id": sample_customer.id,
        "income": 999_999_999.0,
    })
    assert resp.status_code == 422


def test_chat_no_api_key(client, sample_customer):
    resp = client.post("/chat", json={
        "customer_id": sample_customer.id,
        "query": "Explain the risk for this customer",
    })
    assert resp.status_code == 200
    assert "reply" in resp.json()


def test_chat_customer_not_found(client):
    resp = client.post("/chat", json={"customer_id": 99999, "query": "test"})
    assert resp.status_code == 404


def test_portfolio_analytics(client, sample_customer):
    resp = client.get("/analytics/portfolio")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_customers" in data
    assert "avg_default_probability" in data
    assert "risk_distribution" in data
    assert data["total_customers"] >= 1
