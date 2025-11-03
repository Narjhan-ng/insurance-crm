# 📘 Master Document: AI Engineer Roadmap Completa

**Versione**: 1.1 (Voice Care Bot Added)  
**Data**: Ottobre 2025  
**Studente**: Nicola Gnasso  
**Obiettivo**: AI Engineer €45-55k in 6-8 settimane  
**Progetto Core**: Insurance Comparison CRM + Voice Care Bot

---

## 👤 PROFILO STUDENTE

### Background
- **Nome**: Nicola Gnasso
- **Esperienza**: 17 anni IT/Infrastructure
- **Educazione**: Laurea Magistrale Ingegneria Informatica
- **Skills attuali**: PHP, SQL, Bash, C/C++, Linux, Git, Docker basics
- **Esperienza BI**: Data Warehousing, SQL avanzato
- **Current RAL**: €30k
- **Target RAL**: €45-55k (+50-80%)
- **Location**: Aversa (CE), Italia

### Progetti Esistenti
- **Webapp Telco completa** (produzione, non pubblicabile)
- **n8n workflows** su GitHub
- **Sviluppo con Claude Code** (orchestrator + debugger)

### Gap da Colmare
- ❌ Portfolio pubblico progetti AI
- ❌ LangChain/LangGraph formalizzazione
- ❌ Visibilità LinkedIn/community
- ❌ Esperienza "AI Engineer" formale

---

## 🎯 OBIETTIVO FINALE

### Target Position
**AI Engineer** (non MLOps - no esperienza infra production richiesta)

### Salari Mercato Italia 2025
- Entry AI Engineer: €35-45k
- Mid AI Engineer: €45-60k
- Senior AI Engineer: €60-80k+

### Timeline
**6-8 settimane intensive** = 150-200h totali

### Success Criteria
- 8-9 progetti portfolio pubblico
- 1 showcase production-level (Insurance CRM)
- 1 differenziatore (Voice Care Bot)
- 30+ applications inviate
- 5+ interview rounds
- 1+ job offer target

---

## 🏗️ PROGETTI PORTFOLIO

### Settimana 1
1. **Insurance Policy RAG** - Document Q&A system
2. **Eligibility Checker Agent** - Multi-tool agent

### Settimana 2-4
3. **Insurance CRM** - Full-stack application (core)

### Settimana 5
4. **Voice Care Bot** - Real-time voice AI assistant (differenziatore)

### Settimana 6
5. **Multi-Agent System** - LangGraph orchestration
6. **Advisory Services** - Financial advisory module

### Settimana 7-8
- Portfolio polish + Applications

---

## 🏗️ PROGETTO CENTRALE: INSURANCE CRM

### Concept
Clone webapp Telco esistente → Insurance domain
Dimostra: domain adaptation, LangChain integration, production architecture

### Architecture Originale (Telco)

**Database Structure**:
- `crm` (primary): leads, offers, contracts, commissions, users
- `coverage` (secondary): provider coverage data (TIM, OpenFiber, Fastweb, NHM)

**Core Modules** (15 totali):
1. Leads - Customer lifecycle management
2. Coverage - Network availability checking
3. Offers - Dynamic quote generation
4. Contracts - PDF document generation
5. Commissions - Multi-tier compensation
6. Web & Hosting - Additional services
7. Inventory - Device management
8. Dashboard - Role-based analytics
9. Reports - Business intelligence
10. Documents - File management
11. Actions - Task automation
12. Products - Catalog management
13. Validation - Data quality
14. Auth - Security & access
15. Search - Global search

**Tech Stack**:
- PHP 8.0 + custom MVC framework
- MySQL dual database
- mPDF for documents
- Repository pattern
- CSRF protection
- Role-based access (Admin/Manager/Agent/Partner)

### Domain Mapping: Telco → Insurance

| Telco Concept | Insurance Equivalent |
|---------------|---------------------|
| **Lead telecomunicazioni** | Insurance prospect (individual/family/business) |
| **Coverage check (4 providers)** | Policy eligibility check (Generali/UnipolSai/Allianz/AXA) |
| **Tecnologie (FTTH/FTTC/ADSL)** | Insurance types (Life/Auto/Home/Health) |
| **Offerta internet + devices** | Policy quote with coverage options |
| **Contratto telecomunicazioni** | Insurance policy agreement |
| **Commissione agente/manager/partner** | Broker/manager/affiliate commission |
| **Web & Hosting services** | Financial advisory services |
| **Inventory dispositivi** | Policy catalog management |
| **Coverage database** | Eligibility rules database |

### Insurance CRM - Database Schema

