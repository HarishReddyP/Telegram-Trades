import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import dashboard, trades, alerts, settings as settings_routes, reset
from app.db.init_db import init_db
from fastapi.staticfiles import StaticFiles
from pathlib import Path

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Telegram Trade Alert System",
    version="1.0.0",
    description="Reads options alerts from Telegram, parses, risk-checks, "
                "paper-trades, tracks P&L, and reports.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(trades.router)
app.include_router(alerts.router)
app.include_router(settings_routes.router)
app.include_router(reset.router)

# Serve built frontend (if present) under /ui
static_dir = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if static_dir.exists():
    app.mount("/ui", StaticFiles(directory=str(static_dir), html=True), name="ui")
    logging.info("Serving frontend from %s at /ui", static_dir)


@app.on_event("startup")
def _startup():
    try:
        init_db()
    except Exception as e:  # noqa: BLE001
        logging.warning("init_db skipped/failed at startup: %s", e)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/")
def root():
    payload = {"service": "telegram-trade-system", "docs": "/docs"}
    if static_dir.exists():
        payload["dashboard"] = "/ui"
    return payload
