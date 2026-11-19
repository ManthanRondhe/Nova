# AutoMech-AI (Nova AI)

**Voice-Powered Intelligent Garage & Diagnostics Management System**

AutoMech-AI (Nova AI) combines machine learning fault diagnosis, hands-free voice assistance, workforce scheduling, parts inventory auto-ordering, customer self-service tracking, and unbiased company diagnostic approvals.

---

## Architecture Overview

```
                   ┌──────────────────────────────────────────────┐
                   │               User Portals                   │
                   │  1. Technician Assistant (/assistant)        │
                   │  2. Customer Tracking (/customer)            │
                   │  3. Admin Dashboard (/admin)                 │
                   └──────────────────────┬───────────────────────┘
                                          │
                                          ▼
                   ┌──────────────────────────────────────────────┐
                   │             FastAPI Backend Layer            │
                   │                                              │
                   │  • ML Diagnosis Engine (Tfidf + NB/RF)       │
                   │  • Voice Engine (Speech-to-Text & Jargon)    │
                   │  • Mechanic Scheduler & Bay Allocator        │
                   │  • Inventory Manager & Auto-Restock          │
                   │  • Video Guide Service (Feature 1)           │
                   │  • Unbiased Approval Workflow (Feature 2)    │
                   │  • Telegram Bot Handler (Inline Reviews)     │
                   └──────────────────────┬───────────────────────┘
                                          │
                   ┌──────────────────────┴───────────────────────┐
                   │                                              │
                   ▼                                              ▼
    ┌─────────────────────────────┐               ┌─────────────────────────────┐
    │     Database Adapter        │               │   Telegram Bot & External   │
    │  • MongoDB Atlas            │               │  • Reviewer Callbacks       │
    │  • CSV / JSON File Fallback │               │  • Mechanic Notifications   │
    │  • Video Cache (7-day TTL)  │               │  • Dealer Restock Orders    │
    └─────────────────────────────┘               └─────────────────────────────┘
```

---

## Feature 1: Step-by-Step Repair Video Guides

When a diagnosis is performed, AutoMech-AI decomposes the diagnosed fault into an ordered list of 4–6 real-world chronological repair stages:
1. **Diagnosis & Safety Preparation** (e.g. testing with multimeter, disconnect battery, lift safety stands)
2. **Access & Disassembly** (e.g. unbolt brackets, remove serpentine belt, disconnect harnesses)
3. **Component Removal & Bench Inspection** (e.g. compare new and old components, check mating surfaces)
4. **Replacement & Installation** (e.g. hand thread bolts, torque to specification)
5. **Reassembly & Fluids** (e.g. reinstall harnesses, check fluid levels)
6. **Testing After Install & Post-Repair Validation** (e.g. clear DTCs, road test verification)

### YouTube Data API Integration & Graceful Fallback
- **Targeted Video Search**: Queries YouTube Data API v3 using `Vehicle Make + Vehicle Model + Fault + Stage Details`.
- **Ranking & Shorts Filtering**: Filters out YouTube Shorts (< 60s) and ranks videos by engagement and optimal repair tutorial duration (3–20 minutes).
- **Persistent Caching**: Caches video responses in MongoDB or `data/video_cache.json` with a configurable TTL (`VIDEO_CACHE_TTL_DAYS=7`) to conserve API quota.
- **Graceful Fallback**: If the YouTube API key is missing or quota is exhausted, each stage cleanly falls back to a curated direct YouTube Search link (`https://www.youtube.com/results?search_query=...`). The diagnosis response **never crashes**.
- **Voice Response**: Voice stays brief: *"I found videos for each repair step, check the screen."*
- **UI**: Displayed as a collapsible *"Repair Guide"* timeline under the diagnosis in `assistant.html`.

---

## Feature 2: Company-Side Approval Workflow (Unbiased Diagnostics)

To guarantee 100% fair, unbiased diagnostic recommendations without shop inflation or mechanic guesswork, diagnostics are audited by independent company members before any job is authorized or assigned.

### State Machine Lifecycle

```
[ DIAGNOSIS_CREATED ]
         │
         ▼
[ PENDING_COMPANY_REVIEW ] ──(Company Reviewer Rejects)──▶ [ COMPANY_REJECTED ]
         │
  (Company Reviewer Approves)
         │
         ▼
[ COMPANY_APPROVED ]
         │
         ▼
[ PENDING_CUSTOMER_APPROVAL ] ──(Customer Declines)───────▶ [ CUSTOMER_DECLINED ]
         │
  (Customer Approves)
         │
         ▼
[ CUSTOMER_APPROVED ]
         │
         ▼
(Auto-assign Mechanic ➔ Allocate Bay ➔ Notify Mechanic via Telegram ➔ Auto-order Missing Parts)
```