```sql
-- =======================
-- PROSPECTS (ex Leads)
-- =======================
CREATE TABLE prospects (
    id INT PRIMARY KEY AUTO_INCREMENT,
    type ENUM('individual', 'family', 'business') NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    birth_date DATE,
    email VARCHAR(255),
    phone VARCHAR(20),
    tax_code VARCHAR(20),
    status ENUM('new', 'contacted', 'quoted', 'policy_signed', 'declined') DEFAULT 'new',
    risk_category ENUM('low', 'medium', 'high'),
    assigned_broker INT,
    created_by INT NOT NULL,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    FOREIGN KEY (assigned_broker) REFERENCES users(id),
    FOREIGN KEY (created_by) REFERENCES users(id),
    
    INDEX idx_prospects_status (status),
    INDEX idx_prospects_broker (assigned_broker)
);

-- =======================
-- ELIGIBILITY CACHE (ex Coverage)
-- =======================
CREATE TABLE eligibility_cache (
    id INT PRIMARY KEY AUTO_INCREMENT,
    provider ENUM('generali', 'unipolsai', 'allianz', 'axa') NOT NULL,
    insurance_type ENUM('life', 'auto', 'home', 'health') NOT NULL,
    age_min INT,
    age_max INT,
    risk_category VARCHAR(20),
    is_eligible BOOLEAN DEFAULT TRUE,
    base_premium DECIMAL(10,2),
    coverage_max DECIMAL(10,2),
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_eligibility_provider (provider, insurance_type),
    INDEX idx_eligibility_age (age_min, age_max)
);

-- =======================
-- QUOTES (ex Offers)
-- =======================
CREATE TABLE quotes (
    id INT PRIMARY KEY AUTO_INCREMENT,
    prospect_id INT NOT NULL,
    provider VARCHAR(50) NOT NULL,
    insurance_type VARCHAR(50) NOT NULL,
    monthly_premium DECIMAL(10,2) NOT NULL,
    annual_premium DECIMAL(10,2) NOT NULL,
    coverage_amount DECIMAL(10,2) NOT NULL,
    deductible DECIMAL(10,2),
    status ENUM('draft', 'sent', 'accepted', 'rejected', 'expired') DEFAULT 'draft',
    valid_until DATE,
    items JSON COMMENT 'Coverage details and add-ons',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    sent_at TIMESTAMP NULL,
    
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE,
    
    INDEX idx_quotes_prospect (prospect_id),
    INDEX idx_quotes_status (status)
);

-- =======================
-- POLICIES (ex Contracts)
-- =======================
CREATE TABLE policies (
    id INT PRIMARY KEY AUTO_INCREMENT,
    quote_id INT NOT NULL,
    policy_number VARCHAR(50) UNIQUE NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE NOT NULL,
    status ENUM('active', 'expired', 'cancelled') DEFAULT 'active',
    pdf_path VARCHAR(255),
    signed_at TIMESTAMP,
    renewal_date DATE,
    
    FOREIGN KEY (quote_id) REFERENCES quotes(id),
    
    INDEX idx_policies_number (policy_number),
    INDEX idx_policies_renewal (renewal_date)
);

-- =======================
-- COMMISSIONS
-- =======================
CREATE TABLE commissions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    prospect_id INT NOT NULL,
    broker_id INT NOT NULL,
    manager_id INT,
    affiliate_id INT,
    commission_type ENUM('initial', 'renewal_year1', 'renewal_recurring', 'referral') NOT NULL,
    amount DECIMAL(10,2) NOT NULL,
    percentage DECIMAL(5,2) NOT NULL,
    base_amount DECIMAL(10,2) NOT NULL,
    status ENUM('pending', 'approved', 'paid') DEFAULT 'pending',
    period_year INT,
    period_month INT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    paid_at TIMESTAMP NULL,
    
    FOREIGN KEY (prospect_id) REFERENCES prospects(id),
    FOREIGN KEY (broker_id) REFERENCES users(id),
    FOREIGN KEY (manager_id) REFERENCES users(id),
    FOREIGN KEY (affiliate_id) REFERENCES users(id),
    
    INDEX idx_commissions_broker (broker_id, period_year, period_month),
    INDEX idx_commissions_prospect (prospect_id)
);

-- =======================
-- ADVISORY SERVICES (ex Web & Hosting)
-- =======================
CREATE TABLE advisory_offers (
    id VARCHAR(20) PRIMARY KEY,
    prospect_id INT NOT NULL,
    service_type ENUM('financial_planning', 'investment', 'retirement', 'estate_planning') NOT NULL,
    status ENUM('draft', 'sent', 'accepted', 'closed') DEFAULT 'draft',
    total_amount DECIMAL(10,2) DEFAULT 0.00,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (prospect_id) REFERENCES prospects(id) ON DELETE CASCADE
);

-- =======================
-- USERS (unchanged structure)
-- =======================
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(100) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('admin', 'head_of_sales', 'manager', 'broker', 'affiliate') NOT NULL,
    supervisor_id INT NULL,
    is_active BOOLEAN DEFAULT TRUE,
    last_login TIMESTAMP NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    FOREIGN KEY (supervisor_id) REFERENCES users(id)
);
```

### Insurance CRM - API Endpoints

```
# Prospects Management
GET    /api/prospects              # List all prospects
GET    /api/prospects/:id          # Get prospect details
POST   /api/prospects              # Create new prospect
PUT    /api/prospects/:id          # Update prospect
DELETE /api/prospects/:id          # Delete prospect
PUT    /api/prospects/:id/status   # Update status

# Eligibility Checking
POST   /api/eligibility/check      # Check eligibility (all providers)
GET    /api/eligibility/providers  # List providers
POST   /api/eligibility/calculate  # Calculate premium estimate

# Quote Generation
POST   /api/quotes/generate        # Generate multi-provider quotes
GET    /api/quotes/:id             # Get quote details
POST   /api/quotes/:id/accept      # Accept quote
POST   /api/quotes/:id/send        # Send quote via email

# Policy Management
POST   /api/policies/generate      # Generate policy from quote
GET    /api/policies/:id           # Get policy details
GET    /api/policies/:id/pdf       # Download policy PDF

# Commissions
GET    /api/commissions/dashboard  # Commission dashboard
POST   /api/commissions/calculate  # Calculate commissions
GET    /api/commissions/report     # Generate report

# Advisory Services
POST   /api/advisory/create        # Create advisory offer
GET    /api/advisory/:id           # Get advisory details
```

---

## 📅 ROADMAP DETTAGLIATA 6-8 SETTIMANE

---

## 🗓️ SETTIMANA 1: Foundation & Quick Wins

### Obiettivi Week 1
- GitHub portfolio live
- 2 progetti pubblici funzionanti
- LinkedIn attivo
- LangChain basics

### Daily Routine
- **Mattina (1h)**: Learning LangChain docs
- **Pranzo (30m)**: LinkedIn + community
- **Sera (1h)**: Coding + documentation

---

### 📅 GIORNO 1: Setup & Networking

#### Mattina (1h): GitHub Setup

**Task 1: Create Repository**
```bash
mkdir ai-engineering-portfolio
cd ai-engineering-portfolio
git init

mkdir -p projects/{policy-rag,eligibility-agent,insurance-crm,voice-care-bot}
mkdir -p docs
touch README.md

git add .
git commit -m "Initial commit: AI Engineering Portfolio"
```

