# SPEAKEZ AI - Complete Project Documentation

## 1. Project Overview
SPEAKEZ AI is a full-stack, realtime communication coaching platform focused on student presentation and interview preparation.

The application combines:
- realtime speech capture and transcription
- speech quality analytics (pace, fillers, continuity)
- webcam-derived non-verbal analytics (eye contact, posture, emotion proxy)
- interview simulation with rubric-style scoring
- session persistence and report export

The backend supports dual persistence modes:
- SQLite for lightweight/local operation
- MongoDB for richer session/event storage and inspection in MongoDB Compass

## 2. Goals and Use Cases
Primary goals:
- Help users improve spoken communication in practice and interview contexts.
- Provide immediate, actionable coaching while speaking.
- Persist sessions for review, trend tracking, and PDF reporting.

Main use cases:
- Live practice speaking sessions
- Interview preparation with timed response flow
- Session replay/review with transcript and metric timeline
- Progress tracking across multiple sessions

## 3. Tech Stack

### 3.1 Frontend
Core:
- React 18
- Vite 5
- TypeScript
- React Router

UI and interaction:
- Tailwind CSS
- Framer Motion
- Recharts
- Lucide React icons
- Radix UI primitives (dependencies included)

Realtime/browser capabilities:
- WebSocket client for bidirectional low-latency updates
- Web Audio API + ScriptProcessorNode for microphone capture and chunking
- MediaPipe Tasks Vision in browser for face and pose analysis

### 3.2 Backend
Framework and APIs:
- FastAPI
- Uvicorn (ASGI server)
- REST + WebSocket endpoints

Data and settings:
- Pydantic v2
- pydantic-settings
- SQLModel (SQLite path)
- PyMongo (MongoDB path)

AI/ML/audio stack:
- faster-whisper (STT)
- webrtcvad-wheels (voice activity detection)
- NumPy, SciPy
- Librosa (voice variation proxy)
- OpenCV + MediaPipe (dependencies for multimodal pipeline)
- scikit-learn + joblib (optional confidence model)

Reporting:
- ReportLab for PDF report generation

## 4. High-Level Architecture

### 4.1 Frontend architecture
- App shell provides navigation and theme toggle.
- Route-driven pages for Landing, Dashboard, Interview, Analytics, and Session Report.
- Dashboard and Interview open a WebSocket to the backend and stream audio/video-derived payloads.
- Analytics and report pages consume REST endpoints.

### 4.2 Backend architecture
- FastAPI app composes CORS middleware + REST router + WebSocket router.
- Realtime session engine (LiveSession) maintains in-memory session state while active.
- Audio pipeline produces transcription and speech metrics.
- Optional confidence model refines heuristic confidence scores.
- Repository layer abstracts persistence (SQLite/MongoDB) under common functions.

### 4.3 Data flow summary
1. Frontend starts session via WebSocket session_start.
2. Mic chunks are sent as base64 PCM16 chunks.
3. Backend performs incremental transcription and metric updates.
4. Frontend receives transcript_partial and realtime_metrics.
5. On session_stop, backend finalizes and persists transcript + summary.
6. REST APIs expose session list/details/metrics/events and PDF export.

## 5. Implemented Features

### 5.1 Landing and navigation
- Product overview and CTA actions to start session, interview simulator, and analytics.
- Reusable app shell with sticky header and dark/light mode toggle.

### 5.2 Live coaching dashboard
- WebSocket connection management.
- Start/stop microphone capture.
- Optional camera start/stop for visual signals.
- Live transcript rendering with filler-word highlighting.
- Realtime metrics cards:
  - WPM with speed label
  - filler count and filler density
  - continuity proxy
  - confidence score + label
  - visual metrics: eye contact, posture, emotion, voice variation
- Realtime trend charts for WPM and confidence.
- Smart suggestions + personalized insights list.

### 5.3 Interview simulator
- Loads predefined interview questions from backend.
- Timed answer flow (default 3 minutes).
- Reuses realtime speech pipeline during answer recording.
- session_stop triggers interview scoring endpoint.
- Displays content score and overall score.

