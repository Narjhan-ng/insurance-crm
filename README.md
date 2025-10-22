# Insurance CRM Platform

A modern insurance customer relationship management system built with event-driven architecture. This project demonstrates how to build scalable, production-ready applications using async Python and AI-powered features.

## What This Does

Helps insurance brokers manage their customers through the entire lifecycle:
- Track prospects and leads
- Check eligibility across multiple providers (Generali, UnipolSai, Allianz, AXA)
- Generate and compare insurance quotes
- Manage active policies
- Calculate commissions automatically
- Handle renewals and notifications

The interesting part? Everything runs on events. When a customer accepts a quote, the system automatically creates the policy, calculates commissions, generates the PDF contract, and sends notifications - all without blocking the API response.

## Why Event-Driven?

Traditional CRUD apps handle everything synchronously. User clicks "Accept Quote" → server does 5-6 things → response after 10 seconds. Not great.

With events:
- API responds immediately ("Quote accepted!")
- Background workers handle PDF generation, emails, commission calculations
- Each piece can fail and retry independently
- Easy to add new functionality without touching existing code
- Complete audit trail for compliance

Real companies use this pattern (Stripe, Shopify, etc). Wanted to build something that shows I understand production architecture, not just toy CRUD apps.

## Tech Stack

**Backend:**
- FastAPI (async Python web framework)
- SQLAlchemy (ORM)
- Redis Streams (event bus)
- ARQ (async task queue)

**AI/ML:**
- LangChain (for intelligent quote comparison)
- Anthropic Claude (eligibility analysis)

**Database:**
- MySQL (main data store)
- Redis (events + caching)

## Architecture

```
API Request → FastAPI → Business Logic → Publish Event → Redis Stream
                                              ↓
                                        ARQ Workers
                                              ↓
                                   Event Handlers (parallel)
                                              ↓
                            [Emails, PDFs, Notifications, etc.]
```

Every important action publishes an event. Handlers react independently. If email fails, commission calculation still works. Clean separation.

## Getting Started

### Prerequisites

- Python 3.11+
- MySQL 8.0+
- Redis 7.0+

### Installation

```bash
# Clone the repo
git clone https://github.com/yourusername/insurance-crm.git
cd insurance-crm

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your database credentials and API keys

# Run database migrations
alembic upgrade head

# Start Redis (in another terminal)
redis-server

# Start the API server
uvicorn app.main:app --reload

# Start the event workers (in another terminal)
python -m app.workers.main
```

API will be available at `http://localhost:8000`

## Project Structure

```
insurance-crm/
├── app/
│   ├── api/              # FastAPI routes
│   ├── models/           # SQLAlchemy models
│   ├── events/           # Domain event definitions
│   ├── handlers/         # Event handlers
│   ├── workers/          # ARQ background workers
│   ├── services/         # Business logic
│   └── core/             # Config, database, dependencies
├── alembic/              # Database migrations
├── tests/                # Unit and integration tests
└── config/               # Application settings
```

## Key Features

### Event-Driven Workflows

When a prospect is created:
```python
ProspectCreated Event
  ↓
  ├─→ AuditLogHandler (compliance trail)
  ├─→ NotifyBrokerHandler (email to broker)
  ├─→ SendWelcomeEmailHandler (email to customer)
  └─→ UpdateDashboardHandler (real-time metrics)
```

All handlers run in parallel. Failures are isolated and retried automatically.

### AI-Powered Quote Generation

Uses LangChain to compare offers from multiple providers and recommend the best fit based on customer profile, risk assessment, and coverage needs.

### Commission Calculation

Multi-tier commission structure (broker, manager, affiliate) calculated automatically when policies are signed. Event-driven ensures commissions are always in sync with policy state.

## API Examples

### Create a new prospect
```bash
curl -X POST http://localhost:8000/api/prospects \
  -H "Content-Type: application/json" \
  -d '{
    "type": "individual",
    "first_name": "Marco",
    "last_name": "Rossi",
    "email": "marco.rossi@example.com",
    "phone": "+39 333 1234567"
  }'
```

### Check eligibility
```bash
curl -X POST http://localhost:8000/api/eligibility/check \
  -H "Content-Type: application/json" \
  -d '{
    "prospect_id": 123,
    "insurance_type": "life",
    "coverage_amount": 500000
  }'
```

Full API documentation at `http://localhost:8000/docs`

## Development

### Running Tests
```bash
pytest
```

### Code Quality
```bash
# Format code
black .

# Lint
ruff check .
```

## Design Decisions

Some choices I made and why:

**Event-Driven over CRUD**: Better for real-world complexity, demonstrates system design thinking

**ARQ over Celery**: Async-native, cleaner integration with FastAPI, less overhead

**Event Notification over Event Sourcing**: Pragmatic - gets 80% of benefits with 20% of complexity

**Redis Streams over RabbitMQ**: Simpler setup, good enough for this scale, already using Redis for caching

Full rationale documented in progress notes (private).

## What I Learned

- Event-driven architecture is more about organizing side-effects than fancy tech
- Idempotency is harder than it looks (handlers can be called multiple times!)
- Redis Streams are underrated for event buses
- FastAPI + ARQ = beautiful async stack
- Testing async code requires different thinking

## Roadmap

- [ ] WebSocket for real-time dashboard updates
- [ ] PDF generation with reportlab
- [ ] Email templates with Jinja2
- [ ] Admin panel for broker management
- [ ] Analytics dashboard
- [ ] Integration with real insurance provider APIs

## Contributing

This is a portfolio/learning project. Feel free to fork and experiment!

## Author

Nicola Gnasso - AI Engineering Portfolio Project

## Acknowledgments

Anthropic Claude for development assistance