**Task 2: Professional README**
```markdown
# AI Engineering Portfolio

## About Me
AI Engineer specializing in LLM orchestration and multi-agent systems.
Background: 17 years IT infrastructure, transitioning to AI Engineering.

## Tech Stack
- **AI/ML**: LangChain, LangGraph, Claude API, Voice AI
- **Backend**: Python, FastAPI, PHP
- **Database**: MySQL, ChromaDB
- **Tools**: Git, Docker, n8n

## Featured Projects

### 1. Voice Care Bot (Week 5) 🎙️
Real-time voice AI for customer support with system integration.
[View Project →](./projects/voice-care-bot)

### 2. Insurance Comparison CRM (Weeks 2-4)
Full-stack insurance CRM with multi-agent orchestration.
[View Project →](./projects/insurance-crm)

### 3. Insurance Policy RAG System
Q&A system over insurance policy documents using RAG.
[View Project →](./projects/policy-rag)

### 4. Eligibility Checker Agent
Multi-tool agent for insurance eligibility verification.
[View Project →](./projects/eligibility-agent)

## Contact
- LinkedIn: [Your Profile]
- Email: nicola.gnasso@gmail.com
- Location: Aversa, Italy
```

**Task 3: GitHub Profile Optimization**
- Add profile photo
- Bio: "AI Engineer | LLM Orchestration, Voice AI & Multi-Agent Systems"
- Pin portfolio repo

#### Pausa Pranzo (30m): LinkedIn Optimization

**Profile Updates**:
- **Headline**: "AI Engineer | LLM Orchestration, Voice AI & Multi-Agent Systems"
- **About**:
```
AI Engineer specializing in LLM orchestration, RAG systems, voice AI, and multi-agent workflows.

17 years IT infrastructure background, now focused on building production-ready AI applications.

Currently building:
• Insurance CRM with multi-agent orchestration
• Voice AI customer care bot
• RAG systems for knowledge management

Tech: Python, LangChain, LangGraph, FastAPI, Claude API, Voice APIs
```

**Post #1**:
```
🚀 Starting my AI Engineering portfolio in public

After 17 years in IT infrastructure, I'm transitioning to AI Engineering.

Over the next 6 weeks, I'll build and share:
• RAG systems with LangChain
• Voice AI applications
• Multi-agent workflows
• Production-ready AI systems

First project: Insurance Policy Q&A with RAG

Follow along! #AIEngineering #LangChain #BuildInPublic
```

#### Sera (1h): Community Setup

**Join & Engage**:
- Discord: LangChain, n8n, LocalLLaMA, AI Engineers
- Reddit: r/LangChain, r/LocalLLaMA, r/MachineLearning
- LinkedIn: Connect 20 AI engineers (Italian market focus)

---

### 📅 GIORNO 2-3: Progetto 1 - Insurance Policy RAG

*[Same as original - omitted for brevity, full content in previous version]*

---

### 📅 GIORNO 4-5: Progetto 2 - Eligibility Checker Agent

*[Same as original - omitted for brevity]*

---

### 📅 WEEKEND WEEK 1: Publishing & Networking

*[Same as original]*

---

## 🗓️ SETTIMANA 2-4: Insurance CRM Foundation & Complete

*[Same as original - Database, API, n8n workflows, Quote system, Commission, etc.]*

---

## 🗓️ SETTIMANA 5: VOICE CARE BOT (DIFFERENZIATORE)

### Obiettivi Week 5
- Real-time voice AI conversation
- Intent recognition & troubleshooting tree
- System integration (RADIUS mock)
- State management conversazionale
- Production-ready demo

---

### 📅 GIORNO 21-22: Voice Care Bot - Setup & Architecture

#### Concept: Telco Customer Support Voice Bot

**Scenario**:
Cliente chiama per problema internet → Bot risponde vocalmente → Diagnostica → Guida alla risoluzione → Accesso RADIUS se necessario → Escalation se non risolvibile

**Features**:
1. **Voice Interface**: Speech-to-text + Text-to-speech real-time
2. **Intent Recognition**: Problema connessione / Velocità bassa / Modem spento / etc.
3. **Troubleshooting Tree**: Decision tree guidato
4. **RADIUS Integration**: Check/reset modem parameters
5. **Conversational State**: Ricorda contesto conversazione
6. **Escalation Logic**: Transfer to human operator if needed

#### Tech Stack Decision

**Option A: OpenAI Realtime API** (Recommended)
- Voice-to-voice nativo
- Low latency
- Function calling built-in
- Cost: ~$0.06/min input, ~$0.24/min output

**Option B: Assembly AI + Eleven Labs**
- Speech-to-text: Assembly AI
- Text-to-speech: Eleven Labs
- More control, more complex
- Cost simile

**Scelta**: OpenAI Realtime API per semplicità + demo quality

#### Giorno 21 Mattina: Project Setup

**Structure**:
```
projects/voice-care-bot/
├── README.md
├── requirements.txt
├── .env.example
├── app/
│   ├── main.py
│   ├── voice_handler.py
│   ├── intent_classifier.py
│   ├── troubleshooter.py
│   ├── radius_client.py (mock)
│   └── state_manager.py
├── config/
│   ├── intents.json
│   └── troubleshooting_tree.json
├── tests/
│   └── test_scenarios.py
├── recordings/  # Demo recordings
└── docs/
    └── architecture.md
```

**Requirements**:
```
openai==1.12.0
fastapi==0.104.1
uvicorn==0.24.0
websockets==12.0
python-dotenv==1.0.0
pydantic==2.5.0
```

**Environment**:
```bash
OPENAI_API_KEY=your_key_here
REALTIME_MODEL=gpt-4o-realtime-preview-2024-10-01
```

#### Giorno 21 Sera: Intent & Troubleshooting Logic

