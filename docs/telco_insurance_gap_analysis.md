# 🔍 Telco CRM → Insurance CRM: Gap Analysis & Implementation Plan

**Date**: October 23, 2025
**Purpose**: Achieve feature parity between Telco CRM (parent project) and Insurance CRM
**Goal**: Create two parallel, equivalent portfolio projects

---

## 📊 Current State Summary

### Telco CRM (Parent Project)
- **15 Modules** fully implemented
- **Production-ready** with multi-tier commission system
- **PHP-based** with custom MVC framework
- **Dual database** architecture (crm + coverage)
- **Complete business flow** from lead to commission

### Insurance CRM (Current State)
- **3-4 Core Modules** implemented (Prospects, Quotes, Policies, partial Commissions)
- **Event-driven architecture** with FastAPI + Redis + ARQ
- **AI-powered** quote generation with LangChain + Claude
- **Modern tech stack** (Python, async-native)
- **Missing 11+ modules** for feature parity

---

## 🗂️ Module-by-Module Comparison

| # | Telco Module | Insurance Equivalent | Status | Priority | Complexity |
|---|--------------|---------------------|--------|----------|-----------|
| 1 | **Leads** | **Prospects** | ✅ DONE | - | - |
| 2 | **Coverage** | **Eligibility Check** | 🟡 PARTIAL | HIGH | Medium |
| 3 | **Offers** | **Quotes (AI-powered)** | ✅ DONE | - | - |
| 4 | **Contracts** | **Policies** | 🟡 PARTIAL | HIGH | Medium |
| 5 | **Commissions** | **Commissions** | 🟡 PARTIAL | HIGH | High |
| 6 | **Web & Hosting** | **Advisory Services** | ❌ TODO | MEDIUM | Medium |
| 7 | **Inventory** | **Product Catalog** | ❌ TODO | MEDIUM | Low |
| 8 | **Dashboard** | **Dashboard** | ❌ TODO | HIGH | Medium |
| 9 | **Reports** | **Reports** | ❌ TODO | HIGH | Medium |
| 10 | **Documents** | **Documents** | ❌ TODO | MEDIUM | Low |
| 11 | **Actions** | **Task Automation** | ❌ TODO | LOW | Low |
| 12 | **Products** | **Product Management** | ❌ TODO | MEDIUM | Low |
| 13 | **Validation** | **Data Validation** | ❌ TODO | LOW | Low |
| 14 | **Auth** | **Authentication & RBAC** | ❌ TODO | CRITICAL | High |
| 15 | **Search** | **Global Search** | ❌ TODO | LOW | Low |

**Legend**:
- ✅ DONE: Fully implemented
- 🟡 PARTIAL: Exists but incomplete
- ❌ TODO: Not yet started

---

## 🎯 Priority Tiers for Implementation

### 🔴 **TIER 1: CRITICAL (Must Have)**
These modules are essential for basic functionality and security.

1. **Authentication & RBAC** (Module 14)
   - Current: No auth system
   - Need: JWT-based authentication + Role-based access control
   - Roles: Admin, Head of Sales, Manager, Broker, Affiliate
   - Impact: Security, multi-user support
   - Effort: 2-3 days

2. **Dashboard** (Module 8)
   - Current: No analytics/reporting interface
   - Need: Role-based KPI dashboard
   - Features: Sales metrics, commission tracking, pipeline visualization
   - Impact: Core user experience
   - Effort: 2 days

3. **Complete Commissions System** (Module 5)
   - Current: Model exists, handler incomplete
   - Need: Multi-tier calculation (broker, manager, affiliate)
   - Features: Initial, renewal, recurring, referral commissions
   - Impact: Business logic completeness
   - Effort: 2 days

### 🟡 **TIER 2: HIGH VALUE (Should Have)**
These modules significantly enhance functionality.

4. **Eligibility Check Enhancement** (Module 2)
   - Current: Basic quote generation
   - Need: Pre-qualification check across providers
   - Features: Age/risk rules, coverage cache, provider comparison
   - Impact: Better UX, faster quotes
   - Effort: 1-2 days

5. **Policy PDF Generation** (Module 4)
   - Current: Placeholder handler
   - Need: PDF contract generation with reportlab
   - Features: Template-based, digitally signable
   - Impact: Legal compliance, customer deliverables
   - Effort: 1-2 days

6. **Reports Module** (Module 9)
   - Current: None
   - Need: Business intelligence reports
   - Features: Sales reports, commission reports, pipeline reports
   - Impact: Management visibility
   - Effort: 2 days

