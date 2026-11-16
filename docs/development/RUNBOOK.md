# Local Development Runbook

Step-by-step instructions for running the backend and frontend applications locally.

---

## 1. Prerequisites
- **Node.js**: v18+ or v24+ (Node `v24.18.0` detected).
- **Python**: 3.11+ or 3.12+ (Download from python.org with "Add to PATH" checked).
- **Redis**: Local or Docker (or free cloud Upstash Redis).
- **Supabase PostgreSQL**: With `pgvector` enabled.

---

## 2. Environment Configuration
1. Copy `.env.example` in `backend/` to `.env`:
   ```powershell
   Copy-Item backend\.env.example backend\.env
   ```
2. Configure your Supabase Database URI and Gemini API Key in `backend\.env`.

---

## 3. Starting the Backend API
```powershell
# Navigate to backend directory
cd backend

# Install Python requirements
pip install -r requirements.txt

# Start FastAPI development server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
API Documentation will be live at: `http://localhost:8000/docs`

---

## 4. Starting the User Frontend
Open a new PowerShell terminal:
```powershell
cd apps\user-frontend
npm install
npm run dev
```
User application will be live at: `http://localhost:3000`

---

## 5. Starting the Admin Frontend
Open a new PowerShell terminal:
```powershell
cd apps\admin-frontend
npm install
npm run dev -- -p 3001
```
Admin Portal will be live at: `http://localhost:3001`