**config/intents.json**:
```json
{
  "intents": [
    {
      "name": "connection_issue",
      "keywords": ["connessione", "internet", "non funziona", "offline"],
      "priority": "high",
      "initial_question": "Vedo che hai problemi di connessione. Il modem ha le luci accese?"
    },
    {
      "name": "slow_speed",
      "keywords": ["lento", "velocità", "scarica piano", "buffering"],
      "priority": "medium",
      "initial_question": "Capisco, la connessione è lenta. Quanti dispositivi sono connessi al modem?"
    },
    {
      "name": "modem_issue",
      "keywords": ["modem", "router", "luci", "spento"],
      "priority": "high",
      "initial_question": "Problema con il modem. Che luci vedi lampeggiare?"
    },
    {
      "name": "billing_issue",
      "keywords": ["fattura", "pagamento", "costo", "addebito"],
      "priority": "low",
      "escalate": true,
      "message": "Per questioni amministrative ti metto in contatto con un operatore."
    }
  ]
}
```

**config/troubleshooting_tree.json**:
```json
{
  "connection_issue": {
    "step_1": {
      "question": "Il modem ha le luci accese?",
      "yes": "step_2",
      "no": "solution_power"
    },
    "step_2": {
      "question": "La luce internet è verde o rossa?",
      "green": "step_3",
      "red": "solution_check_cables"
    },
    "step_3": {
      "question": "Riesci a connetterti con il cavo ethernet direttamente al modem?",
      "yes": "solution_wifi_issue",
      "no": "action_radius_check"
    },
    "solution_power": {
      "message": "Prova a collegare il modem alla corrente e attendi 2 minuti.",
      "action": "wait_and_retry"
    },
    "solution_check_cables": {
      "message": "Controlla che il cavo dalla presa telefonica al modem sia ben collegato.",
      "action": "wait_customer"
    },
    "solution_wifi_issue": {
      "message": "Il problema è il WiFi. Prova a riavviare il modem tenendo premuto il tasto reset per 10 secondi.",
      "action": "reset_instructions"
    },
    "action_radius_check": {
      "message": "Controllo la tua linea dal sistema...",
      "action": "radius_diagnostic"
    }
  }
}
```

**app/intent_classifier.py**:
```python
import json
from typing import Dict, Optional

class IntentClassifier:
    def __init__(self, config_path="config/intents.json"):
        with open(config_path) as f:
            self.config = json.load(f)
        self.intents = self.config["intents"]
    
    def classify(self, user_input: str) -> Optional[Dict]:
        """Classify user intent from speech input"""
        user_input_lower = user_input.lower()
        
        # Score each intent
        scores = []
        for intent in self.intents:
            score = sum(
                1 for keyword in intent["keywords"]
                if keyword in user_input_lower
            )
            if score > 0:
                scores.append((score, intent))
        
        if scores:
            # Return highest scoring intent
            scores.sort(reverse=True, key=lambda x: x[0])
            return scores[0][1]
        
        return None
    
    def should_escalate(self, intent: Dict) -> bool:
        """Check if intent requires human escalation"""
        return intent.get("escalate", False)
    
    def get_initial_question(self, intent: Dict) -> str:
        """Get first troubleshooting question for intent"""
        return intent.get("initial_question", "Come posso aiutarti?")
```

**app/troubleshooter.py**:
```python
import json
from typing import Dict, Optional, Tuple

class Troubleshooter:
    def __init__(self, config_path="config/troubleshooting_tree.json"):
        with open(config_path) as f:
            self.trees = json.load(f)
        self.current_intent = None
        self.current_step = None
    
    def start_troubleshooting(self, intent_name: str) -> str:
        """Start troubleshooting flow for intent"""
        self.current_intent = intent_name
        self.current_step = "step_1"
        
        tree = self.trees.get(intent_name)
        if not tree:
            return "Non ho una procedura per questo problema. Ti metto in contatto con un operatore."
        
        step = tree[self.current_step]
        return step["question"]
    
    def process_response(self, user_response: str) -> Tuple[str, Optional[str]]:
        """
        Process user response and move to next step
        Returns: (message, action)
        """
        if not self.current_intent or not self.current_step:
            return ("Errore: nessuna procedura attiva", None)
        
        tree = self.trees[self.current_intent]
        current = tree[self.current_step]
        
        # Simple yes/no detection
        response_lower = user_response.lower()
        if "sì" in response_lower or "si" in response_lower or "yes" in response_lower:
            next_step = current.get("yes")
        elif "no" in response_lower:
            next_step = current.get("no")
        elif "verde" in response_lower or "green" in response_lower:
            next_step = current.get("green")
        elif "rosso" in response_lower or "rossa" in response_lower or "red" in response_lower:
            next_step = current.get("red")
        else:
            return ("Non ho capito. Puoi ripetere?", None)
        
        if not next_step:
            return ("Procedura completata.", None)
        
        next_node = tree[next_step]
        
        # Check if it's a solution or next question
        if "question" in next_node:
            self.current_step = next_step
            return (next_node["question"], None)
        else:
            # It's a solution/action
            action = next_node.get("action")
            message = next_node["message"]
            return (message, action)
    
    def reset(self):
        """Reset troubleshooting state"""
        self.current_intent = None
        self.current_step = None
```

---

### 📅 GIORNO 23: Voice Handler & RADIUS Mock

#### Giorno 23 Mattina: RADIUS Client (Mock)

