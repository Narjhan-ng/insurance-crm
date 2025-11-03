# Frontend Development - Starting Point

**Date**: November 3, 2025
**Status**: Backend Complete ✅ | Testing Complete ✅ | Ready for Frontend 🚀
**Backend Server**: Running on `http://localhost:8001`
**API Docs**: `http://localhost:8001/docs` (Swagger UI)

---

## 📋 Table of Contents

1. [Backend Status Summary](#backend-status-summary)
2. [Available APIs](#available-apis)
3. [Technology Stack (Frontend)](#technology-stack-frontend)
4. [User Roles & Dashboards](#user-roles--dashboards)
5. [Implementation Roadmap](#implementation-roadmap)
6. [Design System](#design-system)
7. [Quick Start Commands](#quick-start-commands)

---

## 🎯 Backend Status Summary

### What's Ready

**✅ Completed Backend Modules (9 modules)**:
1. ✅ **Prospect Management** - CRUD + event-driven workflows
2. ✅ **Eligibility System** - 4 provider rules, instant pre-qualification
3. ✅ **AI Quote Generation** - LangChain + Claude for intelligent comparison
4. ✅ **Policy Management** - Contract creation, PDF generation
5. ✅ **Authentication** - JWT + bcrypt, role-based access control
6. ✅ **Dashboard** - Role-specific KPIs (broker/manager/admin)
7. ✅ **Commission System** - Multi-tier calculation (broker/manager/affiliate)
8. ✅ **Reports Module** - Sales analytics, commission tracking
9. ✅ **LangGraph Advisory** - Multi-step AI workflow for personalized recommendations

**✅ Testing Coverage**:
- 66 tests, 100% passing
- 97-100% coverage on critical services (eligibility, auth, commission)
- Fast test suite (4.15 seconds)

**✅ Production-Ready Features**:
- Event-driven architecture (Redis Streams + ARQ)
- Complete audit trail (Event Store)
- Fault-tolerant design
- Structured AI outputs (Pydantic validation)

---

## 🔌 Available APIs

### Base URL
```
http://localhost:8001/api/v1
```

### Authentication APIs

**POST** `/auth/register`
```json
{
  "username": "john_broker",
  "email": "john@example.com",
  "password": "SecurePass123!",
  "role": "broker"
}
```

**POST** `/auth/login`
```json
{
  "username": "john_broker",
  "password": "SecurePass123!"
}
// Returns: {"access_token": "eyJ...", "token_type": "bearer"}
```

**GET** `/auth/me` (requires token)
```
Authorization: Bearer eyJ...
// Returns current user info
```

---

### Prospect APIs

**POST** `/prospects` (create)
```json
{
  "type": "individual",
  "first_name": "Marco",
  "last_name": "Rossi",
  "birth_date": "1985-06-15",
  "email": "marco.rossi@example.com",
  "phone": "+39 340 1234567",
  "tax_code": "RSSMRC85H15H501Z",
  "risk_category": "medium",
  "notes": "Interested in life insurance"
}
```

**GET** `/prospects` (list with filters)
```
?status=new&assigned_broker=1&limit=20&offset=0
```

**GET** `/prospects/{id}` (single)

**PUT** `/prospects/{id}` (update)

**GET** `/prospects/{id}/activity` (activity feed)

---

### Eligibility APIs

**POST** `/eligibility/check`
```json
{
  "prospect_id": 1,
  "insurance_type": "life"
}
// Returns: Eligibility for 4 providers (Generali, Allianz, AXA, UnipolSai)
```

**Response**:
```json
{
  "eligible_count": 2,
  "ineligible_count": 2,
  "providers": [
    {
      "provider": "generali",
      "is_eligible": true,
      "base_premium": 760.00,
      "coverage_max": 500000,
      "reason": "All criteria met"
    },
    {
      "provider": "axa",
      "is_eligible": false,
      "reason": "Age 72 exceeds maximum 65"
    }
  ],
  "best_provider": "generali",
  "lowest_premium": 760.00
}
```

---

### Quote APIs

**POST** `/quotes/generate` (AI-powered)
```json
{
  "prospect_id": 1,
  "insurance_type": "life",
  "coverage_amount": 500000,
  "coverage_years": 20
}
// Takes ~3 seconds (AI processing)
```

**Response**:
```json
{
  "quotes": [
    {
      "id": 1,
      "provider": "generali",
      "monthly_premium": 85.50,
      "annual_premium": 1026.00,
      "ai_score": 92.0,
      "ai_reasoning": {
        "pros": ["Best coverage for age group", "Competitive pricing"],
        "cons": ["Slightly higher deductible"],
        "reasoning": "Generali offers the best value..."
      }
    }
  ],
  "recommended_quote_id": 1,
  "comparison_summary": "Generali is recommended..."
}
```

**GET** `/quotes?prospect_id=1` (list)

**GET** `/quotes/{id}` (single)

---

### Policy APIs

**POST** `/policies/{quote_id}/accept`
```json
{
  "quote_id": 1
}
// Creates policy, triggers PDF generation (async)
```

**Response**:
```json
{
  "policy": {
    "id": 1,
    "policy_number": "POL-2025-000123",
    "status": "active",
    "start_date": "2025-11-03",
    "end_date": "2026-11-03",
    "annual_premium": 1026.00
  },
  "message": "Policy created successfully. PDF generation in progress."
}
```

**GET** `/policies` (list)

**GET** `/policies/{id}` (single)

**GET** `/policies/{id}/pdf` (download PDF contract)

---

### Dashboard APIs

**GET** `/dashboard/broker` (broker dashboard)
```
Authorization: Bearer <token>
?period=month  // today | week | month
```

**Response**:
```json
{
  "pipeline": {
    "new_prospects": 12,
    "contacted": 8,
    "quoted": 5,
    "policies_signed": 2,
    "conversion_rate": 16.7
  },
  "commissions": {
    "pending": 1500.00,
    "approved": 800.00,
    "paid": 3200.00,
    "total": 5500.00
  },
  "recent_activity": [...]
}
```

**GET** `/dashboard/manager` (manager dashboard)
```json
{
  "team_pipeline": {...},
  "team_commissions": {...},
  "top_brokers": [
    {"name": "John Doe", "policies": 5, "commission": 2500.00}
  ]
}
```

**GET** `/dashboard/admin` (admin dashboard)
```json
{
  "company_stats": {...},
  "all_brokers_ranking": [...]
}
```

---

### Reports APIs

**GET** `/reports/sales` (sales report)
```
?start_date=2025-10-01&end_date=2025-10-31&group_by=broker
```

**GET** `/reports/commissions` (commission report)
```
?start_date=2025-10-01&end_date=2025-10-31&broker_id=1
```

**Response**:
```json
{
  "total_commission": 5500.00,
  "breakdown": {
    "initial": 3500.00,
    "renewal_year1": 1500.00,
    "renewal_recurring": 500.00
  },
  "by_status": {
    "pending": 1500.00,
    "approved": 800.00,
    "paid": 3200.00
  },
  "commissions": [...]
}
```

---

### Advisory APIs (LangGraph AI Workflow)

**POST** `/advisory/generate`
```json
{
  "prospect_id": 1,
  "insurance_type": "life"
}
// Multi-step AI workflow: profile → eligibility → risk analysis → recommendations
```

**Response**:
```json
{
  "prospect_id": 1,
  "insurance_type": "life",
  "profile": {
    "age": 40,
    "risk_category": "medium",
    "has_conditions": false
  },
  "eligible_providers": [...],
  "risk_analysis": {
    "risk_score": 35.0,
    "risk_factors": ["Age within optimal range", "No pre-existing conditions"],
    "mitigation_suggestions": ["Regular health checkups"],
    "overall_assessment": "Low to medium risk profile..."
  },
  "recommendations": {
    "providers": [
      {
        "provider": "generali",
        "rank": 1,
        "score": 92.0,
        "pros": ["Best coverage", "Competitive pricing"],
        "cons": ["Slightly higher deductible"],
        "reasoning": "..."
      }
    ],
    "overall_recommendation": "We recommend Generali..."
  },
  "personalized_message": {
    "greeting": "Dear Marco,",
    "body": "Based on your profile...",
    "call_to_action": "Schedule a call to discuss details."
  },
  "workflow_path": ["profile_extractor", "eligibility_checker", "risk_analyzer", "recommendation_generator", "personalizer"]
}
```

---

## 🛠️ Technology Stack (Frontend)

### Recommended Stack

**Framework**: **Next.js 14+** (App Router)
- Server-side rendering for SEO
- API routes for BFF pattern (Backend for Frontend)
- Built-in optimization (images, fonts)
- TypeScript support

**UI Library**: **shadcn/ui** + **Tailwind CSS**
- Copy-paste components (not npm package)
- Fully customizable
- Accessible (ARIA compliant)
- Beautiful defaults

**State Management**: **Zustand** (lightweight) or **TanStack Query** (server state)
- Zustand: Client state (user session, UI state)
- TanStack Query: Server state (API data, caching)

**Form Management**: **React Hook Form** + **Zod**
- Type-safe validation
- Performance optimized
- Easy integration with shadcn/ui

**Charts**: **Recharts** or **Chart.js**
- Dashboard KPI visualizations
- Sales trend graphs

**Tables**: **TanStack Table** (React Table v8)
- Sorting, filtering, pagination
- Column visibility, row selection

**Authentication**: **NextAuth.js** (optional) or custom JWT
- Session management
- Protected routes

---

## 👥 User Roles & Dashboards

### Role Hierarchy

```
Admin
  ↓
Manager
  ↓
Broker
  ↓
Affiliate
```

### Dashboard Requirements by Role

#### **Broker Dashboard**
**URL**: `/dashboard/broker`

**KPIs**:
- My Pipeline (new/contacted/quoted/signed)
- Conversion Rate
- My Commissions (pending/approved/paid)

**Components**:
- Prospect list (assigned to me)
- Recent activity feed
- Commission summary cards
- Quick actions (create prospect, generate quote)

**Actions**:
- Create new prospect
- Generate quotes
- Accept quotes → create policy
- View my commissions

---

#### **Manager Dashboard**
**URL**: `/dashboard/manager`

**KPIs**:
- Team Pipeline (aggregated)
- Team Conversion Rate
- Team Commissions
- Top Brokers Ranking

**Components**:
- Team performance chart
- Broker comparison table
- Team activity feed
- Commission approval queue

**Actions**:
- View team prospects
- Approve commissions
- View detailed broker performance
- Assign prospects to brokers

---

#### **Admin Dashboard**
**URL**: `/dashboard/admin`

**KPIs**:
- Company-wide Stats
- All Brokers Ranking
- Total Commissions
- Revenue Analytics

**Components**:
- Company overview charts
- All brokers ranking
- System health metrics
- User management

**Actions**:
- Manage users (create, deactivate)
- View all prospects/policies
- System configuration
- Export reports

---

## 🗺️ Implementation Roadmap

### Phase 1: Foundation (Week 1)
**Goal**: Setup + Authentication

**Tasks**:
1. Initialize Next.js project with TypeScript
2. Setup Tailwind CSS + shadcn/ui
3. Create project structure (components, lib, hooks)
4. Implement authentication flow:
   - Login page
   - Register page
   - Protected route wrapper
   - JWT token storage (httpOnly cookies or localStorage)
5. Create main layout (sidebar, navbar, user menu)

**Deliverables**:
- ✅ User can register
- ✅ User can login
- ✅ Protected routes redirect to login
- ✅ Basic navigation (sidebar)

---

### Phase 2: Broker Dashboard (Week 2)
**Goal**: Core broker workflow

**Tasks**:
1. Broker dashboard page with KPIs
2. Prospect management:
   - List prospects (table with filters)
   - Create prospect (form with validation)
   - View prospect details (modal or page)
   - Edit prospect
3. Eligibility check UI:
   - Select insurance type
   - Show eligibility results (4 providers)
   - Visual comparison (cards)
4. Quote generation UI:
   - Generate quotes button
   - Loading state (AI processing ~3s)
   - Quote comparison table
   - AI reasoning display

**Deliverables**:
- ✅ Broker can manage prospects
- ✅ Broker can check eligibility
- ✅ Broker can generate AI quotes

---

### Phase 3: Policy & Commissions (Week 3)
**Goal**: Complete sales cycle

**Tasks**:
1. Accept quote → create policy:
   - Quote acceptance modal
   - Policy confirmation
   - PDF download link
2. Policy list & details:
   - Policy table (active/expired)
   - Policy detail page
   - PDF viewer
3. Commission tracking:
   - Commission list (pending/approved/paid)
   - Commission details modal
   - Filter by date range

**Deliverables**:
- ✅ Broker can accept quotes
- ✅ Broker can view policies
- ✅ Broker can track commissions

---

### Phase 4: Manager Dashboard (Week 4)
**Goal**: Team management

**Tasks**:
1. Manager dashboard with team KPIs
2. Team performance charts:
   - Conversion funnel visualization
   - Broker comparison bar chart
3. Top brokers ranking table
4. Commission approval workflow:
   - Pending commissions table
   - Approve/reject buttons
   - Approval confirmation

**Deliverables**:
- ✅ Manager can view team stats
- ✅ Manager can approve commissions

---

### Phase 5: Admin & Reports (Week 5)
**Goal**: System administration

**Tasks**:
1. Admin dashboard with company stats
2. User management:
   - User list (all roles)
   - Create user
   - Deactivate user
3. Reports page:
   - Sales report (date range, filters)
   - Commission report (date range, broker)
   - Export to CSV/PDF

**Deliverables**:
- ✅ Admin can manage users
- ✅ Admin can generate reports

---

### Phase 6: AI Advisory Interface (Week 6)
**Goal**: LangGraph workflow UI

**Tasks**:
1. Advisory generation UI:
   - Start advisory workflow button
   - Loading state with progress steps
   - Display workflow path
2. Advisory results page:
   - Profile summary
   - Risk analysis card
   - Provider recommendations with reasoning
   - Personalized message
3. Save advisory as PDF (optional)

**Deliverables**:
- ✅ User can generate AI advisory
- ✅ User can view multi-step workflow results

---

### Phase 7: Polish & UX (Week 7)
**Goal**: Production-ready UI

**Tasks**:
1. Responsive design (mobile/tablet)
2. Loading states & skeletons
3. Error handling & toast notifications
4. Accessibility improvements
5. Performance optimization:
   - Image optimization
   - Code splitting
   - Route prefetching

**Deliverables**:
- ✅ Mobile-responsive
- ✅ Excellent UX (no jarring states)
- ✅ Accessible (keyboard nav, ARIA)

---

## 🎨 Design System

### Color Palette (Example)

**Primary**: Blue (trust, insurance industry)
```
50:  #eff6ff
100: #dbeafe
500: #3b82f6  (main)
700: #1d4ed8
900: #1e3a8a
```

**Success**: Green (approved, eligible)
```
500: #10b981
```

**Warning**: Yellow (pending)
```
500: #f59e0b
```

**Danger**: Red (rejected, ineligible)
```
500: #ef4444
```

**Neutral**: Gray (text, backgrounds)
```
50:  #f9fafb
100: #f3f4f6
500: #6b7280
900: #111827
```

---

### Component Library (shadcn/ui)

**Install shadcn/ui**:
```bash
npx shadcn-ui@latest init
```

**Components to add**:
```bash
npx shadcn-ui@latest add button
npx shadcn-ui@latest add input
npx shadcn-ui@latest add label
npx shadcn-ui@latest add form
npx shadcn-ui@latest add card
npx shadcn-ui@latest add table
npx shadcn-ui@latest add dialog
npx shadcn-ui@latest add dropdown-menu
npx shadcn-ui@latest add badge
npx shadcn-ui@latest add tabs
npx shadcn-ui@latest add select
npx shadcn-ui@latest add toast
npx shadcn-ui@latest add alert
npx shadcn-ui@latest add skeleton
```

---

### Typography

**Font**: Inter (clean, modern, professional)
```tsx
import { Inter } from 'next/font/google'

const inter = Inter({ subsets: ['latin'] })
```

**Headings**:
- H1: 2.25rem (36px) - Page titles
- H2: 1.875rem (30px) - Section headers
- H3: 1.5rem (24px) - Card titles
- Body: 1rem (16px) - Default text
- Small: 0.875rem (14px) - Captions

---

### Layout Structure

```
┌─────────────────────────────────────────────┐
│  Navbar (logo, user menu, notifications)   │
├──────────┬──────────────────────────────────┤
│ Sidebar  │  Main Content Area              │
│          │                                  │
│ - Home   │  ┌────────────────────────────┐ │
│ - Prosp  │  │  Page Title                │ │
│ - Quotes │  ├────────────────────────────┤ │
│ - Policy │  │  KPI Cards Row             │ │
│ - Comm   │  │  [Card] [Card] [Card]      │ │
│ - Report │  ├────────────────────────────┤ │
│          │  │  Main Content (table/form) │ │
│          │  │                            │ │
│          │  │                            │ │
│          │  └────────────────────────────┘ │
└──────────┴──────────────────────────────────┘
```

---

## 🚀 Quick Start Commands

### Backend (Already Running)
```bash
# In insurance-crm directory
source venv/bin/activate
uvicorn app.main:app --reload --port 8001

# API Docs: http://localhost:8001/docs
```

---

### Frontend Setup (New Project)

**1. Create Next.js project**:
```bash
npx create-next-app@latest insurance-crm-frontend
# ✔ TypeScript? Yes
# ✔ ESLint? Yes
# ✔ Tailwind CSS? Yes
# ✔ App Router? Yes
# ✔ Import alias? @/*

cd insurance-crm-frontend
```

**2. Install shadcn/ui**:
```bash
npx shadcn-ui@latest init
# ✔ Style? Default
# ✔ Base color? Neutral
# ✔ CSS variables? Yes
```

**3. Install dependencies**:
```bash
npm install axios
npm install @tanstack/react-query
npm install react-hook-form zod @hookform/resolvers
npm install date-fns  # Date formatting
npm install recharts  # Charts
```

**4. Add shadcn components**:
```bash
npx shadcn-ui@latest add button card input label form table dialog badge tabs
```

**5. Run dev server**:
```bash
npm run dev
# Frontend: http://localhost:3000
```

---

### Folder Structure (Recommendation)

```
insurance-crm-frontend/
├── app/
│   ├── (auth)/
│   │   ├── login/
│   │   └── register/
│   ├── (dashboard)/
│   │   ├── broker/
│   │   ├── manager/
│   │   └── admin/
│   ├── prospects/
│   ├── quotes/
│   ├── policies/
│   ├── commissions/
│   └── layout.tsx
├── components/
│   ├── ui/              # shadcn components
│   ├── dashboard/
│   ├── prospects/
│   ├── quotes/
│   └── shared/
├── lib/
│   ├── api.ts           # Axios instance
│   ├── auth.ts          # JWT helpers
│   └── utils.ts
├── hooks/
│   ├── useAuth.ts
│   ├── useProspects.ts
│   └── useQuotes.ts
├── types/
│   ├── prospect.ts
│   ├── quote.ts
│   └── user.ts
└── public/
```

---

### API Client Setup (lib/api.ts)

```typescript
import axios from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8001/api/v1';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add JWT token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle 401 errors (redirect to login)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);
```

---

### Example: Login Page

```typescript
// app/(auth)/login/page.tsx
'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { api } from '@/lib/api';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card } from '@/components/ui/card';
import { toast } from '@/components/ui/use-toast';

const loginSchema = z.object({
  username: z.string().min(3),
  password: z.string().min(8),
});

type LoginForm = z.infer<typeof loginSchema>;

export default function LoginPage() {
  const router = useRouter();
  const [loading, setLoading] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginForm) => {
    setLoading(true);
    try {
      const response = await api.post('/auth/login', {
        username: data.username,
        password: data.password,
      });

      const { access_token } = response.data;
      localStorage.setItem('access_token', access_token);

      toast({
        title: 'Login successful',
        description: 'Welcome back!',
      });

      router.push('/dashboard/broker');
    } catch (error) {
      toast({
        title: 'Login failed',
        description: 'Invalid credentials',
        variant: 'destructive',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gray-50">
      <Card className="w-full max-w-md p-8">
        <h1 className="text-2xl font-bold mb-6">Insurance CRM</h1>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <Label htmlFor="username">Username</Label>
            <Input
              id="username"
              {...register('username')}
              placeholder="Enter username"
            />
            {errors.username && (
              <p className="text-sm text-red-500 mt-1">{errors.username.message}</p>
            )}
          </div>

          <div>
            <Label htmlFor="password">Password</Label>
            <Input
              id="password"
              type="password"
              {...register('password')}
              placeholder="Enter password"
            />
            {errors.password && (
              <p className="text-sm text-red-500 mt-1">{errors.password.message}</p>
            )}
          </div>

          <Button type="submit" className="w-full" disabled={loading}>
            {loading ? 'Logging in...' : 'Login'}
          </Button>
        </form>
      </Card>
    </div>
  );
}
```

---

## 📚 Resources & References

### Next.js
- **Docs**: https://nextjs.org/docs
- **App Router**: https://nextjs.org/docs/app
- **Data Fetching**: https://nextjs.org/docs/app/building-your-application/data-fetching

### shadcn/ui
- **Docs**: https://ui.shadcn.com
- **Components**: https://ui.shadcn.com/docs/components
- **Installation**: https://ui.shadcn.com/docs/installation/next

### Tailwind CSS
- **Docs**: https://tailwindcss.com/docs
- **Customization**: https://tailwindcss.com/docs/configuration

### React Hook Form
- **Docs**: https://react-hook-form.com
- **Zod Integration**: https://react-hook-form.com/get-started#SchemaValidation

### TanStack Query
- **Docs**: https://tanstack.com/query/latest
- **React Query**: https://tanstack.com/query/latest/docs/react/overview

---

## 🎯 Success Criteria

**Frontend is ready when**:
- ✅ User can login and access role-based dashboard
- ✅ Broker can manage prospects (CRUD)
- ✅ Broker can check eligibility (4 providers)
- ✅ Broker can generate AI quotes (3s loading state)
- ✅ Broker can accept quote → create policy
- ✅ Broker can view and download policy PDFs
- ✅ Broker can track commissions
- ✅ Manager can view team stats
- ✅ Manager can approve commissions
- ✅ Admin can manage users
- ✅ Responsive design (mobile/tablet/desktop)
- ✅ Excellent UX (loading states, error handling, toast notifications)

---

## 🚀 Ready to Start!

**Backend is running**: `http://localhost:8001`
**API Docs**: `http://localhost:8001/docs`
**All endpoints tested**: 66 tests passing ✅

**Next command**:
```bash
npx create-next-app@latest insurance-crm-frontend
```

---

**Last Updated**: November 3, 2025
**Status**: 🚀 Ready for Frontend Development
