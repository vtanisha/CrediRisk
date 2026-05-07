"""Shared pytest fixtures."""
import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("SECRET_KEY", "test_secret_key_for_pytest")
os.environ.setdefault("ALLOWED_ORIGINS", "http://localhost:3000")
os.environ.setdefault("DATABASE_URL", "sqlite:///./test.db")

import database
import models

# In-memory SQLite for tests
TEST_DB_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DB_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture(scope="session", autouse=True)
def setup_db():
    """Create tables once for the whole test session."""
    models.Base.metadata.create_all(bind=engine)
    yield
    models.Base.metadata.drop_all(bind=engine)


@pytest.fixture()
def db_session():
    db = TestingSessionLocal()
    yield db
    db.close()


@pytest.fixture()
def sample_customer(db_session):
    customer = models.Customer(
        name="Test User",
        age=35,
        income=60000.0,
        loan_amount=200000.0,
        employment_type="Employed",
        credit_score=650.0,
        risk_tier="Medium",
        default_probability=0.45,
    )
    db_session.add(customer)
    db_session.commit()
    db_session.refresh(customer)
    yield customer
    db_session.delete(customer)
    db_session.commit()


@pytest.fixture()
def client(sample_customer):
    """TestClient with DB overridden and inference mocked."""
    from main import app
    app.dependency_overrides[database.get_db] = override_get_db

    mock_prob = 0.42
    mock_shap = [0.1, -0.05, 0.08, -0.12]

    with patch("main.load_ml_system"), \
         patch("main.run_live_inference", return_value=(mock_prob, mock_shap)), \
         patch("main._run_inference_async", return_value=(mock_prob, mock_shap)):
        with TestClient(app) as c:
            yield c

    app.dependency_overrides.clear()