### 5.4 Progress analytics
- Fetches and lists recent sessions.
- Provides links to per-session report page.

### 5.5 Session report page
- Fetches full session details.
- Displays transcript.
- Charts session timeline (WPM and confidence).
- Exposes PDF export action.

### 5.6 PDF export
- Backend-generated PDF includes:
  - session metadata
  - latest summary metrics
  - transcript excerpt

### 5.7 Persistence and storage
- SQLite mode:
  - sessions table
  - metric_points table
- MongoDB mode:
  - sessions collection with full lifecycle and events
  - metric_points collection for timeline
  - counters collection for numeric IDs

### 5.8 Session event tracking (MongoDB mode)
Session event array captures key activity such as:
- session_start
- audio_chunk metadata
- transcript_partial payload snapshots
- realtime_metrics payload snapshots
- video_landmarks payload snapshots
- session_stop and finalize events

This enables richer debugging/audit trails in MongoDB Compass.

## 6. Realtime Metrics and Scoring Logic

### 6.1 Speech metrics
Derived from transcript and audio continuity:
- WPM = words per minute over elapsed duration
- Fillers total and breakdown (um, uh, like, you know, actually, basically, so)
- Filler density = fillers / word count
- Continuity = voiced frame ratio from VAD

### 6.2 Suggestions engine
Rule-based suggestions include:
- reduce fillers when density is high
- increase pace if too slow
- slow down if too fast
- improve sentence continuity when continuity is low

### 6.3 Insight engine
Trend-based heuristics include:
- pace acceleration after 2 minutes
- dominant filler feedback
- sustained low pace suggestions

### 6.4 Confidence estimation
Two-stage approach:
1. Heuristic confidence from pace/fillers/continuity penalties
2. Optional ML override if confidence model exists at backend/models/confidence_model.joblib

### 6.5 Voice variation
- Computed from relative pitch variation using librosa.yin.
- Normalized to a 0..1 expressiveness proxy.

### 6.6 Interview scoring
- Content score based on:
  - answer length
  - structural connectors
  - specificity (numeric mentions)
- Overall score:
  - weighted blend of content and confidence

## 7. API and Protocol Documentation

### 7.1 REST endpoints
- GET /health
  - basic service health check

- GET /api/sessions
  - returns recent session headers (id, timestamps, language, mode)

- GET /api/sessions/{session_id}
  - returns full session details:
    - transcript
    - summary
    - metrics timeline
    - events (when available in MongoDB mode)

- GET /api/interview/questions
  - returns static question bank

- POST /api/interview/score
  - body: answer, confidence
  - returns content and overall score

- GET /api/sessions/{session_id}/report.pdf
  - streams generated PDF report

### 7.2 WebSocket endpoint
- WS /ws/session

Incoming message types:
- session_start
- session_stop
- audio_chunk
- video_landmarks
- video_frame

Outgoing message types:
- ack
- realtime_metrics
- transcript_partial
- transcript_final (defined type, not currently emitted in main flow)
- session_saved
- error

Typical message flow:
1. Client sends session_start.
2. Server responds ack.
3. Client streams audio_chunk and optional video_landmarks.
4. Server emits transcript_partial and realtime_metrics repeatedly.
5. Client sends session_stop.
6. Server emits session_saved.

## 8. Database Documentation

### 8.1 SQLite schema
Session fields:
- id
- started_at
- ended_at
- language
- mode
- transcript
- summary_json

MetricPoint fields:
- id
- session_id
- t_ms
- wpm
- fillers_total
- fillers_density
- confidence
- emotion
- eye_contact
- posture
- voice_variation

### 8.2 MongoDB collections
sessions document (key fields):
- id (numeric)
- started_at, ended_at
- language, mode
- transcript
- summary (object)
- events (array of lifecycle and telemetry events)

metric_points document:
- session_id
- t_ms
- metric values matching realtime payload
- created_at

