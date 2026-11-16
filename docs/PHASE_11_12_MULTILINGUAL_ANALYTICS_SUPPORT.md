# Phase 11 & Phase 12 Architecture & Implementation Guide
## AI FAQ College Chatbot SaaS Platform

**Phases Implemented:**
- **Phase 11: Voice, Multilingual Support and Chat History**
- **Phase 12: Analytics and Support System**

---

## 1. Executive Architecture Summary

This combined phase implements two mission-critical pillars for the institutional AI College Chatbot:
1. **Student Inclusivity & Experience (Phase 11):** Voice Input (Speech-to-Text), Voice Output (Text-to-Speech), localized multi-language interaction in English, Hindi, and Gujarati with acronym and proper noun protection (`ACPC`, `GUJCET`, `FRC`, `MYSY`, `B.Tech`, etc.), persistent tenant-isolated conversation history, and conversation context continuity during RAG answer generation.
2. **Institutional Telemetry & Governance (Phase 12):** Production-grade multi-tenant analytics engine (query volume, satisfaction rates, token telemetry, latency profiles, recurring FAQ tracking, zero-grounding knowledge gap discovery) and a complete threaded student support ticket system with staff-only internal notes and in-app notifications.

---

## 2. Phase 11: Voice, Multilingual Support & Chat History

### 2.1 Multilingual Configuration (`backend/app/services/multilingual_config.py`)
- **Supported Languages:**
  - `en` (English - default)
  - `hi` (हिन्दी - Hindi)
  - `gu` (ગુજરાતી - Gujarati)
- **Protected Technical Entities & Acronyms:**
  Specific academic bodies, examinations, and official quotas are guaranteed preservation without inappropriate transliteration:
  `["ACPC", "GUJCET", "FRC", "MYSY", "AICTE", "NAAC", "GTU", "NBA", "NIRF", "TFW", "TFWS", "SC", "ST", "SEBC", "EWS", "B.Tech", "M.Tech", "Diploma", "B.E.", "M.E.", "BCA", "MCA"]`.
- **System Prompts & Strict Language Adherence:**
  Dynamic prompts instruct LLMs to generate answers solely in the requested language while maintaining verbatim proper nouns, contact emails, and currency values.
- **Localized Tier-5 Fallback Messages:**
  When zero reliable evidence exists, answers default to the exact institutional no-evidence phrase in the user's chosen language:
  - English: *"I could not find reliable information in the official college documents regarding this query. Please consult the official college admissions helpdesk."*
  - Hindi: *"अधिकृत कॉलेज दस्तावेजों में इस विषय पर कोई विश्वसनीय जानकारी नहीं मिली। कृपया कॉलेज के आधिकारिक प्रवेश सहायता केंद्र से संपर्क करें।"*
  - Gujarati: *"સત્તાવાર કોલેજ દસ્તાવેજોમાં આ પૂછપરછ અંગે કોઈ વિશ્વસનીય માહિતી મળી નથી. કૃપા કરીને કોલેજના પ્રવેશ હેલ્પડેસ્કનો સંપર્ક કરો."*

### 2.2 Voice Input (Speech-to-Text)
- Utilizes browser-native Web Speech API (`webkitSpeechRecognition` / `SpeechRecognition`) with explicit user initiation.
- Dynamically configures recognition language code (`en-US`, `hi-IN`, `gu-IN`).
- Provides active pulsating recording visual indicator and clear microphone permission denial notifications.
- **Editable Transcript Review:** Transcribed text populates the chat input textarea before submission, allowing the student to inspect, edit, or append to the query before sending.

### 2.3 Voice Output (Text-to-Speech)
- Powered by `window.speechSynthesis` with matching language codes.
- Implemented with play, pause, and stop controls, plus an active audio playback indicator (`VolumeX` animated wave).
- Automatically sanitizes markdown formatting (bullet points, asterisks, URLs, headings) prior to vocalization to ensure smooth audio delivery.
- **Zero Auto-Play:** Audio will never automatically play without explicit user interaction.