### Security & Integrity
- **Reviewer Whitelist**: Only Telegram chat IDs specified in `COMPANY_REVIEWER_CHAT_IDS` are authorized to review and approve/reject diagnostics.
- **HMAC Signed Tokens**: Inline buttons use signed HMAC-SHA256 tokens (`review_token`) to prevent replay or spoofing attacks.
- **Idempotency**: Repeated button taps return current status gracefully without duplicate side-effects.
- **Customer Authentication**: Customer approval endpoints authenticate using the vehicle registration number or owner phone number, preventing unauthorized actions.
- **Separation of Concerns**: Assistant guidance is clearly separated from official job creation. Official jobs only dispatch to mechanics after both approvals.

---

## Configuration & Feature Flags (`.env`)

```ini
# Application
APP_NAME="Nova AI"
VERSION="1.0.0"

# Telegram Bot
TELEGRAM_BOT_TOKEN="your_bot_token_from_botfather"
TELEGRAM_ADMIN_CHAT_ID="your_admin_chat_id"

# Feature Flags
ENABLE_VIDEO_GUIDES=true
ENABLE_APPROVAL_WORKFLOW=true

# Feature 1: Video Guides
YOUTUBE_API_KEY="your_youtube_data_api_v3_key"
VIDEO_CACHE_TTL_DAYS=7

# Feature 2: Company Reviewers
COMPANY_REVIEWER_CHAT_IDS="123456789,987654321"
APPROVAL_EXPIRY_HOURS=48
APPROVAL_HMAC_SECRET="your_secret_key"
```

---

## API Endpoints Documentation

### 1. Diagnosis with Video Guides
- **Endpoint**: `POST /api/diagnose`
- **Request**:
```json
{
  "query": "starter motor clicking noise but engine won't turn over",
  "vehicle_type": "Car",
  "vehicle_model": "Honda Civic"
}
```
- **Response**:
```json
{
  "query": "starter motor clicking noise but engine won't turn over",
  "detected_system": "Electrical",
  "detected_severity": "Critical",
  "results": [
    {
      "fault_name": "Starter Motor Solenoid Failure",
      "confidence": 0.95,
      "severity": "Critical",
      "obd_code": "P0615",
      "estimated_time_hours": 2.0,
      "estimated_cost_range": "3500-6000",
      "required_parts": "P-001"
    }
  ],
  "top_estimate": { ... },
  "video_guide": {
    "fault_name": "Starter Motor Solenoid Failure",
    "vehicle": "Car Honda Civic",
    "total_stages": 6,
    "stages": [
      {
        "stage_number": 1,
        "stage_title": "Diagnosing & Voltage Drop Testing",
        "description": "Test battery voltage, starter relay, and starter solenoid with a multimeter before removal.",
        "fallback_search_url": "https://www.youtube.com/results?search_query=Car+Honda+Civic+...",
        "is_fallback": false,
        "videos": [
          {
            "video_id": "abc123xyz",
            "title": "How to Test a Starter Motor Without Removing It",
            "channel_title": "Auto Repair Masters",
            "duration": "10:45",
            "thumbnail": "https://i.ytimg.com/vi/abc123xyz/mqdefault.jpg",
            "watch_url": "https://www.youtube.com/watch?v=abc123xyz"
          }
        ]
      }
    ]
  }
}
```

### 2. Standalone Video Guides
- **Endpoint**: `GET /api/diagnosis/{diagnosis_id}/videos`
- **Endpoint**: `GET /api/videos/guide?fault_name=Starter+Motor+Failure&vehicle_make=Honda&vehicle_model=Civic`

### 3. Company Reviewer Action
- **Endpoint**: `POST /api/approval/review`
- **Request**:
```json
{
  "jobcard_id": "JC-0001",
  "action": "approve",
  "reviewer_id": "123456789",
  "token": "a1b2c3d4e5f6g7h8",
  "note": "Verified by Company Master Inspector"
}
```
- **Response**:
```json
{
  "success": true,
  "message": "Company diagnosis approved. Published to Customer Portal.",
  "jobcard": { ... }
}
```

### 4. Customer Approval Action
- **Endpoint**: `POST /api/customer/approval`
- **Request**:
```json
{
  "jobcard_id": "JC-0001",
  "decision": "approve",
  "customer_identifier": "MH-01-AB-1234"
}
```
- **Response**:
```json
{
  "success": true,
  "message": "Service approved! Assigned to Rajesh Kumar.",
  "jobcard": {
    "jobcard_id": "JC-0001",
    "approval_status": "CUSTOMER_APPROVED",
    "status": "In Progress",
    "assigned_mechanic_name": "Rajesh Kumar"
  }
}
```

### 5. Telegram Webhook Callback
- **Endpoint**: `POST /api/telegram/webhook`
- Handles reviewer callback query updates (`REV:APP:JC-0001:token`, `REV:REJ:JC-0001:token`, `REV:INF:JC-0001:token`).

---

## Running Automated Tests

Run the test suite directly with Python unittest:
```bash
python -m unittest tests/test_features.py -v
```
All 13 test cases cover:
- State Machine valid and invalid transitions
- Telegram reviewer whitelisting & token tamper prevention
- Approval idempotency
- Chronological stage ordering & duration parsing
- Graceful video fallback without API key
- End-to-end happy path flow
- Feature flags ON and OFF regression testing