counters document:
- _id (sequence name)
- value (auto-increment counter)

Indexes created in Mongo mode:
- sessions.id (unique)
- sessions.started_at
- metric_points(session_id, t_ms)

## 9. Environment Configuration

Backend environment variables:
- CORS_ALLOW_ORIGINS equivalent via settings.cors_allow_origins
- STORAGE_BACKEND: sqlite | mongodb
- DATABASE_URL: SQLite URL
- MONGODB_URI: Mongo connection string
- MONGODB_DATABASE: target Mongo database
- SPEAKEZ_STT_PROVIDER: local | openai
- OPENAI_API_KEY: required only when openai provider is used
- WHISPER_MODEL: tiny|base|small|medium|large-v3
- WHISPER_DEVICE: auto|cpu|cuda

Current defaults prioritize local execution.

## 10. Setup and Run Instructions

### 10.1 Prerequisites
- Windows PowerShell
- Python 3.12 recommended for dependency compatibility
- Node.js + npm
- Optional: MongoDB Community Server + MongoDB Compass

### 10.2 Backend setup
From repository root:
1. cd backend
2. py -3.12 -m venv .venv
3. .\.venv\Scripts\Activate.ps1
4. pip install -r requirements.txt
5. python -m uvicorn app.main:app --reload --port 8000

### 10.3 Frontend setup
From repository root in a second terminal:
1. cd frontend
2. npm install
3. npm run dev

Frontend URL:
- http://localhost:5173

Backend URL:
- http://localhost:8000

### 10.4 MongoDB mode setup
1. Start local MongoDB server.
2. In backend/.env set:
   - STORAGE_BACKEND=mongodb
   - MONGODB_URI=mongodb://localhost:27017
   - MONGODB_DATABASE=speakez
3. Start backend normally.
4. Open MongoDB Compass and connect to mongodb://localhost:27017.
5. Inspect database speakez collections.

## 11. Frontend Routes
- /
- /dashboard
- /interview
- /analytics
- /report/:sessionId

## 12. Repository Structure Summary
Top-level folders:
- backend: API, realtime processing, persistence, scoring
- frontend: UI and realtime client
- training: notebooks, datasets, templates for model experimentation

Notable backend modules:
- app/main.py: app creation and router wiring
- app/ws.py: WebSocket protocol handling
- app/realtime/session.py: realtime session engine
- app/pipelines/audio.py: STT + speech metrics logic
- app/db_repo.py: storage abstraction (SQLite/MongoDB)
- app/api.py: REST endpoints and report generation

Notable frontend modules:
- src/pages/Dashboard.tsx: main realtime coaching page
- src/pages/Interview.tsx: timed interview simulation
- src/pages/ProgressAnalytics.tsx: session history view
- src/pages/SessionReport.tsx: report and export view
- src/lib/audioCapture.ts: microphone chunking pipeline
- src/lib/vision.ts: browser-side MediaPipe metrics

## 13. Current Behavior Notes and Constraints
- WebSocket endpoint URL is currently hardcoded in frontend to ws://localhost:8000/ws/session.
- REST base URLs are hardcoded to http://localhost:8000 in frontend pages.
- transcript_final message type exists in schema but primary flow emits transcript_partial and session_saved.
- Interview mode sets mode=interview at session_start.
- Dashboard session_start payload currently does not explicitly set mode and defaults to practice.

## 14. Testing and Validation Notes
Validated during integration:
- backend startup in MongoDB mode
- repository write/read cycle for sessions, metrics, events
- health and sessions API responses
- report PDF endpoint rendering

## 15. Future Enhancement Opportunities
- Centralize API base URL via environment-based frontend config
- Add authentication and multi-user support
- Add transcript_final emission and stronger end-of-session summaries
- Expand interview rubric with semantic/LLM-driven assessment
- Add automated tests for websocket and persistence flows
- Add deployment-ready Docker setup

---
This document reflects the implemented code paths currently present in the repository and the active runtime behavior of the project.