7. **Advisory Services** (Module 6)
   - Current: None
   - Need: Financial advisory module (replaces Web & Hosting)
   - Features: Investment planning, retirement planning
   - Impact: Revenue diversification
   - Effort: 1-2 days

### 🟢 **TIER 3: NICE TO HAVE (Could Have)**
These modules improve usability and polish.

8. **Product Catalog Management** (Module 7/12)
   - Current: Hardcoded providers/types
   - Need: Dynamic product/provider management
   - Features: CRUD for insurance products, pricing rules
   - Impact: Flexibility, maintainability
   - Effort: 1 day

9. **Document Management** (Module 10)
   - Current: None
   - Need: File upload/management system
   - Features: Store contracts, claims, ID documents
   - Impact: Centralized storage
   - Effort: 1 day

10. **Global Search** (Module 15)
    - Current: None
    - Need: Full-text search across all entities
    - Features: Search prospects, policies, quotes
    - Impact: Usability
    - Effort: 0.5 day

11. **Data Validation Module** (Module 13)
    - Current: Pydantic validation only
    - Need: Business rule validation (tax codes, age limits, etc.)
    - Impact: Data quality
    - Effort: 0.5 day

12. **Task Automation** (Module 11)
    - Current: Event-driven handlers
    - Need: Scheduled tasks (renewals, expirations)
    - Features: Celery beat or APScheduler
    - Impact: Automation
    - Effort: 1 day

---

## 📋 Detailed Module Breakdown

### Module 1: ✅ Prospects (COMPLETE)
**Telco**: Leads management
**Insurance**: Prospect management
**Status**: Fully implemented

**Features**:
- ✅ CRUD operations
- ✅ Status tracking (new → contacted → quoted → policy_signed)
- ✅ Assignment to brokers
- ✅ Event publishing (ProspectCreated)

**No action needed** - this module is complete.

---

### Module 2: 🟡 Eligibility Check (PARTIAL)
**Telco**: Coverage check (4 ISP providers, FTTH/FTTC/ADSL availability)
**Insurance**: Eligibility check (4 insurance providers, age/risk/type rules)

**Current State**:
- ✅ AI-powered quote generation exists
- ❌ No pre-qualification eligibility check
- ❌ No eligibility cache database
- ❌ No provider-specific rules engine

**Gap**:
```python
# Current: Direct to quote generation
POST /api/quotes/generate → AI generates quotes

# Need: Pre-check eligibility first
POST /api/eligibility/check → Returns eligible providers
POST /api/quotes/generate → Only for eligible providers
```

**What We Need to Build**:

1. **Database Table**: `eligibility_cache`
   ```sql
   CREATE TABLE eligibility_cache (
       id INT PRIMARY KEY AUTO_INCREMENT,
       provider ENUM('generali', 'unipolsai', 'allianz', 'axa'),
       insurance_type ENUM('life', 'auto', 'home', 'health'),
       age_min INT,
       age_max INT,
       risk_category VARCHAR(20),
       is_eligible BOOLEAN,
       base_premium DECIMAL(10,2),
       coverage_max DECIMAL(10,2),
       last_updated TIMESTAMP
   );
   ```

2. **Service**: `EligibilityService`
   ```python
   class EligibilityService:
       async def check_eligibility(
           prospect: Prospect,
           insurance_type: str
       ) -> List[EligibleProvider]:
           # Check age, risk, type against rules
           # Return list of eligible providers
           pass
   ```

3. **API Endpoint**:
   ```python
   POST /api/eligibility/check
   {
       "prospect_id": 123,
       "insurance_type": "life"
   }

   Response:
   {
       "eligible_providers": [
           {"provider": "generali", "base_premium": 450.00},
           {"provider": "allianz", "base_premium": 480.00}
       ],
       "ineligible_providers": [
           {"provider": "axa", "reason": "Age exceeds maximum"}
       ]
   }
   ```

**Effort**: 1-2 days
**Priority**: HIGH
**Dependencies**: None

---

### Module 3: ✅ Quotes (COMPLETE with AI Enhancement)
**Telco**: Offer generation
**Insurance**: AI-powered quote generation

**Status**: Fully implemented with LangChain + Claude integration

**Features**:
- ✅ Multi-provider quote generation
- ✅ AI comparison and recommendation
- ✅ Quote status tracking
- ✅ Expiration dates

**Enhancement Over Telco**: AI-powered recommendations (not in Telco version)

**No action needed** - this module exceeds Telco functionality.

---

