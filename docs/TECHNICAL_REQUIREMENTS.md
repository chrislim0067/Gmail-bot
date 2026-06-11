# Gmail Cold-Email Outreach Platform
## Technical Requirements Document & Build Plan

**Version:** 1.3  
**Date:** 2026-06-10  
**Status:** Production readiness reviewed — append-only improvements in Appendix C  
**Stack:** Next.js + FastAPI + PostgreSQL + Redis + Celery + Gmail API

---

## Table of Contents

1. [Product Overview](#1-product-overview)
2. [Core Requirements](#2-core-requirements)
3. [System Architecture](#3-system-architecture)
   - [3.5 Scaling from 10 to 100–500 Gmail Accounts](#35-scaling-from-10-to-100500-gmail-accounts)
4. [Database Schema](#4-database-schema)
5. [Backend API Endpoints](#5-backend-api-endpoints)
6. [Background Worker Functions](#6-background-worker-functions)
7. [Rate Limiting and Account Protection](#7-rate-limiting-and-account-protection)
8. [Gmail API Integration](#8-gmail-api-integration)
9. [Frontend Pages](#9-frontend-pages)
10. [MVP Build Phases](#10-mvp-build-phases)
11. [Project File Structure](#11-project-file-structure)
12. [Security Requirements](#12-security-requirements)
13. [Testing Plan](#13-testing-plan)
14. [Deployment Plan](#14-deployment-plan)
15. [Cursor Implementation Instructions](#15-cursor-implementation-instructions)
16. [Appendix C: Production Readiness Additions (Append-Only)](#appendix-c-production-readiness-additions-append-only)

---

## 1. Product Overview

### What the App Does

A self-hosted web application that lets a single operator (or small team) connect multiple **personal Gmail accounts** via **OAuth 2.0**, import leads, create personalized email templates, schedule controlled outreach campaigns, and monitor replies, bounces, unsubscribes, and account health — all through the **Gmail API** with strict rate limits and compliance guardrails.

The platform is **not** a bulk spam engine. It is a **controlled, auditable outreach tool** designed to protect sender reputation and comply with CAN-SPAM, GDPR-conscious practices, and Google API Terms of Service.

### Who Uses It

| Persona | Use Case |
|---------|----------|
| **Solo founder / freelancer** | Personal cold outreach for sales, partnerships, recruiting |
| **Small agency operator** | Manage 2–10 Gmail inboxes with separate daily caps |
| **Power user (future)** | Team admin with RBAC, multiple workspaces |

**Primary user for MVP:** Single authenticated app user managing their own Gmail accounts.

### MVP Scope

| In Scope | Out of Scope (MVP) |
|----------|-------------------|
| App login (JWT) | Multi-tenant SaaS billing |
| Gmail OAuth connect (1+ accounts) | SMTP / app-password sending |
| Encrypted token storage + auto-refresh | Shared IP pool / relay servers |
| Campaign CRUD | AI-generated copy at scale |
| CSV lead import + validation | LinkedIn scraping integrations |
| Template engine with `{{variables}}` | Third-party warm-up email networks |
| Queue-based sending with rate limits | Purchased lead lists enforcement |
| Trust-tier caps + compliant volume ramp | Fake human-behavior simulation |
| Gmail account pools (10–500 account scale) | CAPTCHA / proxy / fingerprint evasion |
| Per-account + scheduler + token Redis locks | White-label reseller portal |
| Global risk budget + account review queue | Full CRM |
| Campaign preflight checks | Custom mail server |
| Multi-layer bounce parsing (DSN + headers) | Kubernetes production deploy |
| Lead import batches + compliance ack | |
| OAuth verification planning | |
| Unsubscribe link + suppression list | Mobile native apps |
| Account health dashboard | Prometheus/Grafana (optional stub only) |
| Audit logs | |
| Docker Compose local deploy | |

### Non-Goals

- **No credential harvesting** — passwords and app passwords are never stored or requested.
- **No circumvention of Google security** — no CAPTCHA bypass, no session cookie theft, no unauthorized API access.
- **No spam-scale sending** — hard caps prevent high-volume blast behavior.
- **No purchased/scraped list encouragement** — UI warns on import; system blocks role-based abuse patterns.
- **No open relay** — all sends originate from authenticated user's own Gmail accounts.
- **No malware, tracking pixels for covert surveillance, or deceptive headers.**

### Safety / Compliance Boundaries

```
┌─────────────────────────────────────────────────────────────────┐
│                    COMPLIANCE BOUNDARY BOX                       │
├─────────────────────────────────────────────────────────────────┤
│ ✓ OAuth 2.0 only (gmail.send, gmail.readonly, openid)          │
│ ✓ Physical unsubscribe link in every outreach email             │
│ ✓ List-Unsubscribe header (RFC 8058 one-click where supported)  │
│ ✓ Bounce + unsubscribe permanent suppression                    │
│ ✓ Account tiers: new 5/day → warming 10 → stable 20 → trusted 30 (hard max 75) │
│ ✓ Compliant ramp: promote/demote from success days + bounce/error rates        │
│ ✓ Account pools: stagger sends; never blast all accounts at once               │
│ ✓ Redis locks: one sender + one scheduler + one token refresh per resource     │
│ ✓ Global risk budget: pause new sends when score exceeds threshold             │
│ ✓ Randomized inter-send delay: 120–480 seconds                                 │
│ ✓ Auto-pause on quota errors, bounce spike, auth failures                      │
│ ✓ Audit trail for every send, pause, tier change, and token refresh           │
│ ✓ CAN-SPAM: physical address + honest subject + opt-out                        │
│ ✓ GDPR-conscious: source, consent_basis, import_batch on leads                 │
│ ✗ No sending without unsubscribe mechanism                      │
│ ✗ No retry to bounced/unsubscribed addresses                    │
│ ✗ No parallel burst sends from single account                   │
│ ✗ No header spoofing or deceptive From/Reply-To                 │
└─────────────────────────────────────────────────────────────────┘
```

**Legal disclaimer (shown in app onboarding):** User is solely responsible for compliance with applicable laws (CAN-SPAM, GDPR, CASL, etc.) and Google Terms of Service. The platform enforces technical guardrails but does not provide legal advice.

---

## 2. Core Requirements

### 2.1 Gmail OAuth Connection

| ID | Requirement | Priority |
|----|-------------|----------|
| OAUTH-01 | User initiates connect via "Connect Gmail" → Google consent screen | P0 |
| OAUTH-02 | OAuth state parameter stored in Redis with CSRF nonce, 10-min TTL | P0 |
| OAUTH-03 | Callback exchanges code for access + refresh tokens | P0 |
| OAUTH-04 | Store only encrypted refresh token; access token in Redis cache | P0 |
| OAUTH-05 | Capture `email`, `google_user_id`, `granted_scopes` | P0 |
| OAUTH-06 | Re-connect flow updates tokens without duplicating account row | P0 |
| OAUTH-07 | Revoke flow calls Google revoke endpoint + soft-delete account | P1 |
| OAUTH-08 | Track OAuth consent screen status: `testing`, `in_review`, `published` | P0 |
| OAUTH-09 | Enforce Google test-user limit (100) while app is unverified | P0 |
| OAUTH-10 | Block new connects when app is in Testing and test-user cap reached | P1 |
| OAUTH-11 | Dashboard warning when app is unverified (sensitive scope banner) | P1 |
| OAUTH-12 | Surface `access_denied` and `app_not_verified` as clear user-facing errors | P0 |
| OAUTH-13 | Display `granted_scopes` per account in dashboard | P0 |

### 2.2 Secure Token Management

| ID | Requirement | Priority |
|----|-------------|----------|
| TOK-01 | Refresh tokens encrypted at rest (AES-256-GCM, key from env) | P0 |
| TOK-02 | Access tokens never logged; max Redis TTL = `expires_in - 60s` | P0 |
| TOK-03 | Background token refresh 5 min before expiry | P0 |
| TOK-04 | On `invalid_grant`, mark account `auth_error` and pause all campaigns | P0 |
| TOK-05 | Token refresh failures increment health score penalty | P0 |
| TOK-06 | Acquire `lock:token_refresh:{account_id}` before refresh; TTL 10 min | P0 |

### 2.3 Campaigns

| ID | Requirement | Priority |
|----|-------------|----------|
| CAMP-01 | Campaign: name, template, schedule, status, `campaign_account_pool_id` | P0 |
| CAMP-02 | Statuses: `draft`, `scheduled`, `running`, `paused`, `completed`, `cancelled` | P0 |
| CAMP-03 | Start/end datetime window (timezone-aware) | P0 |
| CAMP-04 | Send only within user-defined business hours (default 9–17 local) | P1 |
| CAMP-05 | Pause/resume manual control | P0 |
| CAMP-06 | Auto-pause propagates to all pending send_jobs | P0 |
| CAMP-07 | `POST /campaigns/{id}/preflight-check` required before start | P0 |
| CAMP-08 | Block start if global risk budget exceeded | P0 |

### 2.4 Leads Import & Validation

| ID | Requirement | Priority |
|----|-------------|----------|
| LEAD-01 | CSV upload: `email` required; optional `first_name`, `last_name`, `company`, `custom_*` | P0 |
| LEAD-02 | RFC 5322 syntax validation + DNS MX lookup (async) | P0 |
| LEAD-03 | Deduplicate by email per campaign | P0 |
| LEAD-04 | Global suppression check (bounce + unsubscribe) before queueing | P0 |
| LEAD-05 | Lead status: `pending`, `queued`, `sent`, `replied`, `bounced`, `unsubscribed`, `skipped`, `failed` | P0 |
| LEAD-06 | Export leads with status filter | P1 |
| LEAD-07 | Fields: `source`, `source_url`, `consent_basis`, `consent_notes`, `import_batch_id` | P0 |
| LEAD-08 | Store `normalized_email`, `last_contacted_at`, `do_not_contact_reason` | P0 |
| LEAD-09 | Reject import if `compliance_acknowledged` is false on batch | P0 |
| LEAD-10 | Warn if `source` or `source_url` missing on cold-outreach import | P1 |
| LEAD-11 | Block role-based emails by default: info@, support@, admin@, sales@, contact@, noreply@, no-reply@ | P0 |
| LEAD-12 | Allow role-based override only via explicit manual flag per import batch | P1 |

### 2.5 Email Templates

| ID | Requirement | Priority |
|----|-------------|----------|
| TMPL-01 | Subject + HTML body + plain-text fallback | P0 |
| TMPL-02 | Variables: `{{first_name}}`, `{{last_name}}`, `{{company}}`, `{{email}}`, custom fields | P0 |
| TMPL-03 | Required footer block: unsubscribe link placeholder `{{unsubscribe_url}}` | P0 |
| TMPL-04 | Template validation rejects send if unsubscribe placeholder missing | P0 |
| TMPL-05 | Preview rendered output for sample lead | P1 |

### 2.6 Personalization

| ID | Requirement | Priority |
|----|-------------|----------|
| PERS-01 | Jinja2-style rendering server-side only | P0 |
| PERS-02 | Missing optional variables → empty string; missing required → skip lead | P0 |
| PERS-03 | HTML escape by default; raw block for intentional HTML | P1 |

### 2.7 Scheduling & Queue

| ID | Requirement | Priority |
|----|-------------|----------|
| QUE-01 | Scheduler creates `send_jobs` from campaign leads at start time | P0 |
| QUE-02 | Celery worker picks jobs respecting rate limits | P0 |
| QUE-03 | Job states: `pending`, `locked`, `sent`, `failed`, `cancelled`, `skipped` | P0 |
| QUE-04 | Idempotency key: `campaign_id + lead_id` unique | P0 |
| QUE-05 | Failed jobs: max 2 retries with exponential backoff (min 30 min) | P0 |
| QUE-06 | Acquire `lock:gmail_account:{id}` before render/send; TTL 10 min | P0 |
| QUE-07 | Release sender lock in `finally` after send result recorded | P0 |
| QUE-08 | Acquire `lock:campaign_scheduler:{campaign_id}` before job materialization | P0 |

### 2.8 Rate Limits & Account Tiers

| ID | Requirement | Priority |
|----|-------------|----------|
| RL-01 | Effective daily cap = `min(user_override, tier_default, tier_hard_max)` | P0 |
| RL-02 | Tiers: `new` 5/10, `warming` 10/20, `stable` 20/50, `trusted` 30/75 (default/hard max per day) | P0 |
| RL-03 | `restricted` and `paused` tiers: **0 sends/day** until manual review | P0 |
| RL-04 | Hourly caps scale with tier (see §7.2) | P0 |
| RL-05 | Pool caps: `max_daily_send`, `max_hourly_send`, `active_account_limit` | P0 |
| RL-06 | Global daily cap across all accounts (default 200) | P0 |
| RL-07 | Inter-send delay random uniform [120s, 480s] per account | P0 |
| RL-08 | Redis sliding-window counters | P0 |
| RL-09 | User may only **decrease** caps; increases require tier promotion | P0 |
| RL-10 | Global risk budget threshold blocks new campaign starts and job queueing | P0 |

### 2.9 Reply Tracking

| ID | Requirement | Priority |
|----|-------------|----------|
| REP-01 | Poll Gmail threads for `In-Reply-To` / `References` matching sent `Message-ID` | P0 |
| REP-02 | Mark lead `replied`; store reply snippet + timestamp | P0 |
| REP-03 | Sync interval: every 15 min per active account | P1 |

### 2.10 Bounce Tracking

| ID | Requirement | Priority |
|----|-------------|----------|
| BNC-01 | Inspect From: mailer-daemon, postmaster, mail delivery subsystem | P0 |
| BNC-02 | Inspect Subject: DSN, Undelivered Mail Returned to Sender, Delivery has failed, etc. | P0 |
| BNC-03 | Parse MIME: `message/delivery-status`, `text/rfc822-headers` | P0 |
| BNC-04 | Parse DSN: Final-Recipient, Original-Recipient, Action, Status, Diagnostic-Code | P0 |
| BNC-05 | Classify SMTP: 5.x.x = hard, 4.x.x = soft | P0 |
| BNC-06 | Fallback regex extraction for bounced recipient when DSN incomplete | P0 |
| BNC-07 | Hard bounce → immediate global suppression | P0 |
| BNC-08 | Soft bounce → 3 strikes then suppression | P1 |
| BNC-09 | Store `smtp_status_code`, `diagnostic`, `detection_method`, `raw_headers` | P0 |
| BNC-10 | Test fixtures: Gmail, Google Workspace, Outlook, soft, malformed | P0 |

### 2.11 Unsubscribe

| ID | Requirement | Priority |
|----|-------------|----------|
| UNS-01 | Signed JWT unsubscribe URL per lead per campaign | P0 |
| UNS-02 | One-click POST + GET confirmation page | P0 |
| UNS-03 | `List-Unsubscribe` + `List-Unsubscribe-Post` headers | P0 |
| UNS-04 | Global suppression table; never re-send | P0 |

### 2.12 Account Health

| ID | Requirement | Priority |
|----|-------------|----------|
| HLTH-01 | Health score 0–100 per Gmail account | P0 |
| HLTH-02 | Penalties: auth error (-50), quota exceeded (-30), bounce rate >5% (-40) | P0 |
| HLTH-03 | Auto-pause account when score < 30 | P0 |
| HLTH-04 | Daily health snapshot event | P1 |
| HLTH-05 | Track rolling 7d bounce rate, error rate, reply rate per account | P0 |
| HLTH-06 | `account_tier` drives caps: new, warming, stable, trusted, restricted, paused | P0 |
| HLTH-07 | `evaluate_account_tier()` promotes/demotes based on success days + metrics | P0 |
| HLTH-08 | `risk_level`: low, medium, high; `review_required` flag | P0 |

### 2.13 Auto-Pause on Errors

| ID | Requirement | Priority |
|----|-------------|----------|
| PAUSE-01 | Pause account on 3 consecutive send failures | P0 |
| PAUSE-02 | Pause account on Google 403/429 quota errors | P0 |
| PAUSE-03 | Pause campaign on bounce rate > 8% in rolling 24h | P0 |
| PAUSE-04 | Notify user in dashboard + audit log entry | P0 |

### 2.14 Admin Dashboard & Audit

| ID | Requirement | Priority |
|----|-------------|----------|
| ADM-01 | Dashboard: sends today, reply rate, bounce rate, active campaigns | P0 |
| ADM-02 | Audit log: actor, action, resource, IP, timestamp, metadata JSON | P0 |
| ADM-03 | Immutable audit records (append-only) | P0 |

### 2.15 Account Pools

| ID | Requirement | Priority |
|----|-------------|----------|
| POOL-01 | Users create named account pools with daily/hourly caps | P0 |
| POOL-02 | Pool membership via join table with priority and `is_active` | P0 |
| POOL-03 | Campaigns reference one pool via `campaign_account_pool_id` FK | P0 |
| POOL-04 | `active_account_limit` prevents all pool accounts sending simultaneously | P0 |
| POOL-05 | Round-robin / priority selection among pool members with capacity | P0 |

### 2.16 Global Risk Budget

| ID | Requirement | Priority |
|----|-------------|----------|
| GRISK-01 | Record risk events: quota (+30), auth (+50), bounce spike (+40), high failure (+30), manual (+20) | P0 |
| GRISK-02 | Rolling global risk score per user; threshold default 100 | P0 |
| GRISK-03 | Above threshold: pause new campaign starts, block new send_jobs | P0 |
| GRISK-04 | Allow reply sync + unsubscribe processing while risk elevated | P0 |
| GRISK-05 | `POST /risk/acknowledge` required to resume after review | P0 |

### 2.17 Gmail Account Risk Policy

> **Critical:** Scaling to 100–500 Gmail accounts is an **architecture** problem *and* an **operational trust** problem. The stack can queue and rate-limit at scale, but Google may restrict or suspend individual accounts based on sending patterns, recipient complaints, and OAuth app reputation — independent of our infrastructure.

| ID | Requirement | Priority |
|----|-------------|----------|
| RISK-01 | Document account risk policy in onboarding; user accepts responsibility | P0 |
| RISK-02 | Never assume high daily caps are safe for newly connected personal Gmail | P0 |
| RISK-03 | `restricted` tier: 0 sends until `POST /gmail/accounts/{id}/review` clears account | P0 |
| RISK-04 | Dashboard shows tier, risk level, connected age, success days, quota/auth errors | P0 |
| RISK-05 | Use account pools to stagger sends; never allow all accounts to send at once | P0 |
| RISK-06 | At 100+ accounts: OAuth verification + dedicated Google Cloud project required | P1 |

**Operational guidance (document in README):**

- Personal Gmail is not designed for high-volume cold outreach.
- More accounts ≠ linear throughput if Google flags the OAuth app or sender patterns.
- Prefer fewer, warmed accounts with clean metrics over many fresh inboxes.
- Scale operationally with pools, tiers, and risk budgets — not by raising caps globally.

---

## 3. System Architecture

### 3.1 High-Level Diagram

```
┌──────────────────────────────────────────────────────────────────────────┐
│                         USER BROWSER                                      │
│                    Next.js 14 App (TypeScript)                            │
│              Tailwind CSS · React Query · Zustand                         │
└─────────────────────────────┬────────────────────────────────────────────┘
                              │ HTTPS / REST + JWT Cookie
                              ▼
┌──────────────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend API (:8000)                          │
│   Routers: auth · gmail · account-pools · campaigns · leads · templates · risk · analytics │
│   Middleware: CORS · JWT auth · request ID · audit hook                   │
└──────┬──────────────────┬──────────────────────┬─────────────────────────┘
       │                  │                      │
       ▼                  ▼                      ▼
┌─────────────┐   ┌──────────────┐      ┌────────────────┐
│ PostgreSQL  │   │    Redis     │      │  Celery Beat   │
│  (primary)  │   │ cache/queue/ │      │  (scheduler)   │
│             │   │ rate limits  │      └───────┬────────┘
└─────────────┘   └──────┬───────┘              │
                         │                      ▼
                         │              ┌─────────────────────────────────┐
                         │              │       Celery Workers            │
                         │              ├─────────────────────────────────┤
                         └─────────────►│ sender_worker                   │
                                        │ reply_sync_worker               │
                                        │ bounce_detection_worker         │
                                        │ campaign_scheduler              │
                                        │ account_tier_evaluator          │
                                        │ risk_budget_monitor             │
                                        │ token_refresh_service           │
                                        └──────────────┬──────────────────┘
                                                       │
                                                       ▼
                                        ┌─────────────────────────────────┐
                                        │         Gmail API (Google)        │
                                        │  gmail.send · gmail.readonly      │
                                        └─────────────────────────────────┘
```

### 3.2 Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **Next.js Dashboard** | UI, form validation, API client, OAuth redirect initiation |
| **FastAPI Backend** | Business logic, auth, CRUD, enqueue jobs, unsubscribe endpoint |
| **PostgreSQL** | Persistent data, relationships, audit trail |
| **Redis** | Celery broker, OAuth state, access token cache, rate limit counters, distributed locks |
| **Celery Beat** | Cron: schedule campaigns, sync replies, health checks, token refresh |
| **Sender Worker** | Dequeue send_jobs, enforce limits, call Gmail send |
| **Reply Sync Worker** | Fetch threads, match replies to sent_emails |
| **Bounce Detection Worker** | Scan mailbox for DSN messages |
| **Campaign Scheduler** | Transition campaigns to running; materialize send_jobs |
| **Account Health Monitor** | Compute scores; trigger pause_account |
| **Token Refresh Service** | Proactive refresh; handle invalid_grant |

### 3.3 Request Flow: Send Email

```
Campaign Scheduler (beat, every 1 min)
    │
    ├─► campaign.status == scheduled && start_at <= now
    │       └─► create_send_jobs() → INSERT send_jobs (pending)
    │
Sender Worker (continuous dequeue)
    │
    ├─► enforce_account_rate_limit()
    ├─► select_available_gmail_account()
    ├─► render_email_template()
    ├─► send_email_via_gmail_api()
    ├─► record_sent_email()
    └─► update lead.status = sent
```

### 3.4 Data Flow: OAuth Connect

```
Browser → GET /api/gmail/connect
    └─► Generate state nonce → Redis SET oauth_state:{nonce}
    └─► Redirect to Google consent URL

Google → GET /api/gmail/callback?code=...&state=...
    └─► Validate state from Redis
    └─► Exchange code for tokens
    └─► Encrypt refresh_token → INSERT oauth_tokens
    └─► INSERT/UPDATE gmail_accounts
    └─► Redirect frontend /accounts?connected=1
```

### 3.5 Scaling from 10 to 100–500 Gmail Accounts

Scaling from 10 to 100–500 connected Gmail accounts is **mostly an operational risk problem**, not only a technical scaling problem. PostgreSQL, Redis, and Celery can handle the queue volume, but Google may throttle, restrict, or suspend individual accounts based on sending behavior, complaints, and OAuth app reputation.

**Design principles for safe scale:**

| Principle | Implementation |
|-----------|----------------|
| Never blast all accounts at once | Account pools with `active_account_limit` |
| Conservative per-account caps | Tier system: new 5/day → trusted 30/day (75 max) |
| Staggered pool throughput | `max_daily_send` + `max_hourly_send` per pool |
| One send per account at a time | Redis `lock:gmail_account:{id}` |
| Observable risk | Global risk budget + per-account `risk_level` |
| Manual recovery path | Review queue for `restricted` accounts |
| Join tables over arrays | Pool membership, analytics, health filtering at scale |

**Account pool concept:**

Each pool groups Gmail accounts under shared caps and a risk policy. Campaigns bind to a pool — not a raw UUID array — so the scheduler can:

- Respect pool daily/hourly budgets
- Limit concurrent active senders via `active_account_limit`
- Prioritize healthier accounts via membership `priority`
- Pause an entire pool without touching unrelated accounts

**Why join tables beat `assigned_account_ids UUID[]`:**

| Concern | UUID array | Join table |
|---------|------------|------------|
| Filter accounts by tier/status | Full table scan + unnest | Indexed FK join |
| Pool analytics (sends per pool) | Denormalized counters only | Queryable membership |
| Add/remove account from pool | Rewrite array column | Insert/delete row |
| Priority ordering | Not supported | `priority` column |
| Active/inactive member | Not supported | `is_active` flag |
| 500-account scale | Poor query plans | Standard relational pattern |

**Operational guidance at 100+ accounts:**

- Split accounts across multiple pools (e.g., 10–25 accounts per pool).
- Keep `active_account_limit` ≤ 10 per pool during ramp-up.
- Monitor global risk score continuously; pause new sends before Google mass-restricts.
- Complete OAuth app verification before connecting accounts beyond test-user limits.
- Do **not** attempt to circumvent Google anti-abuse systems — protect accounts through conservative limits and automatic pause logic.

---

## 4. Database Schema

**Conventions:**
- All tables: `id UUID PK`, `created_at TIMESTAMPTZ`, `updated_at TIMESTAMPTZ`
- Soft delete: `deleted_at TIMESTAMPTZ NULL` where noted
- Timestamps default `NOW()`

### 4.1 `users`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | App user ID |
| email | VARCHAR(255) | UNIQUE, NOT NULL | Login email |
| password_hash | VARCHAR(255) | NOT NULL | bcrypt hash (app auth only) |
| full_name | VARCHAR(255) | NULL | Display name |
| timezone | VARCHAR(64) | DEFAULT 'UTC' | Scheduling |
| global_risk_score | INT | DEFAULT 0 | Rolling risk budget |
| risk_review_required | BOOLEAN | DEFAULT false | Blocks new campaigns when true |
| is_active | BOOLEAN | DEFAULT true | Account status |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `UNIQUE(email)`  
**Relationships:** 1:N → `gmail_accounts`, `campaigns`, `audit_logs`

---

### 4.2 `gmail_accounts`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id, NOT NULL | Owner |
| email | VARCHAR(255) | NOT NULL | Gmail address |
| google_user_id | VARCHAR(128) | NOT NULL | Google sub |
| display_name | VARCHAR(255) | NULL | |
| status | VARCHAR(32) | DEFAULT 'active' | active, paused, auth_error, revoked |
| account_tier | VARCHAR(32) | DEFAULT 'new' | new, warming, stable, trusted, restricted, paused |
| connected_at | TIMESTAMPTZ | NOT NULL | OAuth connect time |
| first_send_at | TIMESTAMPTZ | NULL | First successful send |
| last_successful_send_at | TIMESTAMPTZ | NULL | Last successful send |
| consecutive_success_days | INT | DEFAULT 0 | Days with ≥1 successful send, no failures |
| consecutive_failure_count | INT | DEFAULT 0 | Resets on successful send |
| risk_level | VARCHAR(32) | DEFAULT 'low' | low, medium, high |
| review_required | BOOLEAN | DEFAULT false | Manual review gate |
| daily_send_limit | INT | DEFAULT 5 | User override; capped by tier |
| hourly_send_limit | INT | DEFAULT 1 | User override; capped by tier |
| tier_daily_default | INT | NOT NULL | From account_tier (computed) |
| tier_daily_hard_max | INT | NOT NULL | From account_tier (computed) |
| bounce_rate_7d | DECIMAL(5,4) | DEFAULT 0 | Rolling bounce rate |
| error_rate_7d | DECIMAL(5,4) | DEFAULT 0 | Rolling send failure rate |
| reply_rate_7d | DECIMAL(5,4) | DEFAULT 0 | Rolling reply rate |
| lifetime_send_count | INT | DEFAULT 0 | Total successful sends |
| health_score | INT | DEFAULT 100 | 0–100 |
| last_send_at | TIMESTAMPTZ | NULL | Rate limiting |
| paused_reason | TEXT | NULL | Human-readable |
| paused_at | TIMESTAMPTZ | NULL | |
| deleted_at | TIMESTAMPTZ | NULL | Soft delete |

**Indexes:** `UNIQUE(user_id, email)`, `INDEX(status)`, `INDEX(account_tier)`, `INDEX(user_id)`, `INDEX(review_required)`  
**Relationships:** N:1 → users; 1:1 → oauth_tokens; 1:N → send_jobs, sent_emails, account_health_events; N:M → gmail_account_pools via pool_members

---

### 4.2a `gmail_account_pools`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id, NOT NULL | Owner |
| name | VARCHAR(255) | NOT NULL | Pool name |
| description | TEXT | NULL | |
| max_daily_send | INT | DEFAULT 200 | Pool daily cap |
| max_hourly_send | INT | DEFAULT 40 | Pool hourly cap |
| active_account_limit | INT | DEFAULT 10 | Max concurrent sending accounts |
| risk_policy | VARCHAR(64) | DEFAULT 'conservative' | conservative, standard |
| status | VARCHAR(32) | DEFAULT 'active' | active, paused |
| created_at | TIMESTAMPTZ | NOT NULL | |
| updated_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `INDEX(user_id)`, `UNIQUE(user_id, name)`  
**Relationships:** N:1 → users; 1:N → pool_members, campaigns

---

### 4.2b `gmail_account_pool_members`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| pool_id | UUID | FK → gmail_account_pools.id, NOT NULL | |
| gmail_account_id | UUID | FK → gmail_accounts.id, NOT NULL | |
| priority | INT | DEFAULT 100 | Lower = higher priority |
| is_active | BOOLEAN | DEFAULT true | Include in rotation |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `UNIQUE(pool_id, gmail_account_id)`, `INDEX(pool_id, is_active, priority)`  
**Relationships:** N:1 → gmail_account_pools, gmail_accounts

---

### 4.3 `oauth_tokens`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| gmail_account_id | UUID | FK UNIQUE → gmail_accounts.id | One token set per account |
| encrypted_refresh_token | BYTEA | NOT NULL | AES-256-GCM ciphertext |
| encryption_key_id | VARCHAR(32) | DEFAULT 'v1' | Key rotation |
| granted_scopes | TEXT[] | NOT NULL | Scope audit |
| access_token_expires_at | TIMESTAMPTZ | NULL | Tracking |
| last_refreshed_at | TIMESTAMPTZ | NULL | |
| refresh_fail_count | INT | DEFAULT 0 | |

**Indexes:** `UNIQUE(gmail_account_id)`  
**Note:** Access tokens stored in Redis only, not PostgreSQL.

---

### 4.4 `campaigns`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id | |
| name | VARCHAR(255) | NOT NULL | |
| template_id | UUID | FK → email_templates.id | |
| status | VARCHAR(32) | DEFAULT 'draft' | |
| scheduled_start_at | TIMESTAMPTZ | NULL | |
| scheduled_end_at | TIMESTAMPTZ | NULL | |
| send_window_start_hour | INT | DEFAULT 9 | Local hour |
| send_window_end_hour | INT | DEFAULT 17 | |
| timezone | VARCHAR(64) | DEFAULT 'UTC' | |
| campaign_account_pool_id | UUID | FK → gmail_account_pools.id, NOT NULL | Account pool for sending |
| preflight_passed_at | TIMESTAMPTZ | NULL | Last successful preflight |
| total_leads | INT | DEFAULT 0 | Denormalized |
| sent_count | INT | DEFAULT 0 | |
| replied_count | INT | DEFAULT 0 | |
| bounced_count | INT | DEFAULT 0 | |
| paused_reason | TEXT | NULL | |
| deleted_at | TIMESTAMPTZ | NULL | |

**Indexes:** `INDEX(user_id)`, `INDEX(status)`, `INDEX(scheduled_start_at)`  
**Relationships:** N:1 → users, email_templates; 1:N → leads, send_jobs

---

### 4.5 `leads`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| campaign_id | UUID | FK → campaigns.id | |
| email | VARCHAR(255) | NOT NULL | Original email |
| normalized_email | VARCHAR(255) | NOT NULL | Lowercase, trimmed for dedup |
| first_name | VARCHAR(128) | NULL | |
| last_name | VARCHAR(128) | NULL | |
| company | VARCHAR(255) | NULL | |
| custom_fields | JSONB | DEFAULT '{}' | Extra vars |
| source | VARCHAR(255) | NULL | Lead origin label |
| source_url | TEXT | NULL | Origin URL or CRM reference |
| consent_basis | VARCHAR(64) | NULL | e.g. legitimate_interest, opt_in |
| consent_notes | TEXT | NULL | Free-text compliance notes |
| import_batch_id | UUID | FK NULL → lead_import_batches.id | |
| last_contacted_at | TIMESTAMPTZ | NULL | Last successful outreach |
| do_not_contact_reason | TEXT | NULL | unsubscribed, hard_bounce, role_based, etc. |
| status | VARCHAR(32) | DEFAULT 'pending' | |
| validation_status | VARCHAR(32) | DEFAULT 'pending' | valid, invalid, unknown |
| validation_error | TEXT | NULL | |
| deleted_at | TIMESTAMPTZ | NULL | |

**Indexes:** `UNIQUE(campaign_id, normalized_email)`, `INDEX(campaign_id, status)`, `INDEX(normalized_email)`, `INDEX(import_batch_id)`  
**Relationships:** N:1 → campaigns, lead_import_batches; 1:N → send_jobs, sent_emails

---

### 4.5a `lead_import_batches`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| campaign_id | UUID | FK → campaigns.id, NOT NULL | |
| uploaded_by_user_id | UUID | FK → users.id, NOT NULL | |
| filename | VARCHAR(255) | NOT NULL | Original CSV filename |
| row_count | INT | DEFAULT 0 | Total rows in file |
| imported_count | INT | DEFAULT 0 | Successfully imported |
| skipped_count | INT | DEFAULT 0 | Skipped (dup, role-based, etc.) |
| invalid_count | INT | DEFAULT 0 | Validation failures |
| source_label | VARCHAR(255) | NULL | User-provided source description |
| compliance_acknowledged | BOOLEAN | DEFAULT false | Required true to import |
| allow_role_based_emails | BOOLEAN | DEFAULT false | Override role-based block |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `INDEX(campaign_id, created_at DESC)`  
**Relationships:** N:1 → campaigns, users; 1:N → leads

---

### 4.6 `email_templates`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id | |
| name | VARCHAR(255) | NOT NULL | |
| subject_template | TEXT | NOT NULL | Jinja2 |
| html_template | TEXT | NOT NULL | |
| text_template | TEXT | NULL | Plain fallback |
| is_active | BOOLEAN | DEFAULT true | |
| deleted_at | TIMESTAMPTZ | NULL | |

**Indexes:** `INDEX(user_id)`  
**Relationships:** N:1 → users; 1:N → campaigns

---

### 4.7 `send_jobs`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| campaign_id | UUID | FK → campaigns.id | |
| lead_id | UUID | FK → leads.id | |
| gmail_account_id | UUID | FK NULL → gmail_accounts.id | Assigned at send |
| status | VARCHAR(32) | DEFAULT 'pending' | |
| scheduled_at | TIMESTAMPTZ | NOT NULL | |
| locked_at | TIMESTAMPTZ | NULL | Worker lock |
| attempts | INT | DEFAULT 0 | |
| last_error | TEXT | NULL | |
| idempotency_key | VARCHAR(128) | UNIQUE | campaign:lead |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `UNIQUE(idempotency_key)`, `INDEX(status, scheduled_at)`, `INDEX(campaign_id)`  
**Relationships:** N:1 → campaigns, leads, gmail_accounts

---

### 4.8 `sent_emails`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| send_job_id | UUID | FK UNIQUE → send_jobs.id | |
| campaign_id | UUID | FK → campaigns.id | |
| lead_id | UUID | FK → leads.id | |
| gmail_account_id | UUID | FK → gmail_accounts.id | |
| gmail_message_id | VARCHAR(255) | NULL | Gmail ID |
| rfc_message_id | VARCHAR(255) | NULL | Message-ID header |
| thread_id | VARCHAR(255) | NULL | Gmail thread |
| recipient_email | VARCHAR(255) | NOT NULL | |
| subject | TEXT | NOT NULL | Rendered |
| sent_at | TIMESTAMPTZ | NOT NULL | |
| delivery_status | VARCHAR(32) | DEFAULT 'sent' | |

**Indexes:** `INDEX(gmail_account_id)`, `INDEX(campaign_id)`, `INDEX(rfc_message_id)`, `INDEX(thread_id)`  
**Relationships:** 1:1 → send_jobs; 1:N → reply_events

---

### 4.9 `reply_events`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| sent_email_id | UUID | FK → sent_emails.id | |
| gmail_message_id | VARCHAR(255) | NOT NULL | |
| from_email | VARCHAR(255) | NOT NULL | |
| snippet | TEXT | NULL | |
| received_at | TIMESTAMPTZ | NOT NULL | |
| is_auto_reply | BOOLEAN | DEFAULT false | OOO detection |

**Indexes:** `INDEX(sent_email_id)`, `UNIQUE(gmail_message_id)`  
**Relationships:** N:1 → sent_emails

---

### 4.10 `bounce_events`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| gmail_account_id | UUID | FK → gmail_accounts.id | Detecting account |
| sent_email_id | UUID | FK NULL → sent_emails.id | |
| bounced_email | VARCHAR(255) | NOT NULL | |
| bounce_type | VARCHAR(32) | NOT NULL | hard, soft |
| smtp_status_code | VARCHAR(16) | NULL | e.g. 5.1.1, 550 |
| detection_method | VARCHAR(64) | NOT NULL | dsn_body, header, subject_fallback |
| diagnostic | TEXT | NULL | Diagnostic-Code / SMTP text |
| raw_headers | JSONB | NULL | Parsed bounce headers for audit |
| detected_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `INDEX(bounced_email)`, `INDEX(gmail_account_id, detected_at)`  
**Relationships:** N:1 → gmail_accounts, sent_emails

---

### 4.11 `unsubscribe_list`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id | Scope owner |
| email | VARCHAR(255) | NOT NULL | |
| source | VARCHAR(64) | NOT NULL | link, manual, complaint |
| campaign_id | UUID | FK NULL → campaigns.id | |
| unsubscribed_at | TIMESTAMPTZ | NOT NULL | |
| ip_address | INET | NULL | |

**Indexes:** `UNIQUE(user_id, email)`  
**Relationships:** N:1 → users, campaigns

---

### 4.12 `account_health_events`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| gmail_account_id | UUID | FK → gmail_accounts.id | |
| score | INT | NOT NULL | Snapshot |
| bounce_rate_24h | DECIMAL(5,4) | NULL | |
| send_count_24h | INT | NULL | |
| failure_count_24h | INT | NULL | |
| event_type | VARCHAR(64) | NOT NULL | snapshot, pause, warning |
| details | JSONB | DEFAULT '{}' | |
| recorded_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `INDEX(gmail_account_id, recorded_at DESC)`

---

### 4.13 `audit_logs`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| user_id | UUID | FK NULL → users.id | |
| action | VARCHAR(128) | NOT NULL | e.g. campaign.pause |
| resource_type | VARCHAR(64) | NOT NULL | |
| resource_id | UUID | NULL | |
| ip_address | INET | NULL | |
| user_agent | TEXT | NULL | |
| metadata | JSONB | DEFAULT '{}' | No tokens |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `INDEX(user_id, created_at DESC)`, `INDEX(action)`, `INDEX(resource_type, resource_id)`

---

### 4.14 `risk_budget_events`

| Column | Type | Constraints | Purpose |
|--------|------|-------------|---------|
| id | UUID | PK | |
| user_id | UUID | FK → users.id, NOT NULL | |
| event_type | VARCHAR(64) | NOT NULL | quota_error, auth_error, bounce_spike, etc. |
| severity | VARCHAR(32) | NOT NULL | low, medium, high, critical |
| gmail_account_id | UUID | FK NULL → gmail_accounts.id | |
| campaign_id | UUID | FK NULL → campaigns.id | |
| pool_id | UUID | FK NULL → gmail_account_pools.id | |
| score_delta | INT | NOT NULL | Risk score increment |
| details | JSONB | DEFAULT '{}' | Event context |
| acknowledged_at | TIMESTAMPTZ | NULL | Manual review timestamp |
| created_at | TIMESTAMPTZ | NOT NULL | |

**Indexes:** `INDEX(user_id, created_at DESC)`, `INDEX(event_type)`, `INDEX(acknowledged_at)`  
**Relationships:** N:1 → users, gmail_accounts, campaigns, gmail_account_pools

---

### 4.15 Entity Relationship Diagram

```
users ─────┬───── gmail_accounts ───── oauth_tokens
           │            │
           │            ├──── sent_emails ──── reply_events
           │            ├──── bounce_events
           │            ├──── account_health_events
           │            └──── gmail_account_pool_members ─── gmail_account_pools
           │
           ├──── email_templates
           │
           ├──── campaigns ───── leads ───── lead_import_batches
           │         │            │
           │         └──── send_jobs ──── sent_emails
           │
           ├──── unsubscribe_list
           ├──── risk_budget_events
           └──── audit_logs
```

---

## 5. Backend API Endpoints

**Base URL:** `/api/v1`  
**Auth:** Bearer JWT in `Authorization` header OR `httpOnly` cookie `access_token`  
**Errors:** `{ "detail": string, "code": string, "errors": [] }`

### 5.1 Auth

#### POST `/auth/register`
| | |
|---|---|
| **Body** | `{ "email": "user@example.com", "password": "min8chars", "full_name": "..." }` |
| **Validation** | Email format; password ≥8 chars, 1 upper, 1 number |
| **Response 201** | `{ "id", "email", "full_name" }` |
| **Errors** | 409 email exists |

#### POST `/auth/login`
| | |
|---|---|
| **Body** | `{ "email", "password" }` |
| **Response 200** | `{ "access_token", "token_type": "bearer", "expires_in": 3600 }` + Set-Cookie httpOnly |
| **Errors** | 401 invalid credentials |

#### POST `/auth/logout`
| | |
|---|---|
| **Response 204** | Clears cookie |

#### GET `/auth/me`
| | |
|---|---|
| **Response 200** | `{ "id", "email", "full_name", "timezone" }` |

---

### 5.2 Gmail OAuth

#### GET `/gmail/connect`
| | |
|---|---|
| **Query** | `redirect_uri` (optional override) |
| **Response 302** | Redirect to Google OAuth URL with state |
| **Side effect** | Redis `oauth_state:{nonce}` → `{user_id, created_at}` |

#### GET `/gmail/callback`
| | |
|---|---|
| **Query** | `code`, `state` (required) |
| **Response 302** | Redirect to `{FRONTEND_URL}/accounts?connected=1` |
| **Validation** | State exists in Redis; not expired; user owns session |
| **Errors** | 400 invalid state; 502 token exchange failed |

#### POST `/gmail/accounts/{account_id}/revoke`
| | |
|---|---|
| **Response 200** | `{ "status": "revoked" }` |
| **Side effect** | Google revoke + soft-delete account |

---

### 5.3 Gmail Account Management

#### GET `/gmail/accounts`
| | |
|---|---|
| **Response 200** | `{ "items": [{ "id", "email", "status", "account_tier", "risk_level", "review_required", "health_score", "tier_daily_default", "tier_daily_hard_max", "daily_send_limit", "hourly_send_limit", "connected_at", "consecutive_success_days", "bounce_rate_7d", "error_rate_7d", "recent_quota_errors", "recent_auth_errors", "last_send_at", "sent_today", "sent_this_hour", "granted_scopes" }] }` |

#### GET `/gmail/accounts/{id}`
| | |
|---|---|
| **Response 200** | Full account detail + recent health events |

#### PATCH `/gmail/accounts/{id}`
| | |
|---|---|
| **Body** | `{ "daily_send_limit"?: int, "hourly_send_limit"?: int }` (decrease only without admin flag) |
| **Validation** | Values ≤ `tier_daily_hard_max`; never exceed account tier max |
| **Response 200** | Updated account |

#### POST `/gmail/accounts/{id}/pause`
| | |
|---|---|
| **Body** | `{ "reason": "manual" }` |
| **Response 200** | `{ "status": "paused" }` |

#### POST `/gmail/accounts/{id}/resume`
| | |
|---|---|
| **Validation** | status != auth_error |
| **Response 200** | `{ "status": "active" }` |

#### POST `/gmail/accounts/{id}/review`
| | |
|---|---|
| **Body** | `{ "approved": bool, "notes"?: string, "new_tier"?: string }` |
| **Validation** | Only when `review_required == true` |
| **Response 200** | Clears review flag; may promote from `restricted` |
| **Side effect** | Audit log entry |

#### POST `/gmail/accounts/{id}/set-tier`
| | |
|---|---|
| **Body** | `{ "account_tier": "new"|"warming"|"stable"|"trusted"|"restricted"|"paused", "reason": string }` |
| **Validation** | Manual override; requires audit reason |
| **Response 200** | Updated account with recalculated caps |

---

### 5.3a Gmail Account Pools

#### GET `/gmail/account-pools`
| | |
|---|---|
| **Response 200** | Paginated list of pools with member counts and capacity stats |

#### POST `/gmail/account-pools`
| | |
|---|---|
| **Body** | `{ "name", "description"?, "max_daily_send"?, "max_hourly_send"?, "active_account_limit"?, "risk_policy"? }` |
| **Response 201** | Pool object |

#### GET `/gmail/account-pools/{id}`
| | |
|---|---|
| **Response 200** | Pool detail + members + sends today/hour |

#### PATCH `/gmail/account-pools/{id}`
| | |
|---|---|
| **Body** | Partial update of caps, status, description |
| **Response 200** | Updated pool |

#### POST `/gmail/account-pools/{id}/members`
| | |
|---|---|
| **Body** | `{ "gmail_account_id", "priority"?, "is_active"?: true }` |
| **Response 201** | Membership row |

#### DELETE `/gmail/account-pools/{id}/members/{account_id}`
| | |
|---|---|
| **Response 204** | Remove account from pool |

---

### 5.3b Risk Budget

#### GET `/risk/overview`
| | |
|---|---|
| **Response 200** | `{ "global_risk_score", "threshold", "review_required", "recent_events_count", "paused_campaigns" }` |

#### GET `/risk/events`
| | |
|---|---|
| **Query** | `from`, `to`, `event_type`, `page` |
| **Response 200** | Paginated `risk_budget_events` |

#### POST `/risk/acknowledge`
| | |
|---|---|
| **Body** | `{ "event_ids"?: [], "acknowledge_all"?: bool, "notes"?: string }` |
| **Response 200** | Clears `risk_review_required`; allows new campaign starts |
| **Side effect** | Audit log entry |

---

### 5.4 Campaigns CRUD

#### POST `/campaigns`
| | |
|---|---|
| **Body** | `{ "name", "template_id", "campaign_account_pool_id", "scheduled_start_at"?, "timezone"?, "send_window_start_hour"?, "send_window_end_hour"? }` |
| **Response 201** | Campaign object |

#### GET `/campaigns`
| | |
|---|---|
| **Query** | `status`, `page`, `limit` |
| **Response 200** | Paginated list |

#### GET `/campaigns/{id}`
| | |
|---|---|
| **Response 200** | Campaign + stats |

#### PATCH `/campaigns/{id}`
| | |
|---|---|
| **Body** | Partial update (only if draft or paused) |
| **Response 200** | Updated campaign |

#### DELETE `/campaigns/{id}`
| | |
|---|---|
| **Response 204** | Soft delete; cancel pending jobs |

#### POST `/campaigns/{id}/start`
| | |
|---|---|
| **Validation** | Preflight must pass; global risk budget acceptable |
| **Response 200** | `{ "status": "scheduled" \| "running" }` |

#### POST `/campaigns/{id}/preflight-check`
| | |
|---|---|
| **Purpose** | Validate campaign readiness before start |
| **Response 200** | `{ "passed": bool, "checks": [{ "name", "passed", "message" }] }` |
| **Checks** | Valid template with unsubscribe; valid account pool; pool has active accounts; leads valid; no suppressed leads queued; rate limits allow projected volume; global risk budget acceptable |
| **Side effect** | Sets `preflight_passed_at` on success |

#### POST `/campaigns/{id}/pause`
#### POST `/campaigns/{id}/resume`

---

### 5.5 Leads Import/Export

#### POST `/campaigns/{id}/leads/import`
| | |
|---|---|
| **Body** | `multipart/form-data`: CSV file + `compliance_acknowledged=true` + `source_label`? + `allow_role_based_emails`? |
| **Validation** | Reject if `compliance_acknowledged` is false; warn if source missing |
| **Response 202** | `{ "import_batch_id", "status": "processing" }` |
| **Async** | Celery `import_leads` task |

#### GET `/campaigns/{id}/leads/import/{job_id}`
| | |
|---|---|
| **Response 200** | `{ "status", "imported", "skipped", "errors": [] }` |

#### GET `/campaigns/{id}/leads`
| | |
|---|---|
| **Query** | `status`, `page`, `limit`, `search` |
| **Response 200** | Paginated leads |

#### GET `/campaigns/{id}/leads/export`
| | |
|---|---|
| **Query** | `status` filter |
| **Response 200** | CSV stream |

#### DELETE `/campaigns/{id}/leads/{lead_id}`
| | |
|---|---|
| **Response 204** | Only if not sent |

---

### 5.6 Templates CRUD

#### POST `/templates`
| | |
|---|---|
| **Body** | `{ "name", "subject_template", "html_template", "text_template"? }` |
| **Validation** | Must contain `{{unsubscribe_url}}` in html or text |
| **Response 201** | Template object |

#### GET `/templates`
#### GET `/templates/{id}`
#### PATCH `/templates/{id}`
#### DELETE `/templates/{id}`

#### POST `/templates/{id}/preview`
| | |
|---|---|
| **Body** | `{ "lead_sample": { "email", "first_name", ... } }` |
| **Response 200** | `{ "subject", "html", "text" }` |

---

### 5.7 Send Jobs & Scheduler

#### GET `/campaigns/{id}/send-jobs`
| | |
|---|---|
| **Query** | `status`, `page` |
| **Response 200** | Job list with scheduled_at |

#### POST `/scheduler/tick` (internal/admin)
| | |
|---|---|
| **Auth** | Service token |
| **Response 200** | `{ "jobs_created": N }` |

#### GET `/queue/stats`
| | |
|---|---|
| **Response 200** | `{ "pending", "locked", "failed", "sent_today" }` |

---

### 5.8 Reply Sync

#### POST `/gmail/accounts/{id}/sync-replies`
| | |
|---|---|
| **Response 202** | `{ "task_id" }` |

#### GET `/replies`
| | |
|---|---|
| **Query** | `campaign_id`, `page` |
| **Response 200** | Reply events with lead context |

---

### 5.9 Unsubscribe (Public)

#### GET `/unsubscribe/{token}`
| | |
|---|---|
| **Auth** | None (signed JWT token) |
| **Response 200** | HTML confirmation page |

#### POST `/unsubscribe/{token}`
| | |
|---|---|
| **Auth** | None |
| **Response 200** | `{ "status": "unsubscribed" }` |
| **Side effect** | Insert unsubscribe_list; cancel pending jobs for lead |

#### GET `/unsubscribes` (authenticated)
| | |
|---|---|
| **Response 200** | Paginated unsubscribe list |

#### POST `/unsubscribes/manual`
| | |
|---|---|
| **Body** | `{ "email" }` |
| **Response 201** | Manual suppression entry |

---

### 5.10 Analytics

#### GET `/analytics/overview`
| | |
|---|---|
| **Query** | `from`, `to` |
| **Response 200** | `{ "sent", "replied", "bounced", "unsubscribed", "reply_rate", "bounce_rate" }` |

#### GET `/analytics/campaigns/{id}`
| | |
|---|---|
| **Response 200** | `{ "funnel", "daily_breakdown": [], "account_breakdown": [] }` |

---

### 5.11 Account Health

#### GET `/health/accounts`
| | |
|---|---|
| **Response 200** | All accounts with score + alerts |

#### GET `/health/accounts/{id}/events`
| | |
|---|---|
| **Response 200** | Health event timeline |

---

### 5.12 Audit Logs

#### GET `/audit-logs`
| | |
|---|---|
| **Query** | `action`, `resource_type`, `from`, `to`, `page` |
| **Response 200** | Paginated audit entries |

---

## 6. Background Worker Functions

### 6.1 `connect_gmail_account(user_id, auth_code, state)`

| | |
|---|---|
| **Purpose** | Complete OAuth; persist account + encrypted tokens |
| **Inputs** | User ID, authorization code, CSRF state |
| **Outputs** | `GmailAccount` record |
| **Failure** | Invalid state → raise `OAuthStateError`; exchange fail → `TokenExchangeError`, no partial DB writes |
| **Security** | Validate state nonce; never log code or tokens |

---

### 6.2 `refresh_google_token(gmail_account_id)`

| | |
|---|---|
| **Purpose** | Refresh access token; update Redis cache |
| **Inputs** | gmail_account_id |
| **Outputs** | `{ access_token, expires_at }` (in Redis) |
| **Failure** | `invalid_grant` → `pause_account(reason='auth_error')`; increment `refresh_fail_count` |
| **Security** | Decrypt refresh token in memory only; zero after use |

---

### 6.3 `create_campaign(user_id, payload)`

| | |
|---|---|
| **Purpose** | Validate and insert campaign |
| **Inputs** | User ID, campaign schema |
| **Outputs** | Campaign ORM object |
| **Failure** | Invalid template/account → `ValidationError` |
| **Security** | Verify account ownership |

---

### 6.4 `import_leads(campaign_id, csv_path)`

| | |
|---|---|
| **Purpose** | Parse CSV; bulk insert leads; enqueue validation |
| **Inputs** | Campaign ID, file path |
| **Outputs** | `{ imported, skipped, errors }` |
| **Failure** | Row-level errors collected; transaction per batch of 500 |
| **Security** | Max file 10MB; 50k rows; sanitize fields |

---

### 6.5 `validate_lead_email(lead_id)`

| | |
|---|---|
| **Purpose** | RFC syntax + MX DNS check |
| **Inputs** | lead_id |
| **Outputs** | `validation_status`: valid/invalid |
| **Failure** | DNS timeout → `unknown` (skip send) |
| **Security** | No external HTTP calls except DNS |

---

### 6.6 `render_email_template(template_id, lead_id, unsubscribe_url)`

| | |
|---|---|
| **Purpose** | Jinja2 render subject + bodies |
| **Inputs** | Template ID, lead, signed unsubscribe URL |
| **Outputs** | `{ subject, html, text }` |
| **Failure** | Template error → skip lead, log, mark failed |
| **Security** | Sandboxed Jinja2 (no filesystem); HTML escape default |

---

### 6.7 `create_send_jobs(campaign_id)`

| | |
|---|---|
| **Purpose** | Materialize pending jobs for valid, unsuppressed leads |
| **Inputs** | campaign_id |
| **Outputs** | Count of jobs created |
| **Failure** | Campaign not runnable → no-op |
| **Security** | Acquire `lock:campaign_scheduler:{campaign_id}` before insert; idempotency key prevents duplicates |

---

### 6.7a `run_campaign_preflight(campaign_id)`

| | |
|---|---|
| **Purpose** | Validate template, pool, leads, suppression, rate limits, risk budget |
| **Inputs** | campaign_id |
| **Outputs** | `{ passed: bool, checks: [{ name, passed, message }] }` |
| **Failure** | Any check fails → `passed=false` with reasons |
| **Security** | Block campaign start when global risk budget exceeded |

---

### 6.7b `evaluate_account_tier(gmail_account_id)`

| | |
|---|---|
| **Purpose** | Promote or demote account tier based on metrics |
| **Inputs** | gmail_account_id |
| **Outputs** | `{ account_tier, tier_daily_default, tier_daily_hard_max, promoted, demoted }` |
| **Promotion rules** | new→warming: 7 consecutive success days, bounce < 3%; warming→stable: 14 days, bounce < 3%, no quota errors; stable→trusted: 30 days, bounce < 2%, no auth/quota errors |
| **Demotion rules** | Any→restricted: repeated 403/429, auth errors, bounce spike, manual review flag |
| **Security** | restricted/paused accounts cannot send until manual review; audit every tier change |

---

### 6.8 `enforce_account_rate_limit(gmail_account_id)`

| | |
|---|---|
| **Purpose** | Check Redis counters + inter-send delay |
| **Inputs** | gmail_account_id |
| **Outputs** | `{ allowed: bool, retry_after_seconds: int }` |
| **Failure** | Redis down → fail closed (deny send) |
| **Security** | Per-account Redis keys namespaced |

---

### 6.9 `select_available_gmail_account(campaign_id)`

| | |
|---|---|
| **Purpose** | Pick account from campaign pool with tier capacity + pool budget |
| **Inputs** | campaign_id |
| **Outputs** | gmail_account_id or None |
| **Failure** | None available → reschedule job +5 min |
| **Security** | Respect pool `active_account_limit`; skip restricted/paused/review_required accounts; round-robin by priority |

---

### 6.10 `acquire_account_send_lock(gmail_account_id)`

| | |
|---|---|
| **Purpose** | Ensure only one Celery worker sends from a Gmail account at a time |
| **Inputs** | gmail_account_id |
| **Outputs** | `{ acquired: bool, lock_token: str }` |
| **Failure** | Lock held → reschedule job +30–60s |
| **Security** | Redis `SET lock:gmail_account:{id} {worker_id} NX EX 600`; release via Lua compare-and-del in `finally` after `record_sent_email` |

---

### 6.10a `acquire_scheduler_lock(campaign_id)` / `acquire_token_refresh_lock(account_id)`

| Lock Key | TTL | When |
|----------|-----|------|
| `lock:campaign_scheduler:{campaign_id}` | 10 min | Before `create_send_jobs` |
| `lock:token_refresh:{account_id}` | 10 min | Before `refresh_google_token` |

### 6.11 `send_email_via_gmail_api(gmail_account_id, message)`

| | |
|---|---|
| **Purpose** | Send MIME message via `users.messages.send` |
| **Inputs** | Account ID, `{to, subject, html, text, headers}` |
| **Outputs** | `{ gmail_message_id, thread_id, rfc_message_id }` |
| **Failure** | 401 → refresh token retry once; 429 → backoff; 403 → pause account |
| **Security** | Include List-Unsubscribe headers; no BCC abuse |

---

### 6.12 `record_sent_email(send_job_id, gmail_response, rendered)`

| | |
|---|---|
| **Purpose** | Persist sent_emails; update lead + campaign counters |
| **Inputs** | Job ID, Gmail response, rendered content |
| **Outputs** | `SentEmail` record |
| **Failure** | DB error → compensating retry; Gmail already sent → log critical |
| **Security** | Store subject; not full body in DB (optional truncation) |

---

### 6.13 `sync_replies(gmail_account_id)`

| | |
|---|---|
| **Purpose** | Fetch recent threads; match to sent_emails |
| **Inputs** | gmail_account_id |
| **Outputs** | `{ new_replies: int }` |
| **Failure** | API error → exponential backoff |
| **Security** | Read-only scope; store snippet only |

---

### 6.14 `detect_bounces(gmail_account_id)`

| | |
|---|---|
| **Purpose** | Multi-signal bounce parser; extract bounced address |
| **Inputs** | gmail_account_id |
| **Outputs** | `{ bounces_recorded: int }` |
| **Failure** | Parse failure → log malformed; do not suppress without recipient proof |
| **Security** | Read-only fetch; never execute attachments |
| **Signals** | From: mailer-daemon, postmaster, mail delivery subsystem; Subject: DSN patterns; MIME: delivery-status, rfc822-headers; DSN fields; SMTP 5.x.x/4.x.x; regex fallback |
| **Fixtures** | Gmail mailer-daemon, Google Workspace, Outlook, soft bounce, malformed |

---

### 6.15 `process_unsubscribe(token)`

| | |
|---|---|
| **Purpose** | Verify JWT; add to suppression; cancel jobs |
| **Inputs** | Signed unsubscribe token |
| **Outputs** | `{ email, status }` |
| **Failure** | Invalid/expired token → 400 |
| **Security** | JWT signed with `UNSUBSCRIBE_SECRET`; 90-day expiry |

---

### 6.16 `update_account_health(gmail_account_id)`

| | |
|---|---|
| **Purpose** | Recompute health score, rolling rates; call `evaluate_account_tier`; write snapshot |
| **Inputs** | gmail_account_id |
| **Outputs** | `{ score, account_tier, risk_level, should_pause, review_required }` |
| **Failure** | — |
| **Security** | Tier demotion automatic; promotion requires clean metrics; restricted = 0 sends |

---

### 6.17 `pause_account(gmail_account_id, reason)`

| | |
|---|---|
| **Purpose** | Set status paused; cancel locked jobs |
| **Inputs** | Account ID, reason string |
| **Outputs** | Updated account |
| **Failure** | — |
| **Security** | Audit log entry required |

---

### 6.18 `pause_campaign(campaign_id, reason)`

| | |
|---|---|
| **Purpose** | Pause campaign + pending jobs |
| **Inputs** | Campaign ID, reason |
| **Outputs** | Updated campaign |
| **Failure** | — |
| **Security** | Audit log entry |

---

### 6.19 `retry_failed_job_with_backoff(send_job_id)`

| | |
|---|---|
| **Purpose** | Retry transient failures |
| **Inputs** | send_job_id |
| **Outputs** | Rescheduled job or terminal failure |
| **Failure** | Max attempts (2) → mark failed permanently |
| **Security** | Never retry 400-class errors or bounces |

---

### 6.20 `generate_campaign_analytics(campaign_id)`

| | |
|---|---|
| **Purpose** | Aggregate funnel metrics |
| **Inputs** | campaign_id |
| **Outputs** | Analytics dict |
| **Failure** | — |
| **Security** | User ownership check |

---

### 6.21 `record_risk_event(user_id, event_type, score_delta, ...)`

| | |
|---|---|
| **Purpose** | Append risk budget event; update user `global_risk_score` |
| **Inputs** | user_id, event_type, severity, score_delta, optional account/campaign/pool IDs |
| **Outputs** | `{ new_score, threshold_exceeded }` |
| **Failure** | — |
| **Security** | On threshold exceed: set `risk_review_required`, block new campaign starts and send_jobs |

---

## 7. Rate Limiting and Account Protection

### 7.1 Safe Sending Logic

```
┌─────────────────────────────────────────────────────────────┐
│                    SEND GATE CHECKLIST                       │
│  (evaluated in order for every send_job)                     │
├─────────────────────────────────────────────────────────────┤
│  1. Campaign status == running?                              │
│  2. Global risk budget not exceeded?                         │
│  3. Current time in send window?                             │
│  4. Lead status == queued/pending?                           │
│  5. Lead NOT in unsubscribe_list?                            │
│  6. Lead NOT in bounce suppression?                          │
│  7. Lead validation_status == valid?                         │
│  8. Gmail account status == active?                          │
│  9. Account tier allows sending (not restricted/paused)?     │
│ 10. Account review_required == false?                        │
│ 11. Account health_score >= 30?                              │
│ 12. Account daily count < effective_daily_cap?               │
│ 13. Account hourly count < effective_hourly_cap?             │
│ 14. Account pool has daily/hourly capacity?                  │
│ 15. Pool active_account_limit not exceeded?                  │
│ 16. Recent account errors below threshold?                   │
│ 17. Recent pool errors below threshold?                      │
│ 18. Global daily count < global_daily_limit?                 │
│ 19. now - last_send_at >= random(120, 480) seconds?          │
│ 20. lock:gmail_account:{id} acquired?                        │
│                                                              │
│  ALL pass → send                                           │
│  ANY fail → reschedule with retry_after                      │
└─────────────────────────────────────────────────────────────┘
```

### 7.2 Account Tier Caps

Effective daily cap = `min(user_override, tier_daily_default, tier_daily_hard_max)`.

| Account Tier | Default/Day | Hard Max/Day | Hourly Cap | Sends Allowed |
|--------------|-------------|--------------|------------|---------------|
| `new` | **5** | **10** | 1 | Yes |
| `warming` | **10** | **20** | 3 | Yes |
| `stable` | **20** | **50** | 5 | Yes |
| `trusted` | **30** | **75** | 8 | Yes |
| `restricted` | 0 | 0 | 0 | No — manual review required |
| `paused` | 0 | 0 | 0 | No |

**Replaces previous limits:** per-account daily default 50, hard max 100, and new-account week-1 cap of 20/day were too aggressive for personal Gmail.

### 7.3 Account Tier Promotion & Demotion

Evaluated daily by `evaluate_account_tier()`:

| Transition | Requirements |
|------------|--------------|
| `new` → `warming` | 7 consecutive successful days; bounce rate < 3% |
| `warming` → `stable` | 14 consecutive successful days; bounce < 3%; zero quota errors |
| `stable` → `trusted` | 30 consecutive successful days; bounce < 2%; zero auth/quota errors |
| any → `restricted` | Repeated Google 403/429; auth errors; bounce spike; manual review |
| any → `paused` | Manual pause or auth_error |

**Restricted accounts:** `review_required = true`; 0 sends until `POST /gmail/accounts/{id}/review`.

### 7.4 Pool & Global Limits

| Limit | Default | Hard Max |
|-------|---------|----------|
| Pool `max_daily_send` | 200 | 1000 |
| Pool `max_hourly_send` | 40 | 100 |
| Pool `active_account_limit` | 10 | 50 |
| Global daily (all accounts) | 200 | 500 |
| Inter-send delay | 120–480s random | min 60s |
| Concurrent sends per account | **1** (Redis lock) | 1 |
| Global risk score threshold | 100 | configurable |

### 7.5 Global Risk Budget

| Event Type | Score Delta |
|------------|-------------|
| Quota error (403/429) | +30 |
| Auth error / invalid_grant | +50 |
| Bounce spike (>8% in 24h) | +40 |
| High failure rate (>10% in 24h) | +30 |
| Manual warning | +20 |

**When global risk score exceeds threshold:** pause new campaign starts; block new `send_jobs`; continue reply sync + unsubscribe; show dashboard warning; require `POST /risk/acknowledge`.

### 7.6 Auto-Pause Triggers

| Trigger | Action |
|---------|--------|
| 3 consecutive send failures | `pause_account` |
| Gmail API 429 | Pause 1 hour + risk event |
| Gmail API 403 quota | Pause 24 hours + risk event + tier demotion |
| `invalid_grant` on refresh | `auth_error`; tier → restricted |
| Bounce rate > 8% (24h, min 20 sends) | `pause_campaign` + risk event |
| Account tier → restricted | 0 sends; review queue |
| Global risk threshold exceeded | Block new sends for user |

### 7.7 Suppression Rules

- **Unsubscribe:** Global per `user_id + email`; never overridden
- **Hard bounce:** Permanent global suppression
- **Soft bounce:** 3 events → suppression
- **Role-based email:** Blocked at import unless batch override
- **Duplicate recipient:** Same `campaign_id + normalized_email` blocked
- **Cross-campaign:** Unsubscribe applies to all campaigns for that user

### 7.8 Redis Lock Requirements

| Lock Key | TTL | Acquired | Released |
|----------|-----|----------|----------|
| `lock:gmail_account:{account_id}` | 10 min | Before render/send | After send result recorded (`finally`) |
| `lock:campaign_scheduler:{campaign_id}` | 10 min | Before job materialization | After jobs created |
| `lock:token_refresh:{account_id}` | 10 min | Before token refresh | After refresh completes |

If a worker dies, TTL prevents permanent lock. Stale locks > 9 min logged by health monitor.

### 7.9 Deliverability Best Practices (Built-In)

| Practice | Implementation |
|----------|----------------|
| Compliant tier ramp | `evaluate_account_tier()` — metrics-driven, not fake simulation |
| Account pools | Stagger sends; limit concurrent active accounts |
| Consistent From address | Always send from connected Gmail |
| Plain-text alternative | Always attach `text/plain` part |
| Unsubscribe header | RFC 8058 List-Unsubscribe-Post |
| No URL shorteners | Warn if template contains bit.ly etc. |
| Subject honesty | No RE:/FWD: injection in template validator |

### 7.10 Abuse Patterns the Platform MUST Block

| Pattern | Platform Response |
|---------|-------------------|
| Sending without unsubscribe link | Template validation reject |
| Import without compliance acknowledgement | API 400 |
| Importing >10k leads/day | Hard reject |
| Attempting to raise limits above tier hard max | API 400 |
| Bypassing suppression via re-import | Dedup + global block |
| Parallel send tasks for same account | Redis lock prevents |
| Role-based emails without override | Skipped at import |
| CAPTCHA/proxy/fingerprint evasion | **Not supported — out of scope** |

---

## 8. Gmail API Integration

### 8.1 OAuth Scopes (Least Privilege)

```
https://www.googleapis.com/auth/gmail.send
https://www.googleapis.com/auth/gmail.readonly
openid
email
profile
```

**Not requested (MVP):** `gmail.modify`, `gmail.compose`, full mailbox access, Drive, Contacts.

**MVP uses `gmail.readonly` for reply sync and bounce detection.** This is sufficient for reading inbox metadata and message bodies. If a future phase needs Gmail labels (`Replied`, `Bounced`, etc.), add `gmail.modify` via a separate re-consent flow — do not request it at initial connect.

### 8.2 OAuth Setup Steps

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create project → Enable **Gmail API**
3. Configure **OAuth consent screen** (External → Testing → add test users)
4. Create **OAuth 2.0 Client ID** (Web application)
5. Authorized redirect URI: `http://localhost:8000/api/v1/gmail/callback`
6. Store `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` in `.env`
7. **TODO:** For production, submit app for Google verification

### 8.3 Token Storage Strategy

```
Refresh Token → AES-256-GCM encrypt → PostgreSQL oauth_tokens.encrypted_refresh_token
Access Token  → Redis gmail:access:{account_id} TTL = expires_in - 60
OAuth State   → Redis oauth_state:{nonce} TTL = 600
```

**Key derivation:** `TOKEN_ENCRYPTION_KEY` = 32-byte base64 env var.

### 8.4 Sending Email Flow

```python
# Pseudocode — see workers/sender.py
message = MIMEMultipart("alternative")
message["To"] = lead.email
message["From"] = gmail_account.email
message["Subject"] = rendered_subject
message["List-Unsubscribe"] = f"<{unsubscribe_url}>"
message["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
message.attach(MIMEText(text_body, "plain"))
message.attach(MIMEText(html_body, "html"))

raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
response = gmail_service.users().messages().send(
    userId="me", body={"raw": raw}
).execute()
```

### 8.5 Reading Replies Flow

1. `users.messages.list(q="in:inbox newer_than:7d")`
2. For each message: `users.messages.get(format="metadata", metadataHeaders=["In-Reply-To", "References", "From"])`
3. Match `In-Reply-To` or `References` to `sent_emails.rfc_message_id`
4. Insert `reply_events`; update `leads.status = replied`

### 8.6 Error Handling

| HTTP Code | Action |
|-----------|--------|
| 401 | Refresh token → retry once |
| 403 quota | `pause_account(24h)` |
| 429 | Exponential backoff: 60s, 120s, 300s |
| 400 bad request | Mark job failed; no retry |
| 5xx | Retry with backoff (max 2) |

### 8.7 Quota Handling

- Gmail API: 250 quota units/user/second (send = 100 units)
- Track daily send count internally (well below Google's limits)
- On `rateLimitExceeded` user-facing error: pause + dashboard alert

### 8.8 Revoking Access

```python
# POST https://oauth2.googleapis.com/revoke?token={refresh_token}
# Then: soft-delete gmail_account, delete Redis keys, cancel jobs
```

### 8.9 Google OAuth App Verification Considerations

Connecting many Gmail accounts through **one OAuth client** makes verification an operational requirement.

| Topic | Requirement |
|-------|-------------|
| **Testing mode** | OAuth app limited to **100 test users**; add only owned Gmail accounts as test users for private use |
| **Sensitive scopes** | `gmail.send` and `gmail.readonly` may require app verification before broader/public use |
| **Private/personal use** | Keep app in Testing; explicitly add each Gmail as test user |
| **Production/public use** | Requires OAuth verification + privacy policy + terms of service |
| **Scope display** | Store and show `granted_scopes` per account in dashboard |
| **Error handling** | Clear UI for `access_denied` and app-not-verified errors |
| **Least privilege** | Do not request broader scopes unless required |

| Consent Screen State | Behavior | Platform Action |
|---------------------|----------|-----------------|
| **Testing** | Max 100 test users; unverified warning | Track count; block at cap |
| **In review** | Existing users work | Status banner on connect page |
| **Published (unverified)** | Sensitive scope warning | Recommend verification before scale |
| **Published + verified** | Required for 10+ accounts | Target production state |

### 8.10 Bounce Detection Pipeline

Multi-signal parser — do **not** rely on labels or subject alone.

**From header signals:** mailer-daemon, postmaster, mail delivery subsystem

**Subject signals:** Delivery Status Notification, Undelivered Mail Returned to Sender, Delivery has failed, Address not found, Mail delivery failed

**MIME parts:** `message/delivery-status`, `text/rfc822-headers`

**DSN fields:** Final-Recipient, Original-Recipient, Action, Status, Diagnostic-Code

**SMTP classification:** 5.x.x = hard bounce; 4.x.x = soft bounce

**Fallback:** Regex extraction for bounced recipient when DSN incomplete

| SMTP Status | Classification | Action |
|-------------|----------------|--------|
| 5.x.x | Hard bounce | Immediate global suppression |
| 4.x.x | Soft bounce | 3 strikes then suppression |
| Unknown + mailer-daemon | Soft / manual review | Log + flag if recipient unconfirmed |

**Test fixtures required:**

| Fixture | File |
|---------|------|
| Gmail mailer-daemon bounce | `tests/fixtures/bounce_gmail_mailer_daemon.eml` |
| Google Workspace bounce | `tests/fixtures/bounce_google_workspace.eml` |
| Outlook bounce | `tests/fixtures/bounce_outlook.eml` |
| Soft bounce (4.x.x) | `tests/fixtures/bounce_soft.eml` |
| Malformed bounce | `tests/fixtures/bounce_malformed.eml` |

### 8.11 Scope Upgrade Path (`gmail.modify`) — Post-MVP

| Capability | MVP (`readonly`) | Future (`modify`) |
|------------|------------------|-------------------|
| Read replies | ✓ | ✓ |
| Detect bounces | ✓ | ✓ |
| Apply labels (`Outreach/Replied`) | ✗ | ✓ |
| Mark bounces read/archived | ✗ | ✓ |

Require explicit re-consent; never silently expand scopes on token refresh.

---

## 9. Frontend Pages

### 9.1 Login (`/login`)

| | |
|---|---|
| **Components** | `LoginForm`, `AuthLayout` |
| **Actions** | Submit credentials; redirect to dashboard |
| **API** | `POST /auth/login` |
| **Metrics** | — |

### 9.2 Dashboard (`/`)

| | |
|---|---|
| **Components** | `StatCards`, `ActiveCampaignsList`, `AccountHealthSummary`, `RecentReplies` |
| **Actions** | Quick pause campaign; navigate to details |
| **API** | `GET /analytics/overview`, `GET /campaigns?status=running`, `GET /health/accounts` |
| **Metrics** | Sent today, reply rate, bounce rate, active campaigns, paused accounts |

### 9.3 Gmail Accounts (`/accounts`)

| | |
|---|---|
| **Components** | `AccountCard`, `AccountTierBadge`, `LimitSlider`, `PauseResumeButton`, `GrantedScopesList` |
| **Actions** | Pause/resume; adjust limits; revoke; submit for review |
| **API** | `GET /gmail/accounts`, `PATCH`, `POST pause/resume/review/set-tier` |
| **Metrics** | Tier, risk level, connected age, consecutive success days, quota/auth errors, review_required, sends today/hour |

### 9.3a Account Pools (`/account-pools`)

| | |
|---|---|
| **Components** | `PoolTable`, `PoolForm`, `PoolMemberList`, `PoolCapacityChart` |
| **Actions** | CRUD pools; add/remove members; set priority |
| **API** | `GET/POST/PATCH /gmail/account-pools`, members endpoints |
| **Metrics** | Pool sends today/hour, active accounts, capacity remaining |

### 9.3b Account Review Queue (`/accounts/review`)

| | |
|---|---|
| **Components** | `ReviewQueueTable`, `ReviewModal`, `TierOverrideForm` |
| **Actions** | Approve/reject restricted accounts |
| **API** | `POST /gmail/accounts/{id}/review`, `POST /gmail/accounts/{id}/set-tier` |
| **Metrics** | Pending review count |

### 9.3c Risk Dashboard (`/risk`)

| | |
|---|---|
| **Components** | `RiskScoreGauge`, `RiskEventTimeline`, `RiskAcknowledgeButton` |
| **Actions** | Acknowledge risk events; review blocked campaigns |
| **API** | `GET /risk/overview`, `GET /risk/events`, `POST /risk/acknowledge` |
| **Metrics** | Global score, threshold, recent events |

### 9.4 Connect Gmail (`/accounts/connect`)

| | |
|---|---|
| **Components** | `ConnectGmailButton`, `OAuthInstructions` |
| **Actions** | Redirect to `GET /gmail/connect` |
| **API** | OAuth redirect (full page navigation) |
| **Metrics** | — |

### 9.5 Campaigns (`/campaigns`)

| | |
|---|---|
| **Components** | `CampaignTable`, `CreateCampaignModal`, `StatusBadge` |
| **Actions** | Create, start, pause, delete |
| **API** | `GET/POST /campaigns`, `POST /campaigns/{id}/start` |
| **Metrics** | Status, sent/replied counts, schedule |

### 9.6 Campaign Detail (`/campaigns/[id]`)

| | |
|---|---|
| **Components** | `CampaignHeader`, `LeadStats`, `SendQueueTable`, `FunnelChart`, `CampaignPreflightModal` |
| **Actions** | Import leads, run preflight, start/pause, edit schedule |
| **API** | `GET /campaigns/{id}`, `POST /preflight-check`, `POST /start` |
| **Metrics** | Funnel: pending → sent → replied → bounced |

### 9.7 Leads (`/campaigns/[id]/leads`)

| | |
|---|---|
| **Components** | `LeadTable`, `CSVUploadDropzone`, `ImportComplianceConfirmation`, `ImportJobStatus` |
| **Actions** | Upload CSV with compliance ack; export; delete pending |
| **API** | `POST /leads/import` (requires `compliance_acknowledged=true`) |
| **Metrics** | Validation breakdown |

### 9.8 Templates (`/templates`)

| | |
|---|---|
| **Components** | `TemplateList`, `TemplateEditor` (subject + HTML + preview) |
| **Actions** | CRUD, preview with sample lead |
| **API** | `GET/POST/PATCH /templates`, `POST /templates/{id}/preview` |
| **Metrics** | Variable auto-complete list |

### 9.9 Sending Queue (`/queue`)

| | |
|---|---|
| **Components** | `QueueStats`, `PendingJobsTable`, `FailedJobsTable` |
| **Actions** | Retry failed (manual), cancel pending |
| **API** | `GET /queue/stats`, `GET /campaigns/{id}/send-jobs` |
| **Metrics** | Pending, locked, failed, throughput/hour |

### 9.10 Inbox/Replies (`/replies`)

| | |
|---|---|
| **Components** | `ReplyFeed`, `ReplyDetail`, `CampaignFilter` |
| **Actions** | Mark read; open in Gmail (link) |
| **API** | `GET /replies`, `POST /gmail/accounts/{id}/sync-replies` |
| **Metrics** | Reply count, avg response time |

### 9.11 Unsubscribes (`/unsubscribes`)

| | |
|---|---|
| **Components** | `UnsubscribeTable`, `ManualAddForm` |
| **Actions** | Manual add email |
| **API** | `GET /unsubscribes`, `POST /unsubscribes/manual` |
| **Metrics** | Total suppressed, recent unsubscribes |

### 9.12 Account Health (`/health`)

| | |
|---|---|
| **Components** | `HealthScoreGauge`, `HealthTimeline`, `AlertBanner` |
| **Actions** | Acknowledge alert; pause account |
| **API** | `GET /health/accounts`, `GET /health/accounts/{id}/events` |
| **Metrics** | Score, bounce rate 24h, failure count |

### 9.13 Analytics (`/analytics`)

| | |
|---|---|
| **Components** | `DateRangePicker`, `CampaignComparisonChart`, `DailySendChart` |
| **Actions** | Filter date range; export CSV |
| **API** | `GET /analytics/overview`, `GET /analytics/campaigns/{id}` |
| **Metrics** | Reply rate, bounce rate, unsubscribe rate trends |

### 9.14 Settings (`/settings`)

| | |
|---|---|
| **Components** | `ProfileForm`, `TimezoneSelect`, `GlobalLimitsForm`, `ComplianceNotice` |
| **Actions** | Update profile, timezone, global daily cap |
| **API** | `GET/PATCH /auth/me`, settings endpoint |
| **Metrics** | — |

### 9.15 Audit Logs (`/audit-logs`)

| | |
|---|---|
| **Components** | `AuditLogTable`, `ActionFilter` |
| **Actions** | Filter by action/resource/date |
| **API** | `GET /audit-logs` |
| **Metrics** | Event count |

---

## 10. MVP Build Phases

> **Build order rule:** Account pools and preflight checks come **before** sender worker. Risk budget comes **before** scaling. Real Gmail API is **last** after mock end-to-end passes.

### Phase 1: Auth + Gmail OAuth

- [ ] Repo scaffold, Docker Compose (PostgreSQL, Redis)
- [ ] JWT auth: register, login, me
- [ ] Gmail OAuth connect/callback (mock + `USE_MOCK_GMAIL` toggle)
- [ ] Token encryption, OAuth state CSRF, audit log stub

**Tests:** `test_auth_register_login`, `test_oauth_state_invalid_rejected`, `test_token_encryption_roundtrip`

---

### Phase 2: Account Model + Token Storage + Account Tiers

- [ ] `gmail_accounts` with tier fields, `connected_at`, success/failure counters
- [ ] Token refresh with `lock:token_refresh:{id}`
- [ ] `evaluate_account_tier()` worker
- [ ] Account pause/resume/review/set-tier APIs

**Tests:** `test_account_tier_promotion`, `test_account_tier_demotion_on_quota_error`, `test_restricted_account_cannot_send`, `test_token_refresh_lock`

---

### Phase 3: Account Pools + Pool Membership

- [ ] `gmail_account_pools`, `gmail_account_pool_members` models + migrations
- [ ] Pool CRUD + member APIs
- [ ] Campaign `campaign_account_pool_id` FK (replace UUID arrays)

**Tests:** `test_account_pool_capacity`, `test_pool_active_account_limit`

---

### Phase 4: Campaigns + Templates + Lead Imports

- [ ] Campaigns, templates, leads, `lead_import_batches`
- [ ] CSV import with compliance acknowledgement
- [ ] Role-based email blocking, normalized_email dedup

**Tests:** `test_import_requires_compliance_acknowledgement`, `test_role_based_email_blocked`, `test_lead_dedup_per_campaign`

---

### Phase 5: Preflight Checks + Compliance Validation

- [ ] `run_campaign_preflight()` service
- [ ] `POST /campaigns/{id}/preflight-check` endpoint
- [ ] Block campaign start without passing preflight

**Tests:** `test_preflight_blocks_invalid_campaign`

---

### Phase 6: Queue + Sender Worker with Redis Locks

- [ ] send_jobs, sent_emails models
- [ ] Scheduler with `lock:campaign_scheduler:{id}`
- [ ] Sender with `lock:gmail_account:{id}`, tier caps, pool caps
- [ ] Mock Gmail send end-to-end

**Tests:** `test_sender_requires_account_lock`, `test_scheduler_lock_prevents_duplicate_jobs`, `test_sender_worker_mock`

---

### Phase 7: Replies + Bounces + Unsubscribes

- [ ] Multi-signal bounce parser + fixtures
- [ ] Reply sync, unsubscribe public endpoints
- [ ] Suppression in send gate

**Tests:** `test_bounce_parser_gmail_mailer_daemon`, `test_bounce_parser_soft_bounce`, `test_bounce_parser_malformed_message`, `test_unsubscribe_suppression`

---

### Phase 8: Risk Budget + Account Health + Analytics

- [ ] `risk_budget_events`, global risk score
- [ ] `record_risk_event()`, health monitor
- [ ] Analytics + audit log APIs

**Tests:** `test_global_risk_budget_pauses_new_campaigns`, `test_health_score_penalty`, `test_analytics_funnel`

---

### Phase 9: Frontend Dashboard Pages

- [ ] Account pools, review queue, risk dashboard
- [ ] Campaign preflight modal, import compliance confirmation
- [ ] Pool capacity chart, account tier badges
- [ ] All pages from Section 9

**Acceptance:** Manual walkthrough — connect account → create pool → import leads → preflight → start campaign (mock)

---

### Phase 10: Real Gmail API Integration

- [ ] Replace mock with real `GoogleGmailClient`
- [ ] Set `USE_MOCK_GMAIL=false`; add test users in Google Console
- [ ] E2E: connect → send 1 email → reply sync → bounce detect

**Tests:** `test_real_gmail_send` (manual, skipped in CI)

---

### Phase 11: Docker + Deployment Docs

- [ ] Full Docker Compose stack
- [ ] README setup, `COMPLIANCE.md`, OAuth verification guide
- [ ] Production notes (ECS/K8s stub)

**Tests:** `test_docker_compose_health`, `test_e2e_campaign_flow_mock`

---

## 11. Project File Structure

```
gmail-outreach-platform/
├── docker/
│   ├── docker-compose.yml          # postgres, redis, api, worker, beat, frontend
│   ├── docker-compose.test.yml     # test DB overlay
│   └── Dockerfile.api              # FastAPI production image
│   └── Dockerfile.worker           # Celery worker image
│   └── Dockerfile.frontend         # Next.js standalone
│
├── docs/
│   ├── TECHNICAL_REQUIREMENTS.md   # This document
│   ├── API.md                      # OpenAPI notes
│   └── COMPLIANCE.md               # User-facing compliance guide
│
├── backend/
│   ├── pyproject.toml              # Dependencies: fastapi, sqlalchemy, celery, etc.
│   ├── alembic.ini
│   ├── alembic/
│   │   └── versions/
│   │       └── 001_initial_schema.py
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app factory, CORS, routers
│   │   ├── config.py               # Pydantic Settings from env
│   │   ├── database.py             # SQLAlchemy engine, session
│   │   ├── dependencies.py         # get_db, get_current_user
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── user.py
│   │   │   ├── gmail_account.py
│   │   │   ├── account_pool.py
│   │   │   ├── oauth_token.py
│   │   │   ├── campaign.py
│   │   │   ├── lead.py
│   │   │   ├── lead_import_batch.py
│   │   │   ├── template.py
│   │   │   ├── send_job.py
│   │   │   ├── sent_email.py
│   │   │   ├── reply_event.py
│   │   │   ├── bounce_event.py
│   │   │   ├── unsubscribe.py
│   │   │   ├── health_event.py
│   │   │   ├── risk_budget_event.py
│   │   │   └── audit_log.py
│   │   ├── schemas/
│   │   │   ├── auth.py             # LoginRequest, TokenResponse, UserOut
│   │   │   ├── gmail.py
│   │   │   ├── campaign.py
│   │   │   ├── lead.py
│   │   │   ├── template.py
│   │   │   ├── analytics.py
│   │   │   └── common.py           # Pagination, ErrorResponse
│   │   ├── routers/
│   │   │   ├── auth.py
│   │   │   ├── gmail.py
│   │   │   ├── campaigns.py
│   │   │   ├── leads.py
│   │   │   ├── templates.py
│   │   │   ├── queue.py
│   │   │   ├── replies.py
│   │   │   ├── unsubscribe.py
│   │   │   ├── analytics.py
│   │   │   ├── health.py
│   │   │   └── audit.py
│   │   ├── services/
│   │   │   ├── auth_service.py     # bcrypt, JWT create/verify
│   │   │   ├── oauth_service.py    # Google OAuth flow
│   │   │   ├── token_service.py    # encrypt/decrypt, Redis cache
│   │   │   ├── campaign_service.py
│   │   │   ├── lead_service.py
│   │   │   ├── template_service.py # Jinja2 render
│   │   │   ├── rate_limit_service.py
│   │   │   ├── suppression_service.py
│   │   │   ├── analytics_service.py
│   │   │   ├── health_service.py
│   │   │   └── audit_service.py
│   │   ├── gmail/
│   │   │   ├── client.py           # Gmail API wrapper
│   │   │   ├── mock_client.py      # Mock for tests/dev
│   │   │   └── message_builder.py  # MIME construction
│   │   └── utils/
│   │       ├── crypto.py           # AES-256-GCM
│   │       ├── jwt_unsubscribe.py
│   │       └── logging.py          # Structured JSON logs
│   └── tests/
│       ├── conftest.py             # Test DB, fixtures, mock Gmail
│       ├── test_auth.py
│       ├── test_oauth.py
│       ├── test_campaigns.py
│       ├── test_rate_limits.py
│       ├── test_suppression.py
│       └── test_sender_worker.py
│
├── workers/
│   ├── celery_app.py               # Celery instance, beat schedule
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── sender.py               # send_email_via_gmail_api
│   │   ├── scheduler.py            # create_send_jobs, campaign transitions
│   │   ├── reply_sync.py
│   │   ├── bounce_detection.py
│   │   ├── token_refresh.py
│   │   ├── tier_evaluation.py
│   │   ├── preflight.py
│   │   ├── lead_import.py
│   │   ├── lead_validation.py
│   │   └── health_monitor.py
│   └── config.py                   # Worker-specific settings
│
├── backend/tests/fixtures/         # Bounce parser test fixtures (.eml)
│
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx            # Dashboard
│   │   │   ├── login/page.tsx
│   │   │   ├── account-pools/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/page.tsx
│   │   │   ├── accounts/
│   │   │   │   ├── page.tsx
│   │   │   │   ├── connect/page.tsx
│   │   │   │   └── review/page.tsx
│   │   │   ├── risk/page.tsx
│   │   │   ├── campaigns/
│   │   │   │   ├── page.tsx
│   │   │   │   └── [id]/
│   │   │   │       ├── page.tsx
│   │   │   │       └── leads/page.tsx
│   │   │   ├── templates/page.tsx
│   │   │   ├── queue/page.tsx
│   │   │   ├── replies/page.tsx
│   │   │   ├── unsubscribes/page.tsx
│   │   │   ├── health/page.tsx
│   │   │   ├── analytics/page.tsx
│   │   │   ├── settings/page.tsx
│   │   │   └── audit-logs/page.tsx
│   │   ├── components/
│   │   │   ├── ui/                 # Button, Card, Table, Modal
│   │   │   ├── layout/             # Sidebar, AuthLayout
│   │   │   ├── campaigns/
│   │   │   ├── accounts/
│   │   │   └── analytics/
│   │   ├── lib/
│   │   │   ├── api.ts              # Fetch wrapper
│   │   │   └── auth.ts
│   │   └── types/
│   │       └── api.ts              # TypeScript interfaces
│   └── __tests__/
│       └── api.test.ts
│
├── .env.example                    # All required env vars with placeholders
├── .gitignore
└── README.md
```

### Key File Contents Summary

| File | Contains |
|------|----------|
| `backend/app/config.py` | `DATABASE_URL`, `REDIS_URL`, `JWT_SECRET`, `GOOGLE_CLIENT_ID`, `TOKEN_ENCRYPTION_KEY`, `USE_MOCK_GMAIL=true` |
| `backend/app/main.py` | FastAPI app, include routers, exception handlers |
| `workers/celery_app.py` | Beat: scheduler every 1m, reply sync 15m, health 1h, token refresh 5m |
| `docker/docker-compose.yml` | Services: db, redis, api, worker, beat, frontend |
| `.env.example` | Document every variable; mark `TODO` for Google credentials |

---

## 12. Security Requirements

| ID | Requirement | Implementation |
|----|-------------|----------------|
| SEC-01 | Encrypted refresh tokens | AES-256-GCM in `crypto.py` |
| SEC-02 | Least privilege OAuth | Only gmail.send + gmail.readonly |
| SEC-03 | CSRF on OAuth | Redis state nonce |
| SEC-04 | Secure JWT | HS256, 1h expiry, httpOnly cookie + Secure flag in prod |
| SEC-05 | Audit logs | Append-only; no tokens in metadata |
| SEC-06 | No Gmail password storage | OAuth only; reject app password fields |
| SEC-07 | RBAC (future) | `role` column on users: admin, operator |
| SEC-08 | Secret rotation | `encryption_key_id` supports multi-key decrypt |
| SEC-09 | Safe error logging | Redact tokens, emails partial: `j***@example.com` |
| SEC-10 | HTTPS only in production | HSTS, Secure cookies |
| SEC-11 | Input validation | Pydantic schemas on all endpoints |
| SEC-12 | SQL injection | SQLAlchemy ORM only |
| SEC-13 | Rate limit API | 100 req/min per user on auth endpoints |

---

## 13. Testing Plan

### 13.1 Unit Tests

| Area | Tests |
|------|-------|
| Auth | Password hash, JWT create/verify, expiry |
| Crypto | Encrypt/decrypt roundtrip, wrong key fails |
| Template | Render variables, unsubscribe required |
| Rate limit | Counter increment, window reset, tier caps |
| Suppression | Unsubscribed blocked, bounced blocked |
| Health | Score calculation, tier promotion/demotion |
| Risk budget | Score accumulation, threshold blocking |
| Bounce parser | Gmail, Workspace, Outlook, soft, malformed fixtures |
| Lead import | Compliance ack required, role-based block, normalized_email |

### 13.2 Integration Tests

| Area | Tests |
|------|-------|
| OAuth callback | Mock Google token endpoint; access_denied handling |
| Account tiers | `test_account_tier_promotion`, `test_restricted_account_cannot_send` |
| Account pools | `test_account_pool_capacity`, `test_pool_active_account_limit` |
| Preflight | `test_preflight_blocks_invalid_campaign` |
| Campaign flow | Create → import → preflight → schedule → jobs |
| Unsubscribe | Public endpoint → suppression |
| Risk budget | `test_global_risk_budget_pauses_new_campaigns` |
| Audit | Actions logged correctly |

### 13.3 Worker Tests

| Worker | Tests |
|--------|-------|
| Sender | `test_sender_requires_account_lock`, mock Gmail, rate limit gate |
| Scheduler | `test_scheduler_lock_prevents_duplicate_jobs`, creates jobs at start |
| Token refresh | `test_token_refresh_lock`, invalid_grant pauses |
| Tier evaluation | `test_account_tier_promotion`, `test_account_tier_demotion_on_quota_error` |
| Reply sync | Matches In-Reply-To |
| Bounce | `test_bounce_parser_gmail_mailer_daemon`, `test_bounce_parser_soft_bounce`, `test_bounce_parser_malformed_message` |
| Import | `test_import_requires_compliance_acknowledgement`, `test_role_based_email_blocked` |

### 13.4 Required Test Cases (Checklist)

- [ ] `test_account_tier_promotion`
- [ ] `test_account_tier_demotion_on_quota_error`
- [ ] `test_restricted_account_cannot_send`
- [ ] `test_account_pool_capacity`
- [ ] `test_pool_active_account_limit`
- [ ] `test_sender_requires_account_lock`
- [ ] `test_scheduler_lock_prevents_duplicate_jobs`
- [ ] `test_token_refresh_lock`
- [ ] `test_preflight_blocks_invalid_campaign`
- [ ] `test_global_risk_budget_pauses_new_campaigns`
- [ ] `test_role_based_email_blocked`
- [ ] `test_import_requires_compliance_acknowledgement`
- [ ] `test_bounce_parser_gmail_mailer_daemon`
- [ ] `test_bounce_parser_soft_bounce`
- [ ] `test_bounce_parser_malformed_message`

### 13.4 Test Infrastructure

```bash
# Run all tests
docker compose -f docker/docker-compose.test.yml up -d
cd backend && pytest -v --cov=app

# Mock Gmail (default in tests)
USE_MOCK_GMAIL=true
```

### 13.5 CI Pipeline (Future)

1. Lint: `ruff`, `mypy`
2. Unit + integration tests with mock Gmail
3. Alembic migration up/down test
4. Frontend: `npm test`, `tsc --noEmit`

---

## 14. Deployment Plan

### 14.1 Local Docker Compose (MVP)

```yaml
# docker/docker-compose.yml services:
services:
  db:        postgres:16-alpine    # port 5432
  redis:     redis:7-alpine        # port 6379
  api:       backend Dockerfile    # port 8000
  worker:    workers Dockerfile    # celery worker
  beat:      workers Dockerfile    # celery beat
  frontend:  frontend Dockerfile   # port 3000
```

**Start:**
```bash
cp .env.example .env
# TODO: Fill GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, TOKEN_ENCRYPTION_KEY, JWT_SECRET
docker compose -f docker/docker-compose.yml up --build
```

### 14.2 Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://...` |
| `REDIS_URL` | Yes | `redis://redis:6379/0` |
| `JWT_SECRET` | Yes | 32+ char random string |
| `TOKEN_ENCRYPTION_KEY` | Yes | 32-byte base64 |
| `GOOGLE_CLIENT_ID` | Yes* | *TODO: Google Console |
| `GOOGLE_CLIENT_SECRET` | Yes* | *TODO: Google Console |
| `GOOGLE_REDIRECT_URI` | Yes | `http://localhost:8000/api/v1/gmail/callback` |
| `FRONTEND_URL` | Yes | `http://localhost:3000` |
| `UNSUBSCRIBE_SECRET` | Yes | JWT signing key |
| `USE_MOCK_GMAIL` | Dev | `true` for local without Google |
| `GLOBAL_DAILY_SEND_LIMIT` | No | Default 200 |
| `GLOBAL_RISK_SCORE_THRESHOLD` | No | Default 100 |
| `DEFAULT_TIER_NEW_DAILY` | No | Default 5 |
| `CELERY_BROKER_URL` | Yes | Same Redis URL |

### 14.3 Production (Later)

| Component | Recommendation |
|-----------|----------------|
| API | AWS ECS Fargate or K8s Deployment (2 replicas) |
| Workers | Separate ECS service; scale on queue depth |
| PostgreSQL | RDS with automated backups (7-day retention) |
| Redis | ElastiCache |
| Frontend | Vercel or S3+CloudFront |
| Secrets | AWS Secrets Manager |
| TLS | ALB + ACM certificate |
| Observability | CloudWatch → Prometheus/Grafana optional |

### 14.4 Backup Strategy

- **PostgreSQL:** Daily automated RDS snapshot; point-in-time recovery
- **Redis:** Ephemeral (cache/queue); rebuilt on restart — no backup needed
- **OAuth tokens:** In DB backup; key rotation documented
- **Audit logs:** Retain 1 year; archive to S3 Glacier

---

## 15. Cursor Implementation Instructions

### Step-by-Step Build Order

> **Rules:** Backend first, frontend second. Account pools before sender. Preflight before send. Risk budget before scale. Mock Gmail until STEP 11. Test after each step.

---

### STEP 0: Repo Scaffold

1. `.gitignore`, `.env.example`, `README.md` stub
2. `docker/docker-compose.yml` — postgres + redis
3. `docs/TECHNICAL_REQUIREMENTS.md`, `docs/COMPLIANCE.md` stub

**Test:** `docker compose up db redis` → healthy

---

### STEP 1: Backend Core Auth

1. `backend/pyproject.toml`, `config.py`, `database.py`
2. User model, JWT auth (register, login, me)
3. `backend/tests/test_auth.py`

**Test:** `pytest backend/tests/test_auth.py -v`

---

### STEP 2: Gmail OAuth Mock + Token Encryption

1. `oauth_tokens`, `gmail_accounts` models (base fields)
2. `token_service.py`, `oauth_service.py`, `crypto.py`
3. `mock_client.py`, `GET/POST /gmail/connect`, callback, revoke
4. OAuth error handling for `access_denied`, app-not-verified

**Test:** `pytest backend/tests/test_oauth.py -v`

---

### STEP 3: Gmail Account Tiers + Health/Risk Models

1. Extend `gmail_accounts`: `account_tier`, tier counters, `risk_level`, `review_required`
2. `account_health_events`, `risk_budget_events` models
3. `evaluate_account_tier()` worker task
4. `POST /gmail/accounts/{id}/review`, `POST /gmail/accounts/{id}/set-tier`

**Test:** `test_account_tier_promotion`, `test_restricted_account_cannot_send`

---

### STEP 4: Account Pools + Membership APIs

1. `gmail_account_pools`, `gmail_account_pool_members` models + migration
2. Pool CRUD + member endpoints (Section 5.3a)
3. Update campaigns: `campaign_account_pool_id` FK

**Test:** `test_account_pool_capacity`, `test_pool_active_account_limit`

---

### STEP 5: Campaigns / Templates / Leads / Import Batches

1. Campaign, template, lead, `lead_import_batches` models
2. Campaign/template CRUD, CSV import with compliance ack
3. Role-based email blocking, `normalized_email` dedup
4. `import_leads`, `validate_lead_email` workers

**Test:** `test_import_requires_compliance_acknowledgement`, `test_role_based_email_blocked`

---

### STEP 6: Campaign Preflight Checks

1. `run_campaign_preflight()` service
2. `POST /campaigns/{id}/preflight-check`
3. Gate `POST /campaigns/{id}/start` on preflight + risk budget

**Test:** `test_preflight_blocks_invalid_campaign`

---

### STEP 7: Redis Locks + Rate Limiter + Sender Worker Mock

1. `rate_limit_service.py` with tier + pool caps
2. Redis locks: `lock:gmail_account`, `lock:campaign_scheduler`, `lock:token_refresh`
3. `send_jobs`, `sent_emails`; scheduler + sender tasks (mock Gmail)
4. Full 20-step send gate checklist

**Test:** `test_sender_requires_account_lock`, `test_scheduler_lock_prevents_duplicate_jobs`, `test_token_refresh_lock`

---

### STEP 8: Reply Sync + Bounce Parser + Unsubscribe

1. Bounce fixtures in `backend/tests/fixtures/`
2. Multi-signal `detect_bounces()` implementation
3. Reply sync, public unsubscribe endpoints
4. Suppression service integration

**Test:** `test_bounce_parser_gmail_mailer_daemon`, `test_bounce_parser_soft_bounce`, `test_bounce_parser_malformed_message`

---

### STEP 9: Risk Budget + Analytics + Audit

1. `record_risk_event()` worker
2. `GET /risk/overview`, `/risk/events`, `POST /risk/acknowledge`
3. Analytics, health monitor, audit log routers

**Test:** `test_global_risk_budget_pauses_new_campaigns`, `test_analytics_funnel`

---

### STEP 10: Frontend Pages

1. Next.js scaffold + auth
2. Pages: accounts (tier badge), account-pools, review queue, risk dashboard
3. Campaign preflight modal, import compliance confirmation, pool capacity chart
4. Remaining pages from Section 9

**Test:** Manual E2E with mock Gmail

---

### STEP 11: Real Gmail API Integration

1. `GoogleGmailClient` in `client.py`
2. `USE_MOCK_GMAIL=false`; Google Console test users
3. Manual: connect → send → reply → bounce

**Test:** `test_real_gmail_send` (manual, skipped CI)

---

### STEP 12: Docker + README + Compliance Docs

1. `Dockerfile.api`, `Dockerfile.worker`, `Dockerfile.frontend`
2. Full `docker-compose.yml`
3. README setup guide, `COMPLIANCE.md`, OAuth verification notes

**Test:** `docker compose up --build` → full mock E2E

---

### Implementation Checklist for Cursor

```
[ ] STEP 0: Repo scaffold
[ ] STEP 1: Backend core auth
[ ] STEP 2: Gmail OAuth mock + token encryption
[ ] STEP 3: Gmail account tiers + health/risk models
[ ] STEP 4: Account pools + membership APIs
[ ] STEP 5: Campaigns/templates/leads/import batches
[ ] STEP 6: Campaign preflight checks
[ ] STEP 7: Redis locks + rate limiter + sender worker mock
[ ] STEP 8: Reply sync + bounce parser + unsubscribe
[ ] STEP 9: Risk budget + analytics + audit
[ ] STEP 10: Frontend pages
[ ] STEP 11: Real Gmail API integration
[ ] STEP 12: Docker + README + compliance docs
```

---

## Appendix A: Sample `.env.example`

```bash
# App
APP_ENV=development
API_HOST=0.0.0.0
API_PORT=8000
FRONTEND_URL=http://localhost:3000

# Database
DATABASE_URL=postgresql+asyncpg://outreach:outreach@localhost:5432/outreach

# Redis
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1

# Auth
JWT_SECRET=CHANGE_ME_32_CHAR_MINIMUM_SECRET_KEY
JWT_EXPIRE_MINUTES=60

# Token encryption
TOKEN_ENCRYPTION_KEY=CHANGE_ME_BASE64_32_BYTES

# Unsubscribe JWT
UNSUBSCRIBE_SECRET=CHANGE_ME_UNSUBSCRIBE_SECRET

# Google OAuth — TODO: https://console.cloud.google.com/
GOOGLE_CLIENT_ID=TODO.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=TODO
GOOGLE_REDIRECT_URI=http://localhost:8000/api/v1/gmail/callback
GOOGLE_OAUTH_PUBLISHING_STATUS=testing
GOOGLE_OAUTH_TEST_USER_LIMIT=100

# Feature flags
USE_MOCK_GMAIL=true

# Rate limits & risk (account tiers: new 5/day default, trusted 30/day default, 75 hard max)
GLOBAL_DAILY_SEND_LIMIT=200
GLOBAL_RISK_SCORE_THRESHOLD=100
DEFAULT_TIER_NEW_DAILY=5
DEFAULT_TIER_NEW_HOURLY=1
DEFAULT_TIER_TRUSTED_DAILY=30
DEFAULT_TIER_TRUSTED_HARD_MAX=75
```

---

## Appendix B: Architecture Decision Records

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Email API | Gmail API (not SMTP) | OAuth security, no app passwords |
| Queue | Celery + Redis | Mature, beat scheduler built-in |
| ORM | SQLAlchemy 2.0 async | FastAPI ecosystem fit |
| Frontend | Next.js App Router | SSR for dashboard, API routes proxy optional |
| Mock-first | `USE_MOCK_GMAIL` flag | Develop without Google credentials |
| Token storage | Encrypted refresh in PG, access in Redis | Security + performance |
| Template engine | Jinja2 | Simple, sandboxable |
| Trust tiers | Metrics-driven ramp | new 5/day → trusted 30/day (75 max) |
| Account pools | Join table membership | Scale 10–500 accounts safely |
| Bounce detection | Multi-signal DSN parser | Subject/label alone unreliable |
| Send concurrency | 3 Redis lock types | account + scheduler + token refresh |
| OAuth scopes (MVP) | send + readonly | Verification required for public scale |
| Global risk budget | Event-scored threshold | Pauses new sends before mass restriction |

---

## Appendix C: Production Readiness Additions (Append-Only)

> **Review date:** 2026-06-10  
> **Reviewer role:** Principal Staff Engineer / Security / Deliverability  
> **Scope:** Additive only — no existing requirement removed or simplified.  
> **Purpose:** Close gaps from ~90% → 100% production readiness.

### C.1 Architecture Additions

| ID | Requirement | Priority |
|----|-------------|----------|
| ARCH-01 | Separate Celery queues: `send`, `sync`, `import`, `health`, `dlq` | P0 |
| ARCH-02 | Idempotent domain events table `domain_events` (outbox pattern) for audit + future bus | P1 |
| ARCH-03 | API `/health/live`, `/health/ready` (DB + Redis + broker checks) | P0 |
| ARCH-04 | Graceful shutdown: workers finish in-flight send + release locks on SIGTERM (30s drain) | P0 |
| ARCH-05 | Circuit breaker per `gmail_account_id` on repeated 403/429 (open 1h) | P0 |
| ARCH-06 | Feature flag service stub (`FEATURE_*` env vars) for kill switches | P1 |

**Service boundary note (future microservice extraction):** Extract `gmail-connector` (OAuth + send + sync) first; keep campaign/lead logic in core API. Outbox table enables later event bus without rewrite.

---

### C.2 Database Additions

#### C.2.1 Immediate Fixes (before coding completes)

| Table / Index | Addition | Reason |
|---------------|----------|--------|
| `send_jobs` | `INDEX(gmail_account_id, status, scheduled_at)` | Sender dequeue at scale |
| `send_jobs` | `INDEX(status, scheduled_at) WHERE status IN ('pending','locked')` partial | Hot path |
| `send_jobs` | Columns: `worker_id`, `lock_token`, `lock_expires_at`, `next_retry_at` | Stuck-job recovery |
| `send_jobs` | Column: `dlq_reason`, `dlq_at` | Dead letter tracking |
| `sent_emails` | `INDEX(sent_at DESC)`, `INDEX(campaign_id, sent_at)` | Analytics |
| `gmail_accounts` | `INDEX(user_id, status, account_tier)` composite | Pool selection |
| `unsubscribe_list` | `INDEX(normalized_email)` if not present via email | Suppression lookup |
| `audit_logs` | `correlation_id UUID`, `INDEX(correlation_id)` | Traceability |
| `oauth_tokens` | `last_used_at`, `compromised_at`, `revoked_at` | Rotation / recovery |
| `campaigns` | `INDEX(campaign_account_pool_id, status)` | Pool queries |

#### C.2.2 New Table: `send_job_dlq`

| Column | Type | Purpose |
|--------|------|---------|
| id | UUID PK | |
| send_job_id | UUID FK UNIQUE | Original job |
| failure_class | VARCHAR(64) | poison, max_retries, gmail_permanent, validation |
| payload | JSONB | Snapshot for manual replay |
| replay_count | INT DEFAULT 0 | |
| created_at | TIMESTAMPTZ | |

#### C.2.3 New Table: `analytics_daily_rollups`

| Column | Type | Purpose |
|--------|------|---------|
| id | UUID PK | |
| user_id | UUID FK | |
| campaign_id | UUID FK NULL | NULL = user-wide |
| pool_id | UUID FK NULL | |
| gmail_account_id | UUID FK NULL | |
| rollup_date | DATE | |
| sent_count | INT | |
| replied_count | INT | |
| bounced_count | INT | |
| unsubscribed_count | INT | |
| failed_count | INT | |

**Indexes:** `UNIQUE(user_id, campaign_id, pool_id, gmail_account_id, rollup_date)`  
**Population:** Nightly Celery task + incremental hourly for today.

#### C.2.4 New Table: `analytics_monthly_rollups`

Same shape as daily; populated from daily rollups on 1st of month.

#### C.2.5 New Table: `gmail_sync_cursors`

| Column | Type | Purpose |
|--------|------|---------|
| gmail_account_id | UUID FK UNIQUE | |
| reply_sync_history_id | VARCHAR(255) NULL | Gmail historyId cursor |
| bounce_sync_after | TIMESTAMPTZ | Last processed bounce window |
| updated_at | TIMESTAMPTZ | |

**Reason:** Reply/bounce workers must not re-scan full inbox every 15 min at 500 accounts.

#### C.2.6 Retention Policies

| Table | Hot Retention | Archive |
|-------|---------------|---------|
| `send_jobs` (terminal) | 90 days | S3 parquet export |
| `account_health_events` | 180 days | aggregate only |
| `audit_logs` | 1 year | S3 Glacier |
| `risk_budget_events` | 2 years | — |
| `bounce_events` | 2 years | — |
| `reply_events` | 1 year | snippet only after 90d |

#### C.2.7 Future Scale (500+ accounts)

- Partition `sent_emails`, `send_jobs` by `created_at` monthly
- Read replica for analytics queries
- Connection pooling: PgBouncer transaction mode

#### C.2.8 1M+ Email Events

- Materialized view `mv_campaign_funnel_daily` refreshed hourly
- Separate analytics DB or TimescaleDB extension for event tables
- Never scan raw `sent_emails` for dashboard; rollups only

---

### C.3 Worker System Additions

| ID | Requirement | Priority |
|----|-------------|----------|
| WRK-01 | Dead letter queue: jobs → `send_job_dlq` after max retries or permanent Gmail errors | P0 |
| WRK-02 | Worker heartbeat: Redis `worker:heartbeat:{hostname}` TTL 60s; alert if missing | P0 |
| WRK-03 | Stuck-job sweeper (beat, every 5 min): `locked` jobs where `lock_expires_at < now()` → `pending` | P0 |
| WRK-04 | Poison job detection: same job fails 3x with same error → DLQ, no retry | P0 |
| WRK-05 | Retry jitter: `retry_after = base * 2^attempt + random(0, 60)` prevents retry storms | P0 |
| WRK-06 | Separate concurrency: `send` queue workers ≤ pool active limits; `sync` queue independent | P0 |
| WRK-07 | Gmail send idempotency: store `client_send_id` UUID on job; reject duplicate send if Gmail already succeeded | P0 |
| WRK-08 | `POST /admin/send-jobs/{id}/replay` (auth) for DLQ manual replay | P1 |

**Race condition mitigations:**

| Scenario | Mitigation |
|----------|------------|
| Lock expires mid-send | Renew lock every 120s via Lua `EXPIRE` if holder matches; max send timeout 8 min |
| Worker crash after Gmail send, before DB commit | Reconcile task: match Gmail sent folder by `rfc_message_id` vs pending jobs |
| Duplicate scheduler run | Scheduler lock + `INSERT ... ON CONFLICT (idempotency_key) DO NOTHING` |
| Token refresh during send | Send acquires refresh lock check; wait or skip account |

---

### C.4 Redis Additions

| ID | Requirement | Implementation |
|----|-------------|----------------|
| REDIS-01 | Lock value format: `{worker_id}:{task_id}:{uuid}` | Ownership validation on release |
| REDIS-02 | Lock renewal Lua script every 120s during active send | Prevents false stale release |
| REDIS-03 | Stale lock detector (beat): `TTL lock:*` + holder heartbeat missing → log + metric | |
| REDIS-04 | Redis outage: **fail closed** for sends; **fail open** for read-only dashboard | Documented degradation |
| REDIS-05 | Separate Redis DB indexes: `/0` broker, `/1` cache+locks, `/2` rate limits | Blast radius reduction |
| REDIS-06 | Rate limit keys include date bucket: `rate:account:{id}:daily:{YYYY-MM-DD}` | Correct TTL at midnight UTC |
| REDIS-07 | Global risk score cache: `risk:user:{id}:score` synced from PG every event | Fast gate check |

**Lock release Lua (required):**

```lua
-- KEYS[1]=lock_key, ARGV[1]=holder_token
if redis.call("GET", KEYS[1]) == ARGV[1] then
  return redis.call("DEL", KEYS[1])
else
  return 0
end
```

---

### C.5 OAuth & Secrets Additions

| ID | Requirement | Priority |
|----|-------------|----------|
| OAUTH-14 | Support multiple `encryption_key_id` values; decrypt with any active key | P0 |
| OAUTH-15 | OAuth client rotation runbook: dual client IDs in env during cutover | P1 |
| OAUTH-16 | `GOOGLE_CLIENT_ID` rotation without disconnecting accounts (same Google project) | P1 |
| OAUTH-17 | Compromised account recovery: revoke all tokens, force re-consent, audit `security.account_compromised` | P0 |
| OAUTH-18 | Refresh token reuse detection: if Google rotates refresh token, atomically replace in DB | P0 |
| OAUTH-19 | Secrets from vault in prod (AWS Secrets Manager); never in env files on disk | P0 |

---

### C.6 Security Additions

| ID | Threat | Mitigation |
|----|--------|------------|
| SEC-14 | Token theft (XSS) | httpOnly + Secure + SameSite=Strict cookies; no localStorage JWT |
| SEC-15 | CSRF on state-changing API | SameSite cookies + CSRF double-submit for cookie auth |
| SEC-16 | XSS in templates | CSP header: `default-src 'self'`; sanitize rendered HTML preview only |
| SEC-17 | SSRF via `source_url` | Block private IP ranges; no server-side fetch of source_url |
| SEC-18 | CSV injection | Prefix cells starting with `=`, `+`, `-`, `@` with `'` on export |
| SEC-19 | Jinja2 SSTI | SandboxedEnvironment; no `{% include %}`, no attr access on non-scalars |
| SEC-20 | Unsubscribe token replay | JWT `jti` stored in Redis SET with 90d TTL; one-time use optional flag |
| SEC-21 | Unsubscribe enumeration | Constant-time response; rate limit 30/min per IP on `/unsubscribe/*` |
| SEC-22 | Privilege escalation | All endpoints verify `resource.user_id == current_user.id` |
| SEC-23 | Webhook abuse (future) | HMAC signature + timestamp + replay window |

**Required middleware (add to §3.2):** `RequestIdMiddleware`, `SecurityHeadersMiddleware`, `RateLimitMiddleware`, `AuditHookMiddleware`.

---

### C.7 Observability Additions

| ID | Requirement | Priority |
|----|-------------|----------|
| OBS-01 | Structured JSON logging: `timestamp`, `level`, `correlation_id`, `user_id`, `account_id`, `job_id` | P0 |
| OBS-02 | Propagate `X-Request-ID` from API → Celery task headers → worker logs | P0 |
| OBS-03 | OpenTelemetry trace stub (optional MVP): FastAPI + Celery instrumentation hooks | P1 |
| OBS-04 | Audit categories enum: `auth`, `oauth`, `send`, `campaign`, `risk`, `admin`, `security` | P0 |

#### Required Metrics (Prometheus / CloudWatch)

| Metric | Type | Labels |
|--------|------|--------|
| `send_jobs_total` | counter | status, campaign_id |
| `gmail_api_requests_total` | counter | account_id, method, http_code |
| `gmail_api_latency_seconds` | histogram | method |
| `account_tier_gauge` | gauge | account_id, tier |
| `pool_capacity_remaining` | gauge | pool_id |
| `global_risk_score` | gauge | user_id |
| `redis_lock_acquire_total` | counter | lock_type, result |
| `dlq_jobs_total` | counter | failure_class |
| `bounce_rate_24h` | gauge | account_id |

#### Required Alerts

| Alert | Condition | Severity |
|-------|-----------|----------|
| Send queue depth | pending > 10k for 15m | warning |
| DLQ spike | >50 jobs/hour | critical |
| Global risk threshold | score > threshold | critical |
| Worker heartbeat missing | any worker > 2 min | critical |
| Gmail 403 rate | >5 per account/hour | warning |
| Redis unavailable | ready check fails | critical |
| OAuth refresh failures | >3 accounts in 10m | critical |

#### Required Dashboards

1. **Operations:** queue depth, send rate, error rate, worker health, Redis memory
2. **Deliverability:** bounce/reply/unsub by pool and tier
3. **Risk:** global score timeline, restricted accounts, review queue size
4. **Gmail API:** quota errors, latency p95, per-account send volume

---

### C.8 Reliability & DR Additions

| ID | Requirement | Value |
|----|-------------|-------|
| REL-01 | RTO (full platform restore) | 4 hours |
| REL-02 | RPO (PostgreSQL) | 15 minutes (PITR) |
| REL-03 | RPO (Redis queue) | Accept job loss; jobs re-materializable from campaigns |
| REL-04 | Degraded mode: Redis down | Pause sends; allow reads + unsubscribe |
| REL-05 | Degraded mode: Gmail API down | Queue jobs; exponential backoff globally |
| REL-06 | Degraded mode: single account auth_error | Isolate account; continue pool |

**Recovery procedures (document in `docs/RUNBOOK.md`):**

1. Stuck send_jobs → run stuck-job sweeper manually
2. Mass 403 → pause all campaigns, acknowledge risk, tier demote
3. Token encryption key rotation → dual-key decrypt, re-encrypt batch job
4. Duplicate sends suspected → reconcile by `rfc_message_id`
5. DB restore → stop workers, restore PG, verify migrations, replay DLQ cautiously

**Backup:** RDS automated backups 7d + cross-region snapshot weekly. Test restore monthly.

---

### C.9 Analytics Additions

| ID | Requirement | Priority |
|----|-------------|----------|
| ANLY-01 | Dashboard queries MUST read from `analytics_daily_rollups` only | P0 |
| ANLY-02 | Hourly incremental rollup job for current day | P0 |
| ANLY-03 | Pool-level rollup columns in daily table | P0 |
| ANLY-04 | Account health dashboard reads latest snapshot + rollup, not raw events | P0 |
| ANLY-05 | Risk analytics: 7d/30d trend from `risk_budget_events` aggregated nightly | P1 |

---

### C.10 Account Pool Additions

| ID | Requirement | Priority |
|----|-------------|----------|
| POOL-06 | Pool-level circuit breaker: pause pool if >3 accounts restricted in 24h | P0 |
| POOL-07 | Pool send budget preflight: projected campaign volume vs pool remaining capacity | P0 |
| POOL-08 | Track `pool_sends_today` denormalized counter in Redis, synced hourly to PG | P0 |
| POOL-09 | Account cannot belong to overlapping active pools without explicit flag | P1 |

---

### C.11 Account Health Model Additions

| ID | Requirement | Priority |
|----|-------------|----------|
| HLTH-09 | Health score decay: -1/day without send activity (prevents stale 100 score) | P1 |
| HLTH-10 | Separate `operational_status` from `account_tier` (tier=capacity, status=auth/pause) | P0 |
| HLTH-11 | Store raw metric inputs in health snapshot JSON for audit replay | P0 |
| HLTH-12 | Gmail API error budget per account: max 10 API errors/hour before skip | P0 |

---

### C.12 Future-Proofing (Migration Paths Only — Not MVP)

| Module | Migration Path |
|--------|----------------|
| Feature flags | Env → `feature_flags` table → LaunchDarkly |
| Event bus | `domain_events` outbox → SQS/SNS → Kafka |
| Queue | Celery+Redis → SQS (sender) + Redis (locks/cache) |
| CRM | Webhook outbound on `lead.replied` event; plugin interface |
| Multi-tenant | Add `workspace_id` to all tables; RLS policies |

---

### C.13 Production Readiness Scorecard

| Dimension | Score | Gap to 10/10 |
|-----------|-------|--------------|
| Architecture | 8.5/10 | Outbox, queue separation, circuit breakers (C.1) |
| Security | 8/10 | CSP, unsubscribe replay, SSRF/CSV mitigations (C.6) |
| Scalability | 8/10 | Rollups, sync cursors, partial indexes (C.2) |
| Reliability | 7.5/10 | DLQ, stuck-job sweeper, reconcile task (C.3) |
| Maintainability | 8.5/10 | Runbooks, correlation IDs, feature flags |
| Operational Readiness | 7/10 | Metrics, alerts, dashboards (C.7) |
| **Production Readiness** | **8.5/10 → 10/10 after Appendix C** | Implement C.1–C.11 P0 items |

---

### C.14 Missing Changes Before Coding (Priority Order)

1. Add `send_jobs` lock/retry/DLQ columns + indexes (C.2.1)
2. Implement Redis lock renewal + ownership Lua (C.4)
3. Add DLQ table + stuck-job sweeper spec (C.3)
4. Add `gmail_sync_cursors` for reply/bounce (C.2.5)
5. Add correlation ID middleware (C.7)
6. Add analytics rollup tables (C.2.3)
7. Separate Celery queues (C.1 ARCH-01)
8. Document degraded modes in RUNBOOK (C.8)
9. Add health/live/ready endpoints (C.1 ARCH-03)
10. Add send idempotency / reconcile spec (C.3 WRK-07)

---

### C.15 Missing Changes Before Production (Priority Order)

1. Prometheus metrics + critical alerts (C.7)
2. RDS PITR + tested restore procedure (C.8)
3. Secrets Manager integration (C.5 OAUTH-19)
4. OAuth app verification complete for account count (§8.9)
5. CSP + security headers middleware (C.6)
6. Monthly backup restore drill (C.8)
7. DLQ replay admin tooling (C.3 WRK-08)
8. Cross-region snapshot (C.8)
9. OpenTelemetry tracing (C.7 OBS-03)
10. Partition strategy documented for 500+ accounts (C.2.7)

---

### C.16 Safe To Build Now?

**YES** — with Appendix C P0 items incorporated into STEP 0–7 alongside existing requirements.

**Cursor implementation order (unchanged from §15, with Appendix C embedded):**

1. STEP 0: Scaffold + RUNBOOK.md stub + health endpoints
2. STEP 1: Auth + correlation ID middleware
3. STEP 2: OAuth mock + token encryption + dual-key support stub
4. STEP 3: Account tiers + health + sync cursors table
5. STEP 4: Account pools + pool Redis counters
6. STEP 5: Campaigns/leads/import + analytics rollup tables (empty)
7. STEP 6: Preflight + DLQ schema
8. STEP 7: Redis locks (with renewal) + separate queues + sender mock + stuck-job sweeper
9. STEP 8: Reply/bounce + reconcile task
10. STEP 9: Risk budget + rollup jobs + metrics stubs
11. STEP 10: Frontend
12. STEP 11: Real Gmail
13. STEP 12: Docker + compliance + observability dashboards

---

*End of Technical Requirements Document*