**app/radius_client.py**:
```python
import random
from typing import Dict, Any
from datetime import datetime

class RADIUSClient:
    """
    Mock RADIUS client for demo purposes.
    In production, this would interface with actual RADIUS server.
    """
    
    def __init__(self):
        # Simulate customer database
        self.customers = {
            "user123": {
                "line_status": "active",
                "signal_quality": 85,
                "downstream_speed": 950,  # Mbps
                "upstream_speed": 290,
                "last_sync": "2025-10-10 14:30:00",
                "modem_model": "TIM HUB+",
                "connection_drops_24h": 0
            }
        }
    
    def check_line_status(self, customer_id: str) -> Dict[str, Any]:
        """Check customer line status from RADIUS"""
        customer = self.customers.get(customer_id, {})
        
        if not customer:
            return {
                "status": "not_found",
                "message": "Cliente non trovato nel sistema"
            }
        
        # Simulate some randomness for demo
        signal_quality = customer["signal_quality"] + random.randint(-5, 5)
        
        return {
            "status": "success",
            "data": {
                "line_status": customer["line_status"],
                "signal_quality": max(0, min(100, signal_quality)),
                "downstream_speed": customer["downstream_speed"],
                "upstream_speed": customer["upstream_speed"],
                "last_sync": customer["last_sync"],
                "connection_drops": customer["connection_drops_24h"],
                "modem_model": customer["modem_model"]
            }
        }
    
    def reset_modem(self, customer_id: str) -> Dict[str, Any]:
        """Send reset command to customer modem"""
        customer = self.customers.get(customer_id)
        
        if not customer:
            return {
                "status": "error",
                "message": "Cliente non trovato"
            }
        
        # Simulate reset
        customer["last_sync"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        customer["connection_drops_24h"] = 0
        
        return {
            "status": "success",
            "message": "Modem resettato con successo. Attendi 2 minuti per la riconnessione.",
            "estimated_time": 120  # seconds
        }
    
    def change_wifi_channel(self, customer_id: str, channel: int) -> Dict[str, Any]:
        """Change WiFi channel to reduce interference"""
        return {
            "status": "success",
            "message": f"Canale WiFi cambiato a {channel}. Dovrebbe migliorare la connessione.",
            "new_channel": channel
        }
    
    def run_speed_test(self, customer_id: str) -> Dict[str, Any]:
        """Run remote speed test"""
        customer = self.customers.get(customer_id, {})
        
        # Simulate speed test with some variance
        downstream = customer.get("downstream_speed", 100) * random.uniform(0.9, 1.0)
        upstream = customer.get("upstream_speed", 20) * random.uniform(0.9, 1.0)
        
        return {
            "status": "success",
            "data": {
                "download_speed": round(downstream, 2),
                "upload_speed": round(upstream, 2),
                "latency": random.randint(10, 30),
                "jitter": random.randint(1, 5)
            }
        }
```

#### Giorno 23 Sera: State Manager & Voice Handler

**app/state_manager.py**:
```python
from typing import Dict, Any, Optional
from datetime import datetime

class ConversationState:
    """Manage conversation state across voice interactions"""
    
    def __init__(self):
        self.customer_id: Optional[str] = None
        self.current_intent: Optional[str] = None
        self.troubleshooting_step: Optional[str] = None
        self.context: Dict[str, Any] = {}
        self.conversation_history: list = []
        self.start_time: datetime = datetime.now()
    
    def add_message(self, role: str, content: str):
        """Add message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
    
    def set_customer(self, customer_id: str):
        """Set customer ID for this conversation"""
        self.customer_id = customer_id
    
    def set_intent(self, intent: str):
        """Set current troubleshooting intent"""
        self.current_intent = intent
    
    def update_context(self, key: str, value: Any):
        """Update context with key-value pair"""
        self.context[key] = value
    
    def get_context(self, key: str) -> Any:
        """Get context value by key"""
        return self.context.get(key)
    
    def get_summary(self) -> str:
        """Get conversation summary"""
        duration = (datetime.now() - self.start_time).seconds
        return f"""
        Customer: {self.customer_id}
        Intent: {self.current_intent}
        Duration: {duration}s
        Messages: {len(self.conversation_history)}
        """
    
    def reset(self):
        """Reset state for new conversation"""
        self.__init__()


class StateManager:
    """Manage multiple conversation states"""
    
    def __init__(self):
        self.sessions: Dict[str, ConversationState] = {}
    
    def get_or_create_session(self, session_id: str) -> ConversationState:
        """Get existing session or create new one"""
        if session_id not in self.sessions:
            self.sessions[session_id] = ConversationState()
        return self.sessions[session_id]
    
    def end_session(self, session_id: str):
        """End and cleanup session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
```

**app/voice_handler.py**:
```python
from openai import OpenAI
import json
from typing import Dict, Any
from app.intent_classifier import IntentClassifier
from app.troubleshooter import Troubleshooter
from app.radius_client import RADIUSClient
from app.state_manager import StateManager

class VoiceHandler:
    """Handle voice interactions with OpenAI Realtime API"""
    
    def __init__(self):
        self.client = OpenAI()
        self.intent_classifier = IntentClassifier()
        self.troubleshooter = Troubleshooter()
        self.radius = RADIUSClient()
        self.state_manager = StateManager()
        
        # Define tools for function calling
        self.tools = [
            {
                "type": "function",
                "name": "check_line_status",
                "description": "Check customer's internet line status and quality from RADIUS server",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer ID"
                        }
                    },
                    "required": ["customer_id"]
                }
            },
            {
                "type": "function",
                "name": "reset_modem",
                "description": "Remotely reset customer's modem",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer ID"
                        }
                    },
                    "required": ["customer_id"]
                }
            },
            {
                "type": "function",
                "name": "run_speed_test",
                "description": "Run remote speed test on customer's line",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "customer_id": {
                            "type": "string",
                            "description": "Customer ID"
                        }
                    },
                    "required": ["customer_id"]
                }
            }
        ]
    
    def handle_function_call(self, function_name: str, arguments: Dict) -> str:
        """Execute function call and return result"""
        if function_name == "check_line_status":
            result = self.radius.check_line_status(arguments["customer_id"])
            return json.dumps(result)
        
        elif function_name == "reset_modem":
            result = self.radius.reset_modem(arguments["customer_id"])
            return json.dumps(result)
        
        elif function_name == "run_speed_test":
            result = self.radius.run_speed_test(arguments["customer_id"])
            return json.dumps(result)
        
        return json.dumps({"error": "Unknown function"})
    
    def create_system_prompt(self) -> str:
        """Create system prompt for voice assistant"""
        return """Sei un assistente vocale per supporto tecnico telecomunicazioni.

Il tuo ruolo:
- Aiutare i clienti a risolvere problemi di connessione internet
- Guidarli passo-passo con domande chiare
- Usare un tono amichevole e professionale
- Parlare in italiano
- Essere paziente e comprensivo

Quando il cliente descrive un problema:
1. Classifica il tipo di problema (connessione, velocità, modem, ecc.)
2. Fai domande diagnostiche specifiche
3. Se necessario, usa gli strumenti RADIUS per controllare la linea
4. Guida il cliente alla soluzione
5. Se non riesci a risolvere, offri di trasferire a un operatore umano

Mantieni le risposte brevi e chiare per il dialogo vocale."""
    
    async def start_conversation(self, session_id: str, customer_id: str):
        """Start a new voice conversation"""
        state = self.state_manager.get_or_create_session(session_id)
        state.set_customer(customer_id)
        
        # Initial greeting
        greeting = f"Ciao! Sono l'assistente virtuale. Come posso aiutarti oggi?"
        state.add_message("assistant", greeting)
        
        return greeting
    
    def process_user_speech(self, session_id: str, transcript: str) -> Dict[str, Any]:
        """Process user speech and determine response"""
        state = self.state_manager.get_or_create_session(session_id)
        state.add_message("user", transcript)
        
        # Classify intent if not already set
        if not state.current_intent:
            intent = self.intent_classifier.classify(transcript)
            
            if intent:
                state.set_intent(intent["name"])
                
                # Check if should escalate
                if self.intent_classifier.should_escalate(intent):
                    response = intent["message"]
                    action = "escalate"
                else:
                    # Start troubleshooting
                    response = self.troubleshooter.start_troubleshooting(intent["name"])
                    action = "troubleshoot"
            else:
                response = "Non ho capito bene il problema. Puoi descriverlo in modo diverso?"
                action = "clarify"
        else:
            # Continue troubleshooting
            response, action = self.troubleshooter.process_response(transcript)
        
        state.add_message("assistant", response)
        
        return {
            "response": response,
            "action": action,
            "intent": state.current_intent
        }
```