### Module 4: 🟡 Policies (PARTIAL)
**Telco**: Contract generation with mPDF
**Insurance**: Policy management

**Current State**:
- ✅ Policy model and database
- ✅ Policy creation from accepted quotes
- ✅ Status tracking (active, expired, cancelled)
- ❌ PDF generation (placeholder only)
- ❌ Digital signature support
- ❌ Policy renewal automation

**Gap**:
```python
# Current handler (placeholder):
class PolicyPDFGenerationHandler:
    async def handle(self, event_data):
        logger.info("PDF generation - PLACEHOLDER")
        # TODO: Implement with reportlab

# Need: Full PDF generation
class PolicyPDFGenerationHandler:
    async def handle(self, event_data):
        pdf = generate_policy_pdf(policy)
        save_to_storage(pdf)
        update_policy_pdf_path(policy.id, pdf_path)
        publish_event(PolicyPDFGenerated)
```

**What We Need to Build**:

1. **PDF Generation Service**:
   ```python
   # app/services/pdf_service.py
   from reportlab.lib.pagesizes import A4
   from reportlab.pdfgen import canvas

   class PDFService:
       def generate_policy_pdf(self, policy: Policy) -> bytes:
           # Generate PDF with policy details
           # Include: policy number, dates, coverage, terms
           pass

       def save_pdf(self, pdf_bytes: bytes, policy_number: str) -> str:
           # Save to filesystem or S3
           # Return file path
           pass
   ```

2. **Update Handler**:
   ```python
   class PolicyPDFGenerationHandler(EventHandler):
       async def handle(self, event_data: Dict[str, Any]) -> None:
           policy = get_policy(event_data["policy_id"])

           # Generate PDF
           pdf_service = PDFService()
           pdf_bytes = pdf_service.generate_policy_pdf(policy)
           pdf_path = pdf_service.save_pdf(pdf_bytes, policy.policy_number)

           # Update policy record
           update_policy_pdf_path(policy.id, pdf_path)

           # Publish event
           await EventPublisher.publish(PolicyPDFGenerated(...))
   ```

3. **API Endpoint**:
   ```python
   @router.get("/policies/{policy_id}/pdf")
   async def download_policy_pdf(policy_id: int):
       policy = get_policy(policy_id)
       return FileResponse(policy.pdf_path, filename=f"{policy.policy_number}.pdf")
   ```

**Effort**: 1-2 days
**Priority**: HIGH
**Dependencies**: None

---

### Module 5: 🟡 Commissions (PARTIAL)
**Telco**: Multi-tier commission tracking
**Insurance**: Commission calculation

**Current State**:
- ✅ Commission model exists in database
- ✅ Basic structure (broker, manager, affiliate tiers)
- ❌ Calculation logic not implemented
- ❌ No commission handler
- ❌ No commission reports

**Gap**: Telco has complete commission tracking with:
- Initial sale commission (broker 15%, manager 5%, affiliate 3%)
- Renewal commissions (year 1-5 with declining rates)
- Monthly aggregation
- Payment status tracking

**What We Need to Build**:

1. **Commission Calculation Service**:
   ```python
   # app/services/commission_service.py
   class CommissionService:
       COMMISSION_RATES = {
           "initial": {
               "broker": 0.15,      # 15% of annual premium
               "manager": 0.05,     # 5% of annual premium
               "affiliate": 0.03    # 3% of annual premium
           },
           "renewal_year1": {
               "broker": 0.10,
               "manager": 0.03,
               "affiliate": 0.02
           },
           "renewal_recurring": {
               "broker": 0.05,
               "manager": 0.02,
               "affiliate": 0.01
           }
       }

       async def calculate_initial_commission(
           self,
           policy: Policy,
           broker: User,
           manager: User = None,
           affiliate: User = None
       ) -> List[Commission]:
           annual_premium = policy.quote.annual_premium
           commissions = []

           # Broker commission
           commissions.append(Commission(
               prospect_id=policy.quote.prospect_id,
               broker_id=broker.id,
               commission_type="initial",
               amount=annual_premium * self.COMMISSION_RATES["initial"]["broker"],
               percentage=self.COMMISSION_RATES["initial"]["broker"] * 100,
               base_amount=annual_premium,
               status="pending"
           ))

           # Manager commission (if exists)
           if manager:
               commissions.append(...)

           # Affiliate commission (if exists)
           if affiliate:
               commissions.append(...)

           return commissions
   ```

