import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from dotenv import load_dotenv

load_dotenv()

from config import get_settings
from database import init_db
from routers import tickets, messages, analytics, solutions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

settings = get_settings()

limiter = Limiter(key_func=get_remote_address)
app = FastAPI(title="TechAssist IT Helpdesk API", version="1.0.0")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS
origins = [o.strip() for o in settings.cors_allowed_origins.split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static file serving for uploaded screenshots
upload_path = Path(settings.upload_dir)
upload_path.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_path)), name="uploads")

# Routers
app.include_router(tickets.router,   prefix="/api/v1")
app.include_router(messages.router,  prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(solutions.router, prefix="/api/v1")


@app.on_event("startup")
def on_startup() -> None:
    init_db()
    logger.info("TechAssist API is ready.")


@app.get("/api/v1/health")
def health():
    return {"status": "ok", "version": "1.0.0"}
