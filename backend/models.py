from sqlalchemy import Column, Integer, String, Float, Text, ForeignKey, DateTime, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

try:
    from pgvector.sqlalchemy import Vector
    _pgvector_available = True
except ImportError:
    _pgvector_available = False

class Customer(Base):
    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    age = Column(Integer)
    income = Column(Float)
    loan_amount = Column(Float)
    employment_type = Column(String)
    credit_score = Column(Float)
    risk_tier = Column(String)
    default_probability = Column(Float)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    if _pgvector_available:
        embedding = Column(Vector(64), nullable=True)

    shap_values = relationship("SHAPValue", back_populates="customer", cascade="all, delete-orphan")

    __table_args__ = (
        Index('ix_customer_risk_tier', 'risk_tier'),
        Index('ix_customer_default_probability', 'default_probability'),
    )


class SHAPValue(Base):
    __tablename__ = "shap_values"

    id = Column(Integer, primary_key=True, index=True)
    customer_id = Column(Integer, ForeignKey("customers.id"), index=True)
    feature_name = Column(String)
    contribution = Column(Float)

    customer = relationship("Customer", back_populates="shap_values")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(String, default="analyst")
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