2. **Event Handler**:
   ```python
   # app/handlers/commission_handlers.py
   class CommissionCalculationHandler(EventHandler):
       async def handle(self, event_data: Dict[str, Any]) -> None:
           policy_id = event_data["data"]["policy_id"]

           # Get policy and related users
           policy = get_policy(policy_id)
           broker = get_broker_for_prospect(policy.quote.prospect_id)
           manager = broker.supervisor if broker else None

           # Calculate commissions
           commission_service = CommissionService()
           commissions = await commission_service.calculate_initial_commission(
               policy, broker, manager
           )

           # Save to database
           save_commissions(commissions)

           logger.info(f"✅ Created {len(commissions)} commission records for policy {policy.policy_number}")
   ```

3. **Register Handler**:
   ```python
   # app/workers/main.py
   EVENT_HANDLERS = {
       ...
       "PolicyCreated": [
           PolicyPDFGenerationHandler(),
           PolicyEmailNotificationHandler(),
           CommissionCalculationHandler(),  # ADD THIS
       ],
   }
   ```

4. **Commission Dashboard API**:
   ```python
   # app/api/v1/commissions.py
   @router.get("/dashboard")
   async def commission_dashboard(
       user_id: int,
       period_year: int,
       period_month: int,
       db: Session = Depends(get_db_session)
   ):
       commissions = db.query(Commission).filter(
           Commission.broker_id == user_id,
           Commission.period_year == period_year,
           Commission.period_month == period_month
       ).all()

       return {
           "total_pending": sum(c.amount for c in commissions if c.status == "pending"),
           "total_paid": sum(c.amount for c in commissions if c.status == "paid"),
           "commission_breakdown": [...]
       }
   ```

**Effort**: 2 days
**Priority**: HIGH (TIER 1 - CRITICAL)
**Dependencies**: Policy creation must work

---

### Module 6: ❌ Advisory Services (TODO)
**Telco**: Web & Hosting services
**Insurance**: Financial advisory services

**Concept**: Additional revenue stream beyond insurance policies.

**What We Need to Build**:

1. **Database Table**:
   ```sql
   CREATE TABLE advisory_offers (
       id VARCHAR(20) PRIMARY KEY,
       prospect_id INT NOT NULL,
       service_type ENUM('financial_planning', 'investment', 'retirement', 'estate_planning'),
       status ENUM('draft', 'sent', 'accepted', 'closed'),
       total_amount DECIMAL(10,2),
       created_at TIMESTAMP,
       FOREIGN KEY (prospect_id) REFERENCES prospects(id)
   );

   CREATE TABLE advisory_items (
       id INT PRIMARY KEY AUTO_INCREMENT,
       offer_id VARCHAR(20) NOT NULL,
       service_name VARCHAR(100),
       description TEXT,
       amount DECIMAL(10,2),
       FOREIGN KEY (offer_id) REFERENCES advisory_offers(id)
   );
   ```

2. **Model & API**:
   ```python
   # app/models/advisory.py
   class AdvisoryOffer(Base):
       __tablename__ = "advisory_offers"
       id = Column(String(20), primary_key=True)
       prospect_id = Column(Integer, ForeignKey("prospects.id"))
       service_type = Column(Enum(...))
       status = Column(Enum(...))
       total_amount = Column(Numeric(10, 2))

   # app/api/v1/advisory.py
   @router.post("/")
   async def create_advisory_offer(
       request: AdvisoryOfferCreate,
       db: Session = Depends(get_db_session)
   ):
       offer = AdvisoryOffer(...)
       db.add(offer)
       db.commit()
       return offer
   ```

3. **AI Integration** (Enhancement over Telco):
   ```python
   # Use LangChain to recommend advisory services
   class AdvisoryRecommendationService:
       def recommend_services(self, prospect: Prospect) -> List[str]:
           # Analyze prospect profile
           # Recommend appropriate financial services
           pass
   ```

**Effort**: 1-2 days
**Priority**: MEDIUM (TIER 2)
**Dependencies**: Prospects module

---

### Module 7/12: ❌ Product Catalog (TODO)
**Telco**: Inventory + Products modules
**Insurance**: Product catalog management

**Current State**: Providers and insurance types are hardcoded.

**What We Need to Build**:

1. **Database Tables**:
   ```sql
   CREATE TABLE insurance_providers (
       id INT PRIMARY KEY AUTO_INCREMENT,
       name VARCHAR(100) UNIQUE,
       code VARCHAR(20) UNIQUE,
       is_active BOOLEAN,
       contact_email VARCHAR(255),
       commission_rate DECIMAL(5,2)
   );

   CREATE TABLE insurance_products (
       id INT PRIMARY KEY AUTO_INCREMENT,
       provider_id INT,
       product_code VARCHAR(50),
       insurance_type ENUM('life', 'auto', 'home', 'health'),
       name VARCHAR(200),
       description TEXT,
       base_premium DECIMAL(10,2),
       coverage_amount DECIMAL(12,2),
       is_active BOOLEAN,
       FOREIGN KEY (provider_id) REFERENCES insurance_providers(id)
   );
   ```

