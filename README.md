# AIT AI ASSISTANT (Ahmedabad Institute of Technology)

Official, dedicated, production-quality AI Assistant designed specifically for **Ahmedabad Institute of Technology (AIT)** ([https://www.aitindia.in](https://www.aitindia.in)).

---

## 🏛️ Institutional Knowledge Authority

Unlike generic chatbots or hallucinating LLMs, **AIT AI Assistant** treats Ahmedabad Institute of Technology as its primary institutional knowledge authority following strict hierarchical routing:
1. **Official AIT Website (`aitindia.in`)**
2. **Verified AIT Structured Database**
3. **Verified AIT Institutional RAG Documents**
4. **General AI Model Fallback (General educational & programming questions only)**

> **Anti-Hallucination Guarantee**: If an institutional fact (fees, faculty, admissions, dates) cannot be verified from authentic AIT records, the system responds with:
> *"I couldn't verify that information from the available official AIT sources."*

---

## 🌟 Core Features

- **P0 Real Verified AIT Image Retrieval**: Direct, in-chat presentation of verified campus, library, computer lab, classroom, and sports photos originating from `https://www.aitindia.in`. No AI-generated fake college imagery.
- **Multilingual Intelligence Layer**: Native comprehension of **English**, **Gujarati**, **Hindi**, **Gujlish** (e.g., *"BCA ni fees ketli che?"*), and **Hinglish** (e.g., *"DBMS kaun padhata hai?"*).
- **Coreference & Conversational Memory**: Resolves implicit pronouns across message turns (e.g., *"Who teaches DBMS?"* $\rightarrow$ *"Prof. Anjali Sharma."* $\rightarrow$ *"Where is her office?"* $\rightarrow$ *"Prof. Anjali Sharma's office: Block B, Room 204"*).
- **ChatGPT-Style UX**: Modern responsive SPA with dark navy (`#0b0a3e`) & accent amber (`#f08518`) branding, conversation grouping (Today, Previous 7 Days, Older), pin/archive/delete/rename, copy, and feedback.
- **Typed Server-Sent Events (SSE) Streaming**: Low-latency typed streaming delivering text deltas, image cards, citations, and provenance tags in real-time.
- **Strict User File Permission Isolation**: Uploaded documents (PDF, DOCX, XLSX, TXT, MD, images) are private by default and strictly isolated to the user's authenticated session.
- **Voice Recognition (STT) & Speech**: Web Speech API audio recording with accent tolerance and vocal playback.
- **Enterprise Security**: Input sanitization, prompt injection defense, MIME magic header verification, size quotas, and bcrypt/JWT authentication.

---

## 🚀 Quickstart Guide

### 1. Backend Setup (FastAPI)
Ensure Python 3.10+ is installed:
```bash
# Navigate to project root
cd "c:\Users\HP\OneDrive\Desktop\college chatbot"

# Install dependencies (if not already installed)
pip install -r backend/requirements.txt

# Run the FastAPI server
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend starts at `http://127.0.0.1:8000`.
- Swagger API Docs: `http://127.0.0.1:8000/docs`
- Health Check: `http://127.0.0.1:8000/health`

### 2. Frontend Setup (React + Vite)
In a separate terminal:
```bash
cd apps/user-web
npm install
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 🧪 Automated Testing
Run the automated test suite covering all 11 core verification scenarios:
```bash
python -m pytest backend/tests -v
```

---

## 🐳 Docker Deployment
To launch the complete production stack (PostgreSQL + pgvector, Redis, FastAPI Backend, and Nginx User Web):
```bash
docker-compose up --build
```
