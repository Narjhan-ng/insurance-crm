"""
Pytest configuration and shared fixtures.

This file provides reusable test fixtures for:
- Database sessions (in-memory SQLite)
- Test client (FastAPI)
- Mock data (prospects, users, quotes)
- Mock AI services (avoid real API calls)
"""
import os
import sys
from typing import Generator
from datetime import date, datetime, timedelta
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.database import Base, get_db
# from app.main import app  # Commented to avoid FastAPI/Pydantic version conflict
from app.models.user import User, UserRole
from app.models.prospect import Prospect, ProspectType, ProspectStatus, RiskCategory
from app.models.quote import Quote, QuoteStatus
from app.models.policy import Policy, PolicyStatus
from app.models.commission import Commission, CommissionType, CommissionStatus
from app.models.report import Report  # Fix SQLAlchemy relationship error
from app.services.auth_service import AuthService


# ============================================================================
# DATABASE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def test_engine():
    """
    Create an in-memory SQLite database for testing.

    WHY in-memory:
    - Fast (no disk I/O)
    - Isolated (each test gets fresh DB)
    - No cleanup needed (gone after test)
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,  # Single connection pool for SQLite
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)
    engine.dispose()


@pytest.fixture(scope="function")
def test_db(test_engine) -> Generator[Session, None, None]:
    """
    Create a database session for a single test.

    Usage:
        def test_something(test_db):
            user = User(username="test")
            test_db.add(user)
            test_db.commit()
    """
    TestingSessionLocal = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=test_engine
    )
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(scope="function")
def test_client(test_db: Session) -> Generator[TestClient, None, None]:
    """
    Create a FastAPI test client with overridden database dependency.

    Usage:
        def test_api(test_client):
            response = test_client.post("/api/v1/prospects/", json={...})
            assert response.status_code == 201
    """
    # Import here to avoid loading app at conftest import time
    from app.main import app

    def override_get_db():
        try:
            yield test_db
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


# ============================================================================
# USER FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def test_admin(test_db: Session) -> User:
    """Create a test admin user."""
    admin = User(
        username="admin_test",
        email="admin@test.com",
        password_hash=AuthService.get_password_hash("admin123"),
        role=UserRole.ADMIN,
        is_active=True
    )
    test_db.add(admin)
    test_db.commit()
    test_db.refresh(admin)
    return admin


@pytest.fixture(scope="function")
def test_manager(test_db: Session) -> User:
    """Create a test manager user."""
    manager = User(
        username="manager_test",
        email="manager@test.com",
        password_hash=AuthService.get_password_hash("manager123"),
        role=UserRole.MANAGER,
        is_active=True
    )
    test_db.add(manager)
    test_db.commit()
    test_db.refresh(manager)
    return manager


@pytest.fixture(scope="function")
def test_broker(test_db: Session, test_manager: User) -> User:
    """Create a test broker user."""
    broker = User(
        username="broker_test",
        email="broker@test.com",
        password_hash=AuthService.get_password_hash("broker123"),
        role=UserRole.BROKER,
        supervisor_id=test_manager.id,
        is_active=True
    )
    test_db.add(broker)
    test_db.commit()
    test_db.refresh(broker)
    return broker


@pytest.fixture(scope="function")
def test_auth_headers(test_broker: User) -> dict:
    """
    Create authentication headers for API requests.

    Usage:
        def test_protected_endpoint(test_client, test_auth_headers):
            response = test_client.get("/api/v1/prospects/", headers=test_auth_headers)
    """
    token = AuthService.create_access_token(data={
        "sub": test_broker.username,
        "user_id": test_broker.id,
        "role": test_broker.role.value
    })
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# PROSPECT FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def test_prospect(test_db: Session, test_broker: User) -> Prospect:
    """Create a test prospect."""
    prospect = Prospect(
        type=ProspectType.INDIVIDUAL,
        first_name="Mario",
        last_name="Rossi",
        birth_date=date(1980, 5, 15),  # Age 45 (good for testing)
        email="mario.rossi@example.com",
        phone="+39 340 1234567",
        tax_code="RSSMRA80E15H501Z",
        status=ProspectStatus.NEW,
        risk_category=RiskCategory.MEDIUM,
        assigned_broker=test_broker.id,
        created_by=test_broker.id,
        notes="Test prospect for unit tests"
    )
    test_db.add(prospect)
    test_db.commit()
    test_db.refresh(prospect)
    return prospect


@pytest.fixture(scope="function")
def test_high_risk_prospect(test_db: Session, test_broker: User) -> Prospect:
    """Create a high-risk prospect for edge case testing."""
    prospect = Prospect(
        type=ProspectType.INDIVIDUAL,
        first_name="Giovanni",
        last_name="Bianchi",
        birth_date=date(1950, 3, 20),  # Age 75 (high risk)
        email="giovanni.bianchi@example.com",
        phone="+39 340 9876543",
        tax_code="BNCGNN50C20H501W",
        status=ProspectStatus.NEW,
        risk_category=RiskCategory.HIGH,
        assigned_broker=test_broker.id,
        created_by=test_broker.id,
        notes="High risk prospect: diabetes, hypertension"
    )
    test_db.add(prospect)
    test_db.commit()
    test_db.refresh(prospect)
    return prospect


# ============================================================================
# QUOTE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def test_quote(test_db: Session, test_prospect: Prospect) -> Quote:
    """Create a test quote."""
    quote = Quote(
        prospect_id=test_prospect.id,
        provider="Generali",
        insurance_type="life",
        monthly_premium=Decimal("63.33"),
        annual_premium=Decimal("760.00"),
        coverage_amount=Decimal("250000.00"),
        deductible=Decimal("0.00"),
        status=QuoteStatus.SENT,
        valid_until=date.today() + timedelta(days=30),
        ai_score=Decimal("85.50"),
        ai_reasoning={
            "pros": ["Best price-to-coverage ratio", "Fast claim processing"],
            "cons": ["Limited online services"],
            "reasoning": "Best match for medium-risk profile"
        }
    )
    test_db.add(quote)
    test_db.commit()
    test_db.refresh(quote)
    return quote


# ============================================================================
# POLICY FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def test_policy(test_db: Session, test_quote: Quote) -> Policy:
    """Create a test policy."""
    policy = Policy(
        quote_id=test_quote.id,
        policy_number="POL-2025-TEST001",
        start_date=date.today(),
        end_date=date.today() + timedelta(days=365),
        renewal_date=date.today() + timedelta(days=335),
        status=PolicyStatus.ACTIVE,
        signed_at=datetime.now()
    )
    test_db.add(policy)

    # Update quote status
    test_quote.status = QuoteStatus.ACCEPTED

    test_db.commit()
    test_db.refresh(policy)
    return policy


# ============================================================================
# COMMISSION FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def test_commission(
    test_db: Session,
    test_prospect: Prospect,
    test_broker: User,
    test_manager: User
) -> Commission:
    """Create a test commission."""
    commission = Commission(
        prospect_id=test_prospect.id,
        broker_id=test_broker.id,
        manager_id=test_manager.id,
        commission_type=CommissionType.INITIAL,
        amount=Decimal("114.00"),  # 15% of 760
        percentage=Decimal("15.00"),
        base_amount=Decimal("760.00"),
        status=CommissionStatus.PENDING,
        period_year=2025,
        period_month=10
    )
    test_db.add(commission)
    test_db.commit()
    test_db.refresh(commission)
    return commission


# ============================================================================
# MOCK AI SERVICE FIXTURES
# ============================================================================

@pytest.fixture(scope="function")
def mock_langchain_response():
    """
    Mock response from LangChain AI service.

    Usage:
        def test_advisory(mock_langchain_response, monkeypatch):
            monkeypatch.setattr("app.services.advisory_service.ChatAnthropic", mock_langchain_response)
    """
    class MockLLM:
        def invoke(self, *args, **kwargs):
            return {
                "recommendations": [
                    {
                        "provider": "Generali",
                        "rank": 1,
                        "score": 85.5,
                        "pros": ["Best price", "Fast claims"],
                        "cons": ["Limited online"],
                        "key_features": ["Life coverage", "24/7 support"],
                        "reasoning": "Best for medium risk"
                    }
                ]
            }

        async def ainvoke(self, *args, **kwargs):
            return self.invoke(*args, **kwargs)

    return MockLLM()


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def create_test_prospect_data(override: dict = None) -> dict:
    """Helper to create valid prospect POST data."""
    data = {
        "type": "individual",
        "first_name": "Test",
        "last_name": "User",
        "birth_date": "1985-06-20",
        "email": "test.user@example.com",
        "phone": "+39 340 1111111",
        "tax_code": "TSTUSR85H20H501A",
        "risk_category": "low",
        "notes": "Test prospect"
    }
    if override:
        data.update(override)
    return data


def create_test_user_data(override: dict = None) -> dict:
    """Helper to create valid user registration data."""
    data = {
        "username": "testuser",
        "email": "testuser@example.com",
        "password": "testpass123",
        "role": "broker"
    }
    if override:
        data.update(override)
    return data