2. **Admin API** (CRUD):
   ```python
   # app/api/v1/products.py
   @router.post("/providers")
   async def create_provider(...)

   @router.get("/providers")
   async def list_providers(...)

   @router.post("/products")
   async def create_product(...)

   @router.get("/products")
   async def list_products(...)
   ```

**Effort**: 1 day
**Priority**: MEDIUM (TIER 3)
**Dependencies**: None

---

### Module 8: ❌ Dashboard (TODO)
**Telco**: Role-based dashboard with KPIs
**Insurance**: Analytics dashboard

**What We Need to Build**:

1. **Dashboard API**:
   ```python
   # app/api/v1/dashboard.py
   @router.get("/")
   async def get_dashboard(
       user: User = Depends(get_current_user),
       period: str = "month",
       db: Session = Depends(get_db_session)
   ):
       # Role-based data aggregation
       if user.role == "broker":
           return {
               "my_prospects": count_my_prospects(user.id),
               "my_quotes": count_my_quotes(user.id),
               "my_policies": count_my_policies(user.id),
               "my_commissions": sum_my_commissions(user.id, period),
               "pipeline": get_pipeline(user.id)
           }
       elif user.role == "manager":
           return {
               "team_prospects": count_team_prospects(user.id),
               "team_conversion_rate": calculate_conversion_rate(user.id),
               "team_commissions": sum_team_commissions(user.id, period),
               "top_brokers": get_top_brokers(user.id)
           }
       # ... admin, head_of_sales views
   ```

2. **Aggregation Queries**:
   ```python
   def get_pipeline(broker_id: int) -> Dict:
       return {
           "new_prospects": count(status="new"),
           "contacted": count(status="contacted"),
           "quoted": count(status="quoted"),
           "policy_signed": count(status="policy_signed")
       }
   ```

**Effort**: 2 days
**Priority**: HIGH (TIER 1 - CRITICAL)
**Dependencies**: Auth system

---

### Module 9: ❌ Reports (TODO)
**Telco**: Business intelligence reports
**Insurance**: Sales & commission reports

**What We Need to Build**:

1. **Report Types**:
   - Sales Report (by broker, by period, by product)
   - Commission Report (pending, paid, by tier)
   - Pipeline Report (conversion funnel)
   - Policy Expiration Report (upcoming renewals)

2. **API**:
   ```python
   # app/api/v1/reports.py
   @router.get("/sales")
   async def sales_report(
       start_date: date,
       end_date: date,
       group_by: str = "broker"
   ):
       # Aggregate sales data
       pass

   @router.get("/commissions")
   async def commission_report(
       period_year: int,
       period_month: int,
       status: str = "all"
   ):
       # Aggregate commission data
       pass
   ```

3. **Export**: CSV/Excel export functionality

**Effort**: 2 days
**Priority**: HIGH (TIER 2)
**Dependencies**: Dashboard queries

---

### Module 10: ❌ Document Management (TODO)
**Telco**: Document upload/management
**Insurance**: Policy documents, claims, ID scans

**What We Need to Build**:

1. **Database**:
   ```sql
   CREATE TABLE documents (
       id INT PRIMARY KEY AUTO_INCREMENT,
       prospect_id INT,
       policy_id INT,
       document_type ENUM('id_card', 'policy_pdf', 'claim', 'other'),
       file_name VARCHAR(255),
       file_path VARCHAR(500),
       file_size INT,
       mime_type VARCHAR(100),
       uploaded_by INT,
       uploaded_at TIMESTAMP,
       FOREIGN KEY (prospect_id) REFERENCES prospects(id),
       FOREIGN KEY (policy_id) REFERENCES policies(id)
   );
   ```

2. **File Upload API**:
   ```python
   from fastapi import UploadFile

   @router.post("/upload")
   async def upload_document(
       file: UploadFile,
       prospect_id: int,
       document_type: str
   ):
       # Save file to storage
       file_path = save_file(file)

       # Create document record
       doc = Document(
           prospect_id=prospect_id,
           document_type=document_type,
           file_name=file.filename,
           file_path=file_path
       )
       db.add(doc)
       db.commit()
   ```