---

### 📅 GIORNO 24: Integration & Testing

#### Giorno 24: FastAPI Application

**app/main.py**:
```python
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import json
import asyncio
from typing import Dict

from app.voice_handler import VoiceHandler

app = FastAPI(title="Voice Care Bot")

voice_handler = VoiceHandler()
active_sessions: Dict[str, WebSocket] = {}

@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Voice Care Bot</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                text-align: center;
            }
            .status {
                padding: 20px;
                margin: 20px 0;
                border-radius: 8px;
                background: #f0f0f0;
            }
            button {
                padding: 15px 30px;
                font-size: 18px;
                margin: 10px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
            }
            .start-btn {
                background: #4CAF50;
                color: white;
            }
            .stop-btn {
                background: #f44336;
                color: white;
            }
            .transcript {
                margin-top: 20px;
                padding: 15px;
                background: #e3f2fd;
                border-radius: 8px;
                text-align: left;
                max-height: 400px;
                overflow-y: auto;
            }
            .message {
                margin: 10px 0;
                padding: 10px;
                border-radius: 4px;
            }
            .user {
                background: #c8e6c9;
            }
            .assistant {
                background: #bbdefb;
            }
        </style>
    </head>
    <body>
        <h1>🎙️ Voice Care Bot Demo</h1>
        <div class="status" id="status">Ready to start</div>
        
        <button class="start-btn" onclick="startCall()">Start Call</button>
        <button class="stop-btn" onclick="stopCall()">End Call</button>
        
        <div class="transcript" id="transcript"></div>
        
        <script>
            let ws = null;
            let mediaRecorder = null;
            let audioChunks = [];
            
            async function startCall() {
                document.getElementById('status').textContent = 'Connecting...';
                
                // Connect WebSocket
                ws = new WebSocket('ws://localhost:8000/ws/voice');
                
                ws.onopen = () => {
                    document.getElementById('status').textContent = 'Connected! Speak now...';
                    startRecording();
                };
                
                ws.onmessage = (event) => {
                    const data = JSON.parse(event.data);
                    addMessage('assistant', data.response);
                    
                    if (data.action === 'escalate') {
                        document.getElementById('status').textContent = 'Transferring to operator...';
                        setTimeout(stopCall, 2000);
                    }
                };
                
                ws.onclose = () => {
                    document.getElementById('status').textContent = 'Call ended';
                };
            }
            
            async function startRecording() {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                
                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };
                
                mediaRecorder.onstop = async () => {
                    const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
                    // Send to server for transcription
                    // For demo, we'll use text input instead
                };
                
                mediaRecorder.start();
            }
            
            function stopCall() {
                if (mediaRecorder && mediaRecorder.state !== 'inactive') {
                    mediaRecorder.stop();
                }
                if (ws) {
                    ws.close();
                }
                document.getElementById('status').textContent = 'Call ended';
            }
            
            function addMessage(role, content) {
                const transcript = document.getElementById('transcript');
                const message = document.createElement('div');
                message.className = `message ${role}`;
                message.textContent = `${role.toUpperCase()}: ${content}`;
                transcript.appendChild(message);
                transcript.scrollTop = transcript.scrollHeight;
            }
            
            // For demo: simulate with text input
            setTimeout(() => {
                const input = prompt("Describe your problem (in Italian):");
                if (input && ws) {
                    addMessage('user', input);
                    ws.send(JSON.stringify({ text: input }));
                }
            }, 3000);
        </script>
    </body>
    </html>
    """

@app.websocket("/ws/voice")
async def voice_endpoint(websocket: WebSocket):
    await websocket.accept()
    session_id = str(id(websocket))
    active_sessions[session_id] = websocket
    
    try:
        # Start conversation
        greeting = await voice_handler.start_conversation(session_id, "user123")
        await websocket.send_json({
            "response": greeting,
            "action": "greeting"
        })
        
        while True:
            # Receive data from client
            data = await websocket.receive_json()
            transcript = data.get("text", "")
            
            # Process speech
            result = voice_handler.process_user_speech(session_id, transcript)
            
            # Send response
            await websocket.send_json(result)
            
            # If action requires RADIUS, execute
            if result.get("action") == "radius_diagnostic":
                state = voice_handler.state_manager.get_or_create_session(session_id)
                customer_id = state.customer_id
                
                # Check line status
                line_status = voice_handler.radius.check_line_status(customer_id)
                
                # Interpret results
                if line_status["status"] == "success":
                    data = line_status["data"]
                    interpretation = f"""Ho controllato la tua linea. 
                    Qualità segnale: {data['signal_quality']}%. 
                    Velocità: {data['downstream_speed']} Mbps in download.
                    {'Tutto sembra normale.' if data['signal_quality'] > 80 else 'Rilevato problema di segnale.'}
                    """
                else:
                    interpretation = "Non riesco ad accedere ai dati della linea."
                
                await websocket.send_json({
                    "response": interpretation,
                    "action": "continue"
                })
    
    except WebSocketDisconnect:
        voice_handler.state_manager.end_session(session_id)
        if session_id in active_sessions:
            del active_sessions[session_id]

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "active_sessions": len(active_sessions)
    }
```

