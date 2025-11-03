# Testing Guide - Insurance CRM

**Status**: Testing Infrastructure Complete, Tests In Progress
**Date**: November 3, 2025
**Coverage**: 37% (eligibility service)

---

## ✅ What We Completed Today

### 1. Testing Infrastructure (100% Complete)

Created professional testing setup:

#### **`tests/conftest.py`** (366 lines)
Complete pytest configuration with:
- **In-memory SQLite database** - Fast, isolated test DB
- **Test fixtures** for all models:
  - `test_admin`, `test_manager`, `test_broker` - User fixtures
  - `test_prospect`, `test_high_risk_prospect` - Prospect fixtures
  - `test_quote`, `test_policy`, `test_commission` - Business entity fixtures
- **Mock AI services** - Avoid real API costs
- **Helper functions** - `create_test_prospect_data()`, `create_test_user_data()`

#### **Dependencies Installed**
```bash
pytest==7.4.3           # Test framework
pytest-asyncio==0.21.1  # Async test support
pytest-mock==3.15.1     # Mocking library
pytest-cov==7.0.0       # Coverage reporting
httpx==0.25.2           # API testing (already installed)
```

### 2. Test Files Created

#### **`test_services_eligibility.py`** (360 lines)
Comprehensive eligibility service tests:
- 12 tests covering business logic
- Age-based eligibility rules
- Risk category effects
- Coverage amount scaling
- Edge cases (minors, elderly)

**Status**: Schema mismatch (written before reading actual API)

#### **`test_simple_eligibility.py`** (160 lines)
Simplified tests without heavy fixtures:
- 10 tests, 2 PASSING ✅
- Focus: EligibilityProvider model
- No database dependencies

#### **`test_eligibility_working.py`** (320 lines)
Corrected tests aligned with real API:
- 12 tests covering same scenarios
- Fixed to match actual `EligibilityService` API
- Uses mock prospects (no DB needed)

**Status**: API signature mismatch discovered

---

## 📊 Current Test Coverage

### **Eligibility Service Coverage: 37%**

```
Name                                  Stmts   Miss  Cover   Missing
-------------------------------------------------------------------
app/services/eligibility_service.py      68     43    37%   36, 210-211, 241-320, 344-345, 367-377
```

**What's covered** (37%):
- ✅ EligibilityProvider model creation
- ✅ Basic object instantiation

**What's NOT covered** (63%):
- ❌ `check_eligibility()` - Main business logic (lines 241-320)
- ❌ `get_best_provider()` - Selection logic
- ❌ Provider-specific rules

**Goal**: 80%+ coverage (industry standard)

---

## 🔧 Issues Discovered

### Issue #1: API Signature Mismatch

**Expected** (based on documentation):
```python
EligibilityService.check_eligibility(
    prospect=prospect,
    insurance_type="life",
    coverage_amount=Decimal("250000")  # ❌ Not accepted
)
```

**Actual** (from code):
```python
EligibilityService.check_eligibility(
    prospect: Prospect,
    insurance_type: str,
    db: Session = None  # ✅ Correct signature
)
```

**Fix needed**: Update all tests to remove `coverage_amount` parameter.

### Issue #2: SQLAlchemy Relationship Errors

**Problem**: `User` model references `Report` model which isn't imported.

**Error**:
```
sqlalchemy.exc.InvalidRequestError: When initializing mapper Mapper[User(users)],
expression 'Report' failed to locate a name ('Report').
```

**Fix applied**: Added `from app.models.report import Report` to conftest.py ✅

### Issue #3: FastAPI/Pydantic Version Conflict

**Problem**: Pydantic 2.5.0 incompatible with FastAPI 0.104.1

**Error**:
```
AttributeError: 'FieldInfo' object has no attribute 'in_'
```

**Workaround**: Lazy import of `app.main` in fixtures
**Long-term fix**: Upgrade FastAPI (requires internet connection)

---

## 🎯 Next Steps to Complete Testing

### Priority 1: Fix Existing Tests (30 min)

**Action**: Update `test_eligibility_working.py` to match real API

1. Remove `coverage_amount` from all `check_eligibility()` calls
2. Verify test expectations match actual behavior
3. Run: `pytest tests/test_eligibility_working.py -v`