**Effort**: 1 day
**Priority**: MEDIUM (TIER 3)
**Dependencies**: None

---

### Module 11: ❌ Task Automation (TODO)
**Telco**: Scheduled actions (reminders, follow-ups)
**Insurance**: Renewal reminders, policy expirations

**What We Need to Build**:

1. **Scheduled Tasks** (Celery Beat or APScheduler):
   ```python
   # app/tasks/scheduled.py
   from apscheduler.schedulers.asyncio import AsyncIOScheduler

   scheduler = AsyncIOScheduler()

   @scheduler.scheduled_job('cron', hour=9, minute=0)  # Daily at 9 AM
   async def check_expiring_policies():
       # Find policies expiring in 30 days
       expiring_policies = get_expiring_policies(days=30)

       for policy in expiring_policies:
           # Send renewal reminder
           await send_renewal_email(policy)

           # Publish event
           await EventPublisher.publish(PolicyExpiring(...))

   @scheduler.scheduled_job('cron', day=1, hour=0, minute=0)  # Monthly
   async def generate_commission_reports():
       # Generate monthly commission reports
       pass
   ```

2. **Event**:
   ```python
   class PolicyExpiring(DomainEvent):
       event_type = "PolicyExpiring"
       policy_id: int
       policy_number: str
       expiry_date: str
       days_until_expiry: int
   ```

**Effort**: 1 day
**Priority**: LOW (TIER 3)
**Dependencies**: Email service

---

### Module 13: ❌ Data Validation (TODO)
**Telco**: Business rule validation
**Insurance**: Tax code validation, age limits, etc.

**What We Need to Build**:

1. **Validation Service**:
   ```python
   # app/services/validation_service.py
   import re

   class ValidationService:
       @staticmethod
       def validate_italian_tax_code(tax_code: str) -> bool:
           # Italian Codice Fiscale validation
           pattern = r'^[A-Z]{6}\d{2}[A-Z]\d{2}[A-Z]\d{3}[A-Z]$'
           return bool(re.match(pattern, tax_code.upper()))

       @staticmethod
       def validate_age_for_insurance(
           birth_date: date,
           insurance_type: str
       ) -> Tuple[bool, str]:
           age = calculate_age(birth_date)

           limits = {
               "life": (18, 75),
               "auto": (18, None),
               "home": (18, None),
               "health": (0, 85)
           }

           min_age, max_age = limits.get(insurance_type, (18, None))

           if age < min_age:
               return False, f"Minimum age for {insurance_type} insurance is {min_age}"
           if max_age and age > max_age:
               return False, f"Maximum age for {insurance_type} insurance is {max_age}"

           return True, "OK"
   ```

2. **Integrate into Pydantic Models**:
   ```python
   from pydantic import validator

   class ProspectCreate(BaseModel):
       tax_code: str
       birth_date: date

       @validator('tax_code')
       def validate_tax_code(cls, v):
           if not ValidationService.validate_italian_tax_code(v):
               raise ValueError('Invalid Italian tax code format')
           return v
   ```

**Effort**: 0.5 day
**Priority**: LOW (TIER 3)
**Dependencies**: None

---

### Module 14: ❌ Authentication & RBAC (TODO)
**Telco**: Session-based auth with role hierarchy
**Insurance**: JWT-based auth with RBAC

**What We Need to Build**:

1. **User Model Enhancement** (already exists):
   ```python
   # app/models/user.py - already has role structure
   class User(Base):
       role = Column(Enum('admin', 'head_of_sales', 'manager', 'broker', 'affiliate'))
       supervisor_id = Column(Integer, ForeignKey('users.id'))
   ```

2. **Auth Service**:
   ```python
   # app/services/auth_service.py
   from datetime import datetime, timedelta
   from jose import JWTError, jwt
   from passlib.context import CryptContext

   pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

   class AuthService:
       SECRET_KEY = settings.SECRET_KEY
       ALGORITHM = "HS256"
       ACCESS_TOKEN_EXPIRE_MINUTES = 30

       @staticmethod
       def verify_password(plain_password: str, hashed_password: str) -> bool:
           return pwd_context.verify(plain_password, hashed_password)

       @staticmethod
       def get_password_hash(password: str) -> str:
           return pwd_context.hash(password)

       @staticmethod
       def create_access_token(data: dict) -> str:
           to_encode = data.copy()
           expire = datetime.utcnow() + timedelta(minutes=AuthService.ACCESS_TOKEN_EXPIRE_MINUTES)
           to_encode.update({"exp": expire})
           return jwt.encode(to_encode, AuthService.SECRET_KEY, algorithm=AuthService.ALGORITHM)

       @staticmethod
       def verify_token(token: str) -> dict:
           try:
               payload = jwt.decode(token, AuthService.SECRET_KEY, algorithms=[AuthService.ALGORITHM])
               return payload
           except JWTError:
               raise HTTPException(status_code=401, detail="Invalid token")
   ```