#### Testing Scenarios

**Test 1: Connection Issue**
```
User: "Non ho internet, non funziona niente"
Bot: "Vedo che hai problemi di connessione. Il modem ha le luci accese?"
User: "Sì, sono accese"
Bot: "La luce internet è verde o rossa?"
User: "Rossa"
Bot: "Controlla che il cavo dalla presa telefonica al modem sia ben collegato."
```

**Test 2: Slow Speed with RADIUS**
```
User: "Internet è molto lento"
Bot: "Capisco, la connessione è lenta. Controllo la tua linea dal sistema..."
[RADIUS check]
Bot: "Ho controllato. Qualità segnale: 72%. Velocità: 450 Mbps. 
     Rilevato problema di segnale. Provo a resettare il modem?"
User: "Sì"
[RADIUS reset]
Bot: "Modem resettato. Attendi 2 minuti per la riconnessione."
```

---

### 📅 GIORNO 25: Documentation & Demo

**README.md**:
```markdown
# 🎙️ Voice Care Bot

Real-time voice AI assistant for telecommunications customer support.

## Features
- **Voice Interface**: Speech-to-text and text-to-speech
- **Intent Recognition**: Automatic problem classification
- **Troubleshooting Tree**: Guided problem resolution
- **System Integration**: RADIUS server access (mock)
- **State Management**: Conversational context retention
- **Smart Escalation**: Transfer to human when needed

## Architecture

\`\`\`
Customer Call → Voice Interface → Intent Classifier →
Troubleshooting Engine → RADIUS Integration →
Solution / Escalation
\`\`\`

## Tech Stack
- OpenAI Realtime API (voice)
- FastAPI + WebSocket
- State management system
- RADIUS client (mock)

## Supported Scenarios
1. Connection issues (no internet)
2. Slow speed problems
3. Modem/router troubleshooting
4. WiFi connectivity issues

## Demo
[Link to video demo]

## Production Considerations
- Real RADIUS integration needed
- Authentication & authorization
- Call recording & compliance
- Fallback to human operators
- Multi-language support

## Skills Demonstrated
- Real-time voice AI
- System integration
- Conversational state management
- Function calling
- Decision trees
```

**Create Demo Video**:
- Screen record call simulation
- Show different scenarios
- Demonstrate RADIUS integration
- Show escalation flow

---

### WEEKEND WEEK 5: Publishing

**LinkedIn Post #6**:
```
🎙️ Built a Voice AI Customer Support Bot

Real-time voice assistant that:
• Understands customer problems (Italian)
• Guides through troubleshooting steps
• Integrates with backend systems (RADIUS)
• Escalates to humans when needed

Tech: OpenAI Realtime API + function calling + state management

Why voice AI matters:
✓ 24/7 availability
✓ Instant response
✓ System integration
✓ Natural interaction

This is the future of customer support.

[Demo video]
[GitHub]

#VoiceAI #CustomerSupport #AIEngineering
```

---

### KPI Week 5 - CHECK ✓
- [ ] Voice Care Bot complete & deployed
- [ ] Video demo published
- [ ] Documentation comprehensive
- [ ] LinkedIn post with engagement
- [ ] 5 progetti totali portfolio
- [ ] Differenziatore chiaro (voice AI)

---

## 🗓️ SETTIMANA 6: Multi-Agent + Advisory + Optimization

### Obiettivi Week 6
- LangGraph multi-agent orchestration
- Advisory services module (Insurance CRM)
- Production optimization
- Advanced RAG improvements

---

### 📅 GIORNO 26-27: LangGraph Multi-Agent

**Progetto: Insurance Advisory Multi-Agent System**

**Concept**: 
Team di 3 agenti specializzati che collaborano per advisory completo:
1. **Risk Analyzer**: Analizza profilo cliente e rischi
2. **Product Matcher**: Trova prodotti assicurativi ottimali
3. **Advisor**: Genera raccomandazioni personalizzate

**Architecture**:
```
Customer Profile → Risk Analyzer → Product Matcher → Advisor → Report
                        ↓                ↓              ↓
                   [Risk Assessment] [Product List] [Recommendations]
```

**Implementation**:
```python
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class AdvisoryState(TypedDict):
    customer_profile: dict
    risk_assessment: dict
    recommended_products: List[dict]
    advisory_report: str
    messages: List[dict]

# Define agents
def risk_analyzer_node(state: AdvisoryState):
    # LangChain agent per risk analysis
    ...

def product_matcher_node(state: AdvisoryState):
    # LangChain agent per product recommendation
    ...

def advisor_node(state: AdvisoryState):
    # LangChain agent per final advisory
    ...

# Build graph
workflow = StateGraph(AdvisoryState)
workflow.add_node("analyze_risk", risk_analyzer_node)
workflow.add_node("match_products", product_matcher_node)
workflow.add_node("generate_advisory", advisor_node)

workflow.add_edge("analyze_risk", "match_products")
workflow.add_edge("match_products", "generate_advisory")
workflow.add_edge("generate_advisory", END)

workflow.set_entry_point("analyze_risk")

advisory_system = workflow.compile()
```

*[Full implementation details...]*

---

### 📅 GIORNO 28-29: Advisory Services Module

**Integration with Insurance CRM**:
- Advisory offers database table
- API endpoints
- PDF generation for advisory reports
- Commission calculation

*[Implementation details...]*

---

### 📅 GIORNO 30: Production Optimization