**Expected outcome**: 10-12 tests passing, coverage → 70%+

### Priority 2: Commission Service Tests (45 min)

Create `tests/test_services_commission.py`:
```python
def test_calculate_initial_commission_broker_15_percent():
    """Test: Broker gets 15% on initial policy."""
    policy = create_test_policy(annual_premium=Decimal("1000.00"))

    commissions = CommissionService.calculate_initial_commissions(
        policy=policy,
        broker=test_broker,
        manager=test_manager
    )

    broker_comm = next(c for c in commissions if c.broker_id == test_broker.id)
    assert broker_comm.amount == Decimal("150.00")  # 15%
    assert broker_comm.percentage == Decimal("15.00")
```

**Tests to write**:
- Initial commission calculation (15%)
- Manager override (5%)
- Affiliate commission (3%)
- Renewal year 1 (10%)
- Recurring renewals (5%)
- Multi-tier structure

### Priority 3: Integration Tests (1 hour)

Create `tests/test_api_prospects.py`:
```python
def test_create_prospect_returns_201(test_client, test_auth_headers):
    """Test: POST /prospects creates new prospect."""
    data = {
        "type": "individual",
        "first_name": "Mario",
        "last_name": "Rossi",
        "birth_date": "1980-05-15",
        "email": "mario@example.com",
        "risk_category": "medium"
    }

    response = test_client.post(
        "/api/v1/prospects/",
        json=data,
        headers=test_auth_headers
    )

    assert response.status_code == 201
    assert response.json()["first_name"] == "Mario"
```

**Endpoints to test**:
- POST /prospects/ (create)
- GET /prospects/ (list)
- GET /prospects/{id} (detail)
- POST /eligibility/check
- POST /advisory/generate (AI)

### Priority 4: Event Handler Tests (45 min)

Create `tests/test_handlers_policy.py`:
```python
@pytest.mark.asyncio
async def test_policy_creation_handler_idempotency():
    """Test: Handler doesn't create duplicate policies."""
    event = QuoteAcceptedEvent(quote_id=1, ...)
    handler = PolicyCreationHandler()

    # First call
    await handler.handle(event)
    policies = db.query(Policy).filter_by(quote_id=1).all()
    assert len(policies) == 1

    # Second call (idempotent)
    await handler.handle(event)
    policies = db.query(Policy).filter_by(quote_id=1).all()
    assert len(policies) == 1  # Still 1!
```