3. **Auth Endpoints**:
   ```python
   # app/api/v1/auth.py
   from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

   oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")

   @router.post("/login")
   async def login(
       form_data: OAuth2PasswordRequestForm = Depends(),
       db: Session = Depends(get_db_session)
   ):
       user = db.query(User).filter(User.username == form_data.username).first()

       if not user or not AuthService.verify_password(form_data.password, user.password_hash):
           raise HTTPException(status_code=401, detail="Invalid credentials")

       access_token = AuthService.create_access_token(
           data={"sub": user.username, "role": user.role}
       )

       return {"access_token": access_token, "token_type": "bearer"}

   @router.post("/register")
   async def register(
       username: str,
       email: str,
       password: str,
       role: str,
       db: Session = Depends(get_db_session)
   ):
       hashed_password = AuthService.get_password_hash(password)
       user = User(
           username=username,
           email=email,
           password_hash=hashed_password,
           role=role
       )
       db.add(user)
       db.commit()
       return {"message": "User created successfully"}
   ```

4. **Dependency for Protected Routes**:
   ```python
   # app/api/dependencies.py
   async def get_current_user(
       token: str = Depends(oauth2_scheme),
       db: Session = Depends(get_db_session)
   ) -> User:
       payload = AuthService.verify_token(token)
       username = payload.get("sub")

       user = db.query(User).filter(User.username == username).first()
       if not user:
           raise HTTPException(status_code=401, detail="User not found")

       return user

   def require_role(allowed_roles: List[str]):
       def role_checker(user: User = Depends(get_current_user)):
           if user.role not in allowed_roles:
               raise HTTPException(status_code=403, detail="Insufficient permissions")
           return user
       return role_checker
   ```

5. **Protect Existing Routes**:
   ```python
   # Example: Only brokers and managers can create prospects
   @router.post("/", response_model=ProspectResponse)
   async def create_prospect(
       request: ProspectCreate,
       user: User = Depends(require_role(["broker", "manager", "admin"])),
       db: Session = Depends(get_db_session)
   ):
       ...
   ```

**Effort**: 2-3 days
**Priority**: CRITICAL (TIER 1)
**Dependencies**: None - should be implemented ASAP

---

### Module 15: ❌ Global Search (TODO)
**Telco**: Full-text search across entities
**Insurance**: Search prospects, policies, quotes

**What We Need to Build**:

1. **Search Service**:
   ```python
   # app/services/search_service.py
   from sqlalchemy import or_

   class SearchService:
       @staticmethod
       def search(query: str, db: Session) -> Dict:
           results = {}

           # Search prospects
           prospects = db.query(Prospect).filter(
               or_(
                   Prospect.first_name.ilike(f"%{query}%"),
                   Prospect.last_name.ilike(f"%{query}%"),
                   Prospect.email.ilike(f"%{query}%"),
                   Prospect.tax_code.ilike(f"%{query}%")
               )
           ).limit(10).all()
           results["prospects"] = [p.to_dict() for p in prospects]

           # Search policies
           policies = db.query(Policy).filter(
               Policy.policy_number.ilike(f"%{query}%")
           ).limit(10).all()
           results["policies"] = [p.to_dict() for p in policies]

           # Search quotes
           quotes = db.query(Quote).filter(
               or_(
                   Quote.provider.ilike(f"%{query}%"),
                   Quote.insurance_type.ilike(f"%{query}%")
               )
           ).limit(10).all()
           results["quotes"] = [q.to_dict() for q in quotes]

           return results
   ```

2. **API**:
   ```python
   @router.get("/search")
   async def global_search(
       q: str,
       db: Session = Depends(get_db_session),
       user: User = Depends(get_current_user)
   ):
       return SearchService.search(q, db)
   ```

**Effort**: 0.5 day
**Priority**: LOW (TIER 3)
**Dependencies**: None

---

## 📅 Implementation Timeline

### **Phase 1: Foundation (Week 1)** - 5 days
**Goal**: Security, authentication, and core infrastructure

