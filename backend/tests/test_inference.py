"""Unit tests for the inference module."""
import pytest
from unittest.mock import patch, MagicMock
import numpy as np


def test_run_live_inference_returns_valid_probability():
    """Inference output must be in [0, 1]."""
    import torch
    import joblib

    mock_model = MagicMock()
    mock_model.return_value = torch.tensor([[0.65]])
    mock_scaler = MagicMock()
    mock_scaler.transform.return_value = np.array([[0.1, 0.2, 0.3, 0.4]], dtype=np.float32)

    with patch("inference.model", mock_model), \
         patch("inference.scaler", mock_scaler), \
         patch("inference.explainer", None):
        from inference import run_live_inference
        prob, shap_vals = run_live_inference(
            income=60000, loan_amount=200000, age=35, credit_score=650
        )

    assert 0.0 <= prob <= 1.0


def test_run_live_inference_returns_4_shap_values():
    import torch

    mock_model = MagicMock()
    mock_model.return_value = torch.tensor([[0.3]])
    mock_scaler = MagicMock()
    mock_scaler.transform.return_value = np.array([[0.1, 0.2, 0.3, 0.4]], dtype=np.float32)

    with patch("inference.model", mock_model), \
         patch("inference.scaler", mock_scaler), \
         patch("inference.explainer", None):
        from inference import run_live_inference
        prob, shap_vals = run_live_inference(60000, 200000, 35, 650)

    assert len(shap_vals) == 4


def test_run_live_inference_fallback_when_model_none():
    """Should return (0.5, [0,0,0,0]) when model not loaded."""
    with patch("inference.model", None), patch("inference.scaler", None):
        from inference import run_live_inference
        # Prevent load_ml_system from actually loading
        with patch("inference.load_ml_system"):
            prob, shap_vals = run_live_inference(60000, 200000, 35, 650)

    assert prob == 0.5
    assert shap_vals == [0.0, 0.0, 0.0, 0.0]


def test_uncertainty_returns_required_keys():
    import torch

    mock_model = MagicMock()
    mock_model.return_value = torch.tensor([[0.5]])
    mock_model.train = MagicMock()
    mock_model.eval = MagicMock()
    mock_scaler = MagicMock()
    mock_scaler.transform.return_value = np.array([[0.1, 0.2, 0.3, 0.4]], dtype=np.float32)

    with patch("inference.model", mock_model), \
         patch("inference.scaler", mock_scaler):
        from inference import run_inference_with_uncertainty
        result = run_inference_with_uncertainty(60000, 200000, 35, 650, n_samples=10)

    assert set(result.keys()) == {"mean", "std", "p5", "p95"}
    assert 0.0 <= result["mean"] <= 1.0
