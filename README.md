# CodexArena Monorepo

CodexArena is a real-time technical interview platform with:

- Recruiter room management and live candidate monitoring
- Candidate coding interview flow with Monaco + Yjs collaboration
- Secure multi-language code execution pipeline
- AI question generation and AI code evaluation
- Browser-side anti-cheat signals + replay timeline support

---

## Project Structure

- `backend/` - FastAPI services, workers, schemas, execution engine, WebSocket hub
- `frontend/` - React + TypeScript + Vite UI
- `infra/` - infrastructure scaffolding (docker/k8s-related assets)

---

## Implemented So Far

### Backend

- Auth + JWT:
  - `POST /auth/register`
  - `POST /auth/login`
  - `POST /auth/refresh`
- Room + candidate flow:
  - `POST /rooms`
  - `GET /rooms`
  - `GET /rooms/{room_id}`
  - `DELETE /rooms/{room_id}`
  - `POST /rooms/{room_id}/join`
  - `GET /rooms/resolve/{join_token}`
- Questioning:
  - `POST /questions/generate`
  - `GET /questions/{question_id}`
- Execution:
  - `POST /execute`
  - `GET /execute/{job_id}`
- Real-time:
  - `WS /ws/{room_id}` with JWT auth and room access checks
  - events include `code.delta`, `cursor.update`, `cheat.event`, `execution.result`, `ai.evaluation`
- AI services:
  - AI question generator (`Gemini` + schema validation + sandbox validation)
  - AI code evaluator with rubric scoring
- Security/execution:
  - Docker container pool with timeouts and isolation-oriented flags
  - 5-language runners (`python`, `javascript`, `java`, `cpp`, `go`)
- Replay groundwork:
  - 30s snapshot capture in Redis
  - snapshot archive on room close (MinIO/S3 best-effort with local fallback)
  - `GET /attempts/{attempt_id}/snapshots`

### Frontend

- App routing:
  - `/` landing
  - `/login` recruiter login
  - `/dashboard` recruiter dashboard (protected)
  - `/join/:token` candidate join page
  - `/waiting/:room_id` waiting room
  - `/interview/:room_id` candidate interview
  - `/report/:attempt_id` evaluation report (protected)
- Candidate experience:
  - question panel (markdown, examples, hints, timer)
  - Monaco editor + Yjs sync
  - run + test results
  - anti-cheat client monitors:
    - large paste
    - tab switch
    - copy detection
    - keystroke anomaly
    - idle timeout
    - face absence / multi-face (MediaPipe FaceMesh)
- Recruiter experience:
  - room list + room controls
  - candidate cards + live view
  - cheat alert panel
  - evaluation report:
    - score doughnut
    - Big-O display
    - AI feedback/suggestions
    - test summary
    - replay tab with timeline scrubber + diff

---

## Local Run

### 1) Backend

Use Python 3.12 (important for dependency alignment):

```powershell
cd D:\codexarena\backend
py -3.12 -m pip install -r requirements.txt
py -3.12 -m uvicorn app.main:app --reload
```

Backend default URL: `http://127.0.0.1:8000`

Quick checks:

- `GET /health`
- `GET /`

### 2) Frontend

```powershell
cd D:\codexarena\frontend
npm install
npm run dev
```

Frontend default URL: `http://localhost:5173`

---

## Current Notes

- Some endpoints/pages still use fallback rendering if optional backend report APIs are unavailable.
- Snapshot archive writes to MinIO/S3 when configured; otherwise it falls back to local JSON archive files.
- This repository has substantial Phase 1/2 and partial Phase 3 implementation; full production hardening (Phase 4 items) is still pending.