| Day | Module | Tasks | Priority |
|-----|--------|-------|----------|
| 1-2 | **Auth & RBAC** | JWT auth, role middleware, protect routes | CRITICAL |
| 3 | **Dashboard** | Basic KPI dashboard, role-based views | HIGH |
| 4 | **Commissions** | Complete calculation logic, handlers | HIGH |
| 5 | **PDF Generation** | Policy PDF with reportlab | HIGH |

**End of Phase 1**: Secure, authenticated system with complete policy-to-commission flow.

---

### **Phase 2: Business Logic (Week 2)** - 4 days
**Goal**: Complete core business functionality

| Day | Module | Tasks | Priority |
|-----|--------|-------|----------|
| 6 | **Eligibility Check** | Rules engine, cache table, API | HIGH |
| 7 | **Reports** | Sales report, commission report | HIGH |
| 8-9 | **Advisory Services** | Advisory offers, items, API, AI recommendations | MEDIUM |

**End of Phase 2**: Full business feature parity with Telco CRM.

---

### **Phase 3: Polish & Extras (Week 3)** - 3 days
**Goal**: Usability and advanced features

| Day | Module | Tasks | Priority |
|-----|--------|-------|----------|
| 10 | **Product Catalog** | Providers, products CRUD | MEDIUM |
| 11 | **Documents** | File upload, management | MEDIUM |
| 12 | **Search + Validation + Tasks** | Global search, validation rules, scheduled tasks | LOW |

**End of Phase 3**: Production-ready Insurance CRM equivalent to Telco CRM.

---

### **Phase 4: Frontend (Week 4)** - 5 days
**Goal**: Complete full-stack project

| Day | Module | Tasks | Priority |
|-----|--------|-------|----------|
| 13-14 | **Frontend Setup** | Next.js + shadcn/ui, routing | CRITICAL |
| 15-16 | **Core Pages** | Dashboard, prospects, quotes, policies | CRITICAL |
| 17 | **Auth UI** | Login, register, role-based navigation | CRITICAL |

**End of Phase 4**: Complete, deployable full-stack application.

---

## 🎯 Success Metrics

### Feature Parity Checklist
- [ ] 15/15 modules implemented (100% parity)
- [ ] Multi-tier commission system working
- [ ] Role-based access control functional
- [ ] PDF generation operational
- [ ] Dashboard with real-time KPIs
- [ ] Complete business flow: Prospect → Eligibility → Quote → Policy → Commission
- [ ] Frontend for all major operations

### Enhancement Over Telco CRM
- ✅ AI-powered quote recommendations (LangChain + Claude)
- ✅ Event-driven architecture (better scalability)
- ✅ Async-native (faster performance)
- ✅ Modern tech stack (Python, FastAPI, Redis)
- ✅ Complete audit trail (Event Store)

---

## 💡 Strategic Recommendations

### 1. **Prioritize Auth First**
Without authentication, the project is insecure and not production-ready. This should be **Day 1 priority**.

### 2. **Complete Business Flow**
Focus on Tier 1 modules (Auth, Dashboard, Commissions, PDF) to demonstrate complete business logic.

### 3. **Frontend Is Non-Negotiable**
As the user stated: *"Un progetto è un progetto, completo."* Backend-only is incomplete.

### 4. **Use Telco as Reference**
When implementing each module, look at Telco's implementation for business logic patterns:
- How does Telco calculate commissions? → Apply same logic to insurance
- What reports does Telco generate? → Create insurance equivalents
- How does Telco handle user roles? → Implement same RBAC

### 5. **Maintain AI Advantage**
Keep the AI-powered quote generation - this is a differentiator over the Telco project.

### 6. **Documentation**
Update `case_study_complete.md` with each new module to explain architectural decisions.

---

## 🚀 Next Steps (Immediate)

1. **Review this gap analysis** with the user
2. **Confirm priority order** for implementation
3. **Start with Authentication** (Module 14) - 2-3 days
4. **Implement Dashboard** (Module 8) - 2 days
5. **Complete Commissions** (Module 5) - 2 days
6. **Continue through Phase 1-4**

---

## 📊 Current Progress Summary

**Modules Complete**: 3 / 15 (20%)
**Modules Partial**: 3 / 15 (20%)
**Modules TODO**: 9 / 15 (60%)

**Estimated Total Effort**: 17-20 days (3-4 weeks)
- Phase 1 (Foundation): 5 days
- Phase 2 (Business Logic): 4 days
- Phase 3 (Polish): 3 days
- Phase 4 (Frontend): 5 days

**Timeline to Feature Parity**: 3-4 weeks of focused development

---

**Document End** - Ready for review and implementation planning.
