from pydantic import BaseModel, Field
from typing import List, Optional

class SHAPValueBase(BaseModel):
    feature_name: str
    contribution: float

class CustomerBase(BaseModel):
    name: str
    age: int = Field(ge=18, le=100)
    income: float = Field(gt=0, le=10_000_000)
    loan_amount: float = Field(gt=0, le=50_000_000)
    employment_type: str
    credit_score: float = Field(ge=300, le=850)
    risk_tier: str
    default_probability: float = Field(ge=0.0, le=1.0)

class CustomerCreate(BaseModel):
    name: str
    age: int = Field(ge=18, le=100)
    income: float = Field(gt=0, le=10_000_000)
    loan_amount: float = Field(gt=0, le=50_000_000)
    employment_type: str = "Employed"
    credit_score: float = Field(ge=300, le=850)
    notes: Optional[str] = None

class Customer(CustomerBase):
    id: int
    notes: Optional[str] = None

    class Config:
        from_attributes = True

class CustomerDetail(Customer):
    shap_values: List[SHAPValueBase] = []

    class Config:
        from_attributes = True

class PredictionRequest(BaseModel):
    customer_id: int
    income: Optional[float] = Field(default=None, gt=0, le=10_000_000)
    loan_amount: Optional[float] = Field(default=None, gt=0, le=50_000_000)
    model_type: str = "neural_net"

class PredictionResponse(BaseModel):
    new_default_probability: float
    delta: float
    mock_shap_values: List[SHAPValueBase]
    confidence_lower: Optional[float] = None
    confidence_upper: Optional[float] = None
    model_type: str = "neural_net"

class ModelComparisonResponse(BaseModel):
    neural_net_probability: float
    xgboost_probability: Optional[float] = None
    ensemble_probability: Optional[float] = None
    mock_shap_values: List[SHAPValueBase]

class ChatRequest(BaseModel):
    customer_id: int
    query: str

class PortfolioAnalytics(BaseModel):
    risk_distribution: List[dict]
    income_histogram: List[dict]
    default_probability_distribution: List[dict]
    avg_default_probability: float
    total_customers: int
    high_risk_percentage: float


class LoginRequest(BaseModel):
    email: str
    password: str


class RegisterRequest(BaseModel):
    email: str
    password: str
    role: Optional[str] = "analyst"
