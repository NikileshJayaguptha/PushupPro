from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from . import database
from .analysis import ISSUE_LABELS, ISSUE_TIPS
from .config import get_settings
from .routers import progress, sessions
from .services.processing import recover_interrupted_jobs

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")


@asynccontextmanager
async def lifespan(app: FastAPI):
    database.init_db()
    recover_interrupted_jobs()
    yield


app = FastAPI(
    title="PushupPro API",
    version="1.0.0",
    description="Push-up rep counting and form analysis from workout videos.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().cors_origin_list,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Range", "Accept-Ranges", "Content-Length"],
)
app.include_router(sessions.router)
app.include_router(progress.router)


@app.get("/api/health", tags=["meta"])
def health():
    with database.engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return {"status": "ok"}


@app.get("/api/meta", tags=["meta"])
def meta():
    from .analysis import DEFAULT_CONFIG

    c = DEFAULT_CONFIG
    return {
        "issue_labels": ISSUE_LABELS,
        "issue_tips": ISSUE_TIPS,
        "thresholds": {
            "depth_target": c.depth_target_deg,
            "depth_flag": c.depth_flag_deg,
            "lockout_flag": c.lockout_flag_deg,
            "sag_flag": c.sag_flag_deg,
            "pike_flag": c.pike_flag_deg,
        },
    }