### 2.4 Multi-Turn Conversation Context in RAG
- The RAG engine (`rag_service.py`) dynamically extracts the recent conversation turns (up to 4 turns, max 1,500 tokens) associated with the `session_id`.
- Dialogue context is injected into the model prompt under `Recent Conversation Context:`, enabling follow-up questions such as *"What about hostel fees for the same branch?"* or *"How do I apply for that?"*.

### 2.5 User Language Preferences Sync
- New endpoints `GET /api/v1/users/preferences` and `PUT /api/v1/users/preferences`.
- Automatically persists the student's chosen language into `users.preferred_language` and `users.preferences` JSONB.

---

## 3. Phase 12: Analytics & Support System

### 3.1 Live Database Analytics Engine (`analytics_service.py`)
All statistics are computed directly from database tables (`chat_sessions`, `chat_messages`, `feedback`, `knowledge_chunks`, `support_tickets`, `ai_provider_events`). No fake numbers are used.

- **Endpoints:**
  - `GET /api/v1/analytics/platform`: Platform-level metrics across all colleges for Super Admins.
  - `GET /api/v1/analytics/college`: Institutional metrics scoped to the administrator's college.
  - `GET /api/v1/analytics/questions`: Frequently asked questions with percentages and ask counts.
  - `GET /api/v1/analytics/unanswered-questions`: Zero-evidence and low-confidence student inquiries identifying institutional knowledge gaps.
  - `GET /api/v1/analytics/ai-usage`: Token telemetry, prompt/completion split, provider breakdown, failure rates, and estimated costs.
- **Date Filtering:**
  Supports `TODAY`, `7D`, `30D`, `90D`, and custom timestamp filtering.

### 3.2 Support Ticket Lifecycle & Threaded Replies (`support_service.py`)
- **Statuses:** `OPEN`, `IN_PROGRESS`, `WAITING_FOR_USER`, `RESOLVED`, `CLOSED`.
- **Categories:** `LOGIN`, `CHATBOT`, `INCORRECT_ANSWER`, `MISSING_INFO`, `DOCUMENT`, `TECHNICAL`, `OTHER`.
- **Priorities:** `LOW`, `MEDIUM`, `HIGH`, `URGENT`.
- **Threaded Conversation Replies:**
  - Database entity `support_ticket_replies` supports multi-turn staff-student dialogue.
  - **Internal Admin Staff Notes (`is_internal=True`):**
    College and Super Admins can write internal coordination notes on tickets.
    **Security Enforcement:** When a student accesses `GET /support/tickets/{id}`, `support_service.py` strictly redacts any reply where `is_internal == True`.

### 3.3 In-App Notifications (`in_app_notification_service.py`)
- Table `in_app_notifications` with user and college scoping.
- Tracks `is_read`, notification categories (`CRAWL`, `INGESTION`, `TICKET`, `SYSTEM`), and deep links.
- Endpoints:
  - `GET /api/v1/notifications`
  - `PATCH /api/v1/notifications/{id}/read`
  - `POST /api/v1/notifications/read-all`

---

## 4. Database Migrations

### Migration `016_analytics_support_and_multilingual.sql`
- Adds `WAITING_FOR_USER` to `support_ticket_status` enum.
- Enhances `support_tickets` with `category`, `priority`, `assigned_to_user_id`, `resolution_notes`, and `updated_at`.
- Creates `support_ticket_replies` table.
- Creates `in_app_notifications` table.
- Adds `preferred_language` and `preferences` JSONB to `users` table.
- Adds `category` and `session_id` to `feedback` table.
- Adds composite tenant isolation indexes.

---

## 5. Verification & Testing

Run the automated verification suite:
```bash
node scripts/test_phase11_phase12.js
```
All 32 programmatic test assertions pass verifying database migrations, multilingual rules, RAG context continuity, voice sanitization, tenant isolation, internal staff note redaction, and frontend connectivity.

