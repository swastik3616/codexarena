from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import analytics, auth, attempts, candidates, execute, questions, rooms
from app.api.routes import websocket as websocket_routes
from app.core.config import settings


app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(rooms.router)
app.include_router(candidates.router)
app.include_router(questions.router)
app.include_router(execute.router)
app.include_router(attempts.router)
app.include_router(analytics.router)
app.include_router(websocket_routes.router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": "1.0.0"}


@app.get("/")
def read_root() -> dict[str, str]:
    return {"message": "CodexArena Backend Running"}