**Critical tests**:
- Idempotency (can process event twice safely)
- Retry logic (failures don't corrupt state)
- Event publishing (new events created correctly)

### Priority 5: LangGraph Advisory Tests (1 hour)

Create `tests/test_services_advisory.py`:
```python
@pytest.mark.asyncio
async def test_advisory_workflow_complete(mock_claude_api):
    """Test: Complete advisory workflow executes all nodes."""

    with patch('langchain_anthropic.ChatAnthropic', return_value=mock_claude_api):
        result = await AdvisoryService.generate_advisory(
            prospect=test_prospect,
            insurance_type="life"
        )

    # Check workflow executed all nodes
    assert "profile_extractor" in result["workflow_path"]
    assert "eligibility_checker" in result["workflow_path"]
    assert "risk_analyzer" in result["workflow_path"]

    # Check structured output
    assert result["recommendations"] is not None
    assert len(result["recommendations"]) >= 1
```

**Tests to write**:
- Complete workflow execution
- Conditional routing (eligible vs ineligible paths)
- Node-level testing (each node independently)
- Mock AI responses (avoid API costs)
- Error handling in workflow

---

## 📈 Coverage Goals

### Target Coverage by Module

| Module | Current | Target | Priority |
|--------|---------|--------|----------|
| `eligibility_service.py` | 37% | 80% | HIGH |
| `commission_service.py` | 0% | 75% | HIGH |
| `advisory_service.py` | 0% | 70% | MEDIUM |
| `auth_service.py` | 0% | 85% | MEDIUM |
| `pdf_service.py` | 0% | 60% | LOW |
| **Overall** | **~15%** | **75%+** | - |

---

## 🛠️ Running Tests

### Run all tests
```bash
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_eligibility_working.py -v
```

### Run with coverage
```bash
pytest tests/ --cov=app --cov-report=html
# Open htmlcov/index.html to see detailed coverage
```

### Run only passing tests
```bash
pytest tests/test_simple_eligibility.py::TestEligibilityBasics -v
```

### Run with short traceback
```bash
pytest tests/ -v --tb=short
```

---

## 💡 Testing Best Practices Applied

### 1. **Test Pyramid**
```
        /\
       /E2E\      ← Few (manual for now)
      /------\
     /  API   \   ← Some (integration tests)
    /----------\
   /   Unit     \ ← Many (service tests)
  /--------------\
```

### 2. **AAA Pattern** (Arrange-Act-Assert)
```python
def test_example():
    # Arrange: Set up test data
    prospect = create_mock_prospect(age=45, risk=RiskCategory.MEDIUM)

    # Act: Execute the code under test
    results = EligibilityService.check_eligibility(prospect, "life")

    # Assert: Verify the outcome
    assert len(results) == 4
```

### 3. **Test Naming Convention**
```
test_<what>_<condition>_<expected_result>

Examples:
- test_medium_risk_middle_age_multiple_providers
- test_below_minimum_age_all_rejected
- test_calculate_initial_commission_broker_15_percent
```

### 4. **Fixtures for Reusability**
Instead of creating test data in every test, use fixtures:
```python
def test_something(test_prospect, test_broker):
    # test_prospect and test_broker are ready to use!
    assert test_prospect.assigned_broker == test_broker.id
```

### 5. **Mock External Dependencies**
```python
@patch('langchain_anthropic.ChatAnthropic')
def test_advisory_without_real_api(mock_claude):
    mock_claude.return_value.invoke.return_value = fake_response
    # Now test runs without calling real Claude API (no cost!)
```

---

## 🎓 What We Learned

### Issue #1: Documentation vs Reality
**Problem**: Tests written based on assumptions failed because actual API was different.

**Lesson**: Always read the actual code before writing tests. Documentation can be outdated.

**Solution**:
1. Read service file first: `app/services/eligibility_service.py`
2. Check method signatures: `def check_eligibility(...)`
3. Write tests matching reality

### Issue #2: SQLAlchemy Relationships
**Problem**: Creating `Prospect` object triggered SQLAlchemy to configure ALL models, including `User → Report` relationship.

**Lesson**: In testing, import order matters. Import all related models in conftest.py.

**Solution**: Added `from app.models.report import Report` to conftest.py

### Issue #3: Version Compatibility
**Problem**: Pydantic 2.5.0 + FastAPI 0.104.1 = incompatibility

**Lesson**: AI library ecosystems move fast. Pin versions and test upgrades.

**Workaround**: Lazy import of `app.main` to delay FastAPI initialization

---

## 📚 Resources

### Pytest Documentation
- Official docs: https://docs.pytest.org/
- Fixtures: https://docs.pytest.org/en/latest/explanation/fixtures.html
- Parametrize: https://docs.pytest.org/en/latest/how-to/parametrize.html

### Coverage
- pytest-cov: https://pytest-cov.readthedocs.io/
- Coverage.py: https://coverage.readthedocs.io/

### Mocking
- unittest.mock: https://docs.python.org/3/library/unittest.mock.html
- pytest-mock: https://pytest-mock.readthedocs.io/

### FastAPI Testing
- Testing guide: https://fastapi.tiangolo.com/tutorial/testing/
- TestClient: https://fastapi.tiangolo.com/advanced/testing-dependencies/

---

## 🎯 Success Criteria

Testing is complete when:
- ✅ Coverage ≥ 75% for core services
- ✅ All critical business logic tested
- ✅ API endpoints have integration tests
- ✅ Event handlers tested for idempotency
- ✅ LangGraph workflow tested with mocks
- ✅ CI/CD pipeline runs tests automatically

---

**Current Status**:
- Infrastructure: ✅ Complete
- Unit Tests: 🟡 In Progress (2 passing, learning API)
- Integration Tests: ⏳ Pending
- Coverage: 🔴 37% → Target 75%

**Next Session**: Fix eligibility tests, then write commission tests.
