# SPEAKEZ AI – Real-Time Communication Coach for Students

Full-stack AI coaching app that analyzes speech + webcam signals in real time to help students improve presentations and interview skills.

## Full Documentation
- See PROJECT_DOCUMENTATION.md for complete technical and feature documentation.

## Tech
- **Frontend**: React + Vite + Tailwind + shadcn/ui + Framer Motion + Recharts
- **Backend**: FastAPI + WebSockets + SQLModel (SQLite)
- **AI**: faster-whisper (local STT), MediaPipe (landmarks), OpenCV, Librosa

## Quickstart (Windows)

### 1) Backend
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2) Frontend
```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Interview simulator
- Open `http://localhost:5173/interview`
- Click **Start** and answer the displayed question within the timer.
- Click **Stop** to generate a rubric score (content + overall).

## Environment
Backend env vars (optional):
- `SPEAKEZ_STT_PROVIDER=local|openai` (default `local`)
- `OPENAI_API_KEY=...` (only if using `openai`)
 - Optional trainable confidence model: place a `joblib` model at `backend/models/confidence_model.joblib`

MongoDB backend (optional):
- `STORAGE_BACKEND=sqlite|mongodb` (default `sqlite`)
- `MONGODB_URI=mongodb://localhost:27017`
- `MONGODB_DATABASE=speakez`

### MongoDB Compass + full session persistence
1. Start MongoDB locally (default URI `mongodb://localhost:27017`).
2. Open MongoDB Compass and connect to `mongodb://localhost:27017`.
3. In `backend/.env`, set:
	- `STORAGE_BACKEND=mongodb`
	- `MONGODB_URI=mongodb://localhost:27017`
	- `MONGODB_DATABASE=speakez`
4. Restart backend:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

Stored collections:
- `sessions` (session lifecycle, transcript, summary, events)
- `metric_points` (realtime metrics timeline)
- `counters` (auto-increment numeric session IDs)

## Notes
- This repo includes **training notebooks + dataset templates** in `training/` to demonstrate fine-tuning/validation beyond pretrained models.