**Tasks**:
- Query optimization (database indexes)
- Caching strategy (Redis-ready)
- API rate limiting
- Error handling comprehensive
- Logging structured
- Monitoring setup

---

### WEEKEND WEEK 6: Polish & Deploy

**Tasks**:
- Deploy all projects live
- Update all README files
- Create architecture diagrams
- LinkedIn posts (2-3)

---

### KPI Week 6 - CHECK ✓
- [ ] Multi-agent system working
- [ ] Advisory module complete
- [ ] All projects deployed
- [ ] 7+ progetti portfolio
- [ ] Performance optimized
- [ ] 10+ LinkedIn posts totali

---

## 🗓️ SETTIMANA 7-8: Job Ready

### Week 7: Portfolio Polish

**Tasks**:
- Complete all documentation
- Create demo videos (all projects)
- Write 3 blog posts
- LinkedIn content series
- Portfolio website (optional)

### Week 8: Applications & Interviews

**Tasks**:
- CV optimization
- 30+ applications
- Interview preparation
- Mock interviews
- Follow-ups

---

## 📚 RISORSE COMPLETE

### Voice AI Resources
- OpenAI Realtime API: https://platform.openai.com/docs/guides/realtime
- WebRTC Guide: https://webrtc.org/getting-started/overview
- Speech Recognition: https://developer.mozilla.org/en-US/docs/Web/API/Web_Speech_API

### LangChain Documentation
- Main: https://python.langchain.com
- LangGraph: https://langchain-ai.github.io/langgraph/
- Agents: https://python.langchain.com/docs/modules/agents/
- RAG: https://python.langchain.com/docs/tutorials/rag/

### Anthropic Resources
- Docs: https://docs.anthropic.com
- Cookbook: https://github.com/anthropics/anthropic-cookbook

### Communities
- Discord: LangChain, n8n, LocalLLaMA, AI Engineers
- Reddit: r/LangChain, r/LocalLLaMA, r/MachineLearning

### Job Boards Italia
- LinkedIn Jobs
- Wellfound
- AIJobs.net
- Stack Overflow Jobs

---

## 📝 PROGETTI QUICK REFERENCE

| Week | Progetti | Skills Demonstrated |
|------|----------|-------------------|
| 1 | Policy RAG + Eligibility Agent | LangChain, RAG, Function calling |
| 2-4 | Insurance CRM | Full-stack, Production architecture, Domain adaptation |
| 5 | Voice Care Bot | Voice AI, Real-time, System integration |
| 6 | Multi-agent + Advisory | LangGraph, Multi-agent orchestration |
| 7-8 | Portfolio + Jobs | Professional presentation |

---

## ✅ FINAL CHECKLIST (Week 8)

### Portfolio Ready
- [ ] 8-9 progetti pubblici
- [ ] Insurance CRM deployed
- [ ] Voice Care Bot demo video
- [ ] All README professional
- [ ] Architecture diagrams

### Differenziatori
- [ ] Voice AI (pochi hanno)
- [ ] Production architecture (Insurance CRM)
- [ ] Domain adaptation (Telco → Insurance)
- [ ] Multi-agent orchestration

### Job Ready
- [ ] CV updated
- [ ] 30+ applications
- [ ] Interview prep complete
- [ ] Network 100+ connections

---

## 💰 SUCCESS FORMULA

**Input**: 150-200h over 6-8 weeks  
**Differenziatore**: Voice Care Bot (unique)  
**Output**: €50k+ AI Engineer position

**€30k → €50k+ = 67% increase = Life changing**

---

**Master Document Version 1.1 (Voice Care Bot Edition)**  
*Last Updated: Pre-Week 5*  
*Save and re-upload for full context*

🚀 **Ready to start Monday!**


---

## 🏠 PROGETTO BONUS: HOME THEATER AI CONSULTANT

### Overview
**Purpose**: Demonstrate AI skill versatility in non-insurance domain
**Timeline**: Week 5-6 (1 week implementation)
**Value**: Personal story + broader appeal + same core AI skills

### Problem Statement
Users with large/complex rooms don't know:
- What audio equipment to buy
- How many devices needed
- Where to position them
- Budget allocation

### Solution Architecture
Multi-agent system for home theater consultation:

```
User Input (room planimetry + preferences)
    ↓
Room Analyzer Agent
  - Analyzes room dimensions, acoustics
  - RAG: acoustic principles database
    ↓
Budget Optimizer Agent
  - Allocates budget across components
  - Considers user preferences (quality vs quantity)
    ↓
Product Research Agent
  - RAG: product catalog + reviews database
  - Recommends specific models
    ↓
Installation Planner Agent
  - Generates positioning recommendations
  - Tool: geometric calculations
    ↓
Orchestrator (LangGraph)
  - Synthesizes all agent outputs
  - Generates comprehensive report
```

### Tech Stack
- **LangChain/LangGraph**: Multi-agent orchestration
- **RAG**:
  - Acoustic knowledge base
  - Product catalog database
  - User reviews corpus
- **Tools**: Geometric/spatial calculations
- **Frontend**: Interactive room planner (canvas/SVG)
- **Backend**: FastAPI

### Key Features
1. **Room Planner**: Upload/draw room dimensions
2. **Preference Input**: Budget, use case, preferences
3. **Multi-Agent Analysis**: Comprehensive evaluation
4. **Product Recommendations**: Specific models with rationale
5. **Installation Guide**: Step-by-step positioning
6. **Budget Breakdown**: Cost allocation explanation

### Demonstrates (Same Skills as Insurance Projects)
- ✅ Multi-agent orchestration (LangGraph)
- ✅ RAG systems (multiple knowledge bases)
- ✅ Tool calling (calculations)
- ✅ Production deployment
- ✅ Clean architecture

### Differentiation Value
- **Personal story**: Authentic problem-solving
- **Broader appeal**: Not all recruiters are insurance-focused
- **Memorability**: "The home theater AI guy"
- **Versatility proof**: Can apply AI to any domain

### Implementation Notes
*Detailed architecture to be designed during Week 5 based on Insurance CRM learnings*