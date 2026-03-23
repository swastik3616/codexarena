# CodexArena Monorepo (Backend + Frontend)

CodexArena is a live coding interview prototype with real-time monitoring:

- The **backend** is a FastAPI app that manages “rooms” in memory and broadcasts candidate updates via WebSockets.
- The **frontend** is a React + Vite app with routes for recruiters (monitor rooms) and candidates (join an editor session). Candidates push editor changes over WebSockets and recruiters see them live.

---

## Project Structure

- `backend/`: FastAPI app (JWT/auth stubs, routers, `/health`)
- `frontend/`: React + Vite UI
- `infra/`: Docker Compose for local dependencies (redis, supabase-local, minio)
- (older prototype folders removed)

---

## Backend (FastAPI)

### What it exposes

- `GET /`
  - Returns `{ "message": "CodexArena Backend Running" }`

- `WebSocket /ws/room/{room_id}?candidate_name=...`
  - When a candidate connects, the server:
    - Accepts the connection
    - Generates a `candidate_id`
    - Broadcasts `candidate_joined` to everyone connected in that room
  - Then it continuously receives JSON messages from that candidate and rebroadcasts them to the whole room.
  - On disconnect, it broadcasts `candidate_left`.

### In-memory behavior

Room state is stored in-memory only (no database). If the backend restarts, all rooms/candidates are reset.

### WebSocket message contract (current behavior)

Candidate -> Backend (messages sent by the candidate editor):

```json
{
  "type": "code_update",
  "code": "<editor contents>",
  "timestamp": "2026-03-23T12:34:56.789Z"
}
```

Possible other message types sent by the frontend today:

```json
{ "type": "run_code", "status": "running", "timestamp": "..." }
```
```json
{ "type": "submit", "code": "<current code>", "timestamp": "..." }
```

Backend -> Everyone in the room (rebroadcasted wrapper):

```json
{
  "type": "<same as incoming type>",
  "candidate_id": "<server generated id>",
  "payload": {
    "...original message fields..."
  }
}
```

Server-generated join/leave broadcasts:

```json
{ "type": "candidate_joined", "candidate_id": "<id>", "candidate_name": "<name>" }
```
```json
{ "type": "candidate_left", "candidate_id": "<id>", "candidate_name": "<name>" }
```

### How to run (backend)

```powershell
cd D:\codexarena\backend

# Install deps + start server (verification)
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend is expected to be reachable by the frontend at `ws://localhost:8000/...`.

---

## Frontend (React + Vite)

### What it provides

Routes (configured in `src/App.tsx`):

- `/` -> `DashboardPage` (overview placeholder UI)
- `/rooms` -> `RoomsPage` (room list + “create room” UI)
- `/rooms/:roomId` -> `RoomDetailPage` (recruiter live monitoring UI)
- `/join/:roomId` -> `JoinPage` (candidate invitation page)
- `/editor` -> `EditorPage` (candidate editor + WebSocket connection)

### Real-time flow (candidate <-> recruiter)

1. Recruiter opens: `/rooms/:roomId`
2. Candidate opens: `/join/:roomId`
3. `JoinPage` currently **redirects** to `/editor?room=<roomId>&candidate=<name>`
4. `EditorPage` connects to:
   `ws://localhost:8000/ws/room/<roomId>?candidate_name=<candidateName>`
5. As the candidate types, `EditorPage` sends `code_update` messages (with `{ code, timestamp }`)
6. `RoomDetailPage` listens for:
   - `candidate_joined` / `candidate_left`
   - `code_update` and displays `data.payload.code` per `candidate_id`

### How to run (frontend)

```powershell
cd D:\codexarena\frontend
npm install
npm run dev
```

Then open the URL Vite prints (default is typically `http://localhost:5173/`).

### Notes / current limitations

- The “proctored environment / monitoring” copy in `JoinPage` is currently UI-only (no camera/tab-switch logic in this code).
- Backend currently rebroadcasts any incoming message type, but the recruiter UI only uses `code_update` to update displayed code.
- `RoomDetailPage` shares an invite link with a **hardcoded** frontend port (`http://localhost:5174/join/{roomId}`). If your Vite dev server is on a different port, update that string in the frontend code.

---

## Running the full app locally

1. Start the backend (port `8000`) using the instructions in the backend section.
2. Start the frontend (Vite dev server).
3. Recruiter: open `/rooms/:roomId`
4. Candidate: open `/join/:roomId` (or use the invite link shown on the room page)

