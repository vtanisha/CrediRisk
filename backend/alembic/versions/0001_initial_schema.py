"""Initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-07

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'customers',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(), nullable=True),
        sa.Column('age', sa.Integer(), nullable=True),
        sa.Column('income', sa.Float(), nullable=True),
        sa.Column('loan_amount', sa.Float(), nullable=True),
        sa.Column('employment_type', sa.String(), nullable=True),
        sa.Column('credit_score', sa.Float(), nullable=True),
        sa.Column('risk_tier', sa.String(), nullable=True),
        sa.Column('default_probability', sa.Float(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), onupdate=sa.func.now()),
    )
    op.create_index('ix_customers_id', 'customers', ['id'], unique=True)
    op.create_index('ix_customers_name', 'customers', ['name'])
    op.create_index('ix_customer_risk_tier', 'customers', ['risk_tier'])
    op.create_index('ix_customer_default_probability', 'customers', ['default_probability'])

    op.create_table(
        'shap_values',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('customer_id', sa.Integer(), sa.ForeignKey('customers.id'), nullable=True),
        sa.Column('feature_name', sa.String(), nullable=True),
        sa.Column('contribution', sa.Float(), nullable=True),
    )
    op.create_index('ix_shap_values_id', 'shap_values', ['id'], unique=True)
    op.create_index('ix_shap_values_customer_id', 'shap_values', ['customer_id'])

    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('hashed_password', sa.String(), nullable=False),
        sa.Column('role', sa.String(), server_default='analyst'),
        sa.Column('is_active', sa.Integer(), server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index('ix_users_id', 'users', ['id'], unique=True)
    op.create_index('ix_users_email', 'users', ['email'], unique=True)


def downgrade() -> None:
    op.drop_table('users')
    op.drop_table('shap_values')
    op.drop_table('customers')
