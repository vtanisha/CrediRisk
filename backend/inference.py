import logging
import warnings

import joblib
import numpy as np
import shap
import torch

from train_model import TabularDeepModel

warnings.filterwarnings('ignore')
logger = logging.getLogger(__name__)

model = None
scaler = None
explainer = None
background_tensor = None


def load_ml_system() -> None:
    global model, scaler, explainer, background_tensor
    if model is not None:
        return

    logger.info("Loading PyTorch ML system into memory...")
    try:
        model = TabularDeepModel(4, 1)
        model.load_state_dict(torch.load("models/model.pt", map_location="cpu", weights_only=True))
        model.eval()
        scaler = joblib.load("models/scaler.pkl")

        background = np.zeros((100, 4), dtype=np.float32)
        background_tensor = torch.tensor(background)
        try:
            explainer = shap.DeepExplainer(model, background_tensor)
        except Exception as e:
            logger.warning("SHAP DeepExplainer unavailable (%s); using gradient approximation", e)
            explainer = None

        logger.info("ML system loaded successfully")
    except Exception as e:
        logger.error("Failed to load ML models: %s", e)


def run_live_inference(income: float, loan_amount: float, age: float, credit_score: float):
    global model, scaler, explainer

    if model is None:
        load_ml_system()

    if model is None:
        logger.warning("Model unavailable; returning fallback prediction")
        return 0.5, [0.0, 0.0, 0.0, 0.0]

    # Normalise credit score to EXT_SOURCE_2 scale (same as train_model.py)
    ext_source_2 = credit_score / 850.0

    features = np.array([[income, loan_amount, age, ext_source_2]], dtype=np.float32)
    scaled_feats = scaler.transform(features)
    tensor_feats = torch.tensor(scaled_feats, dtype=torch.float32)

    with torch.no_grad():
        prob = model(tensor_feats).item()

    shap_vals = [0.0, 0.0, 0.0, 0.0]
    if explainer is not None:
        try:
            sv = explainer.shap_values(tensor_feats)
            if isinstance(sv, list):
                sv = sv[0]
            shap_vals = sv[0].tolist()
        except Exception as e:
            logger.debug("SHAP computation failed: %s", e)

    # Gradient-based fallback when SHAP produces near-zero values
    if sum(abs(v) for v in shap_vals) < 0.0001:
        t = torch.tensor(scaled_feats, dtype=torch.float32, requires_grad=True)
        out = model(t)
        out.backward()
        grads = t.grad[0].detach().numpy()
        shap_vals = (grads * scaled_feats[0]).tolist()

    return prob, shap_vals


def run_inference_with_uncertainty(
    income: float, loan_amount: float, age: float, credit_score: float, n_samples: int = 50
):
    """MC Dropout uncertainty estimation. Requires Dropout layers in the model."""
    global model, scaler

    if model is None:
        load_ml_system()
    if model is None:
        return {"mean": 0.5, "std": 0.0, "p5": 0.5, "p95": 0.5}

    ext_source_2 = credit_score / 850.0
    features = np.array([[income, loan_amount, age, ext_source_2]], dtype=np.float32)
    scaled_feats = scaler.transform(features)
    tensor_feats = torch.tensor(scaled_feats, dtype=torch.float32)

    # Enable dropout for MC sampling
    model.train()
    try:
        samples = []
        with torch.no_grad():
            for _ in range(n_samples):
                p = model(tensor_feats).item()
                samples.append(p)
    finally:
        model.eval()

    arr = np.array(samples)
    return {
        "mean": float(arr.mean()),
        "std": float(arr.std()),
        "p5": float(np.percentile(arr, 5)),
        "p95": float(np.percentile(arr, 95)),
    }


def extract_embedding(income: float, loan_amount: float, age: float, credit_score: float):
    """Return the 64-dim penultimate layer activations for pgvector storage."""
    global model, scaler

    if model is None:
        load_ml_system()
    if model is None:
        return None

    ext_source_2 = credit_score / 850.0
    features = np.array([[income, loan_amount, age, ext_source_2]], dtype=np.float32)
    scaled_feats = scaler.transform(features)
    tensor_feats = torch.tensor(scaled_feats, dtype=torch.float32)

    activations = {}

    def hook(module, input, output):
        activations["penultimate"] = output.detach().numpy()[0]

    # Register hook on the second-to-last Linear layer (index 2 in the Sequential)
    handle = model.net[2].register_forward_hook(hook)
    try:
        with torch.no_grad():
            model(tensor_feats)
    finally:
        handle.remove()

    return activations.get("penultimate")
