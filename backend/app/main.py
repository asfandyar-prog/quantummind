import sys
import asyncio

# psycopg 3's async driver cannot run on Windows' default ProactorEventLoop; it
# needs a SelectorEventLoop. Set the policy before any event loop is created
# (Windows dev only — Linux/prod use epoll and are unaffected).
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlalchemy import text
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.memory import init_checkpointer, close_checkpointer
    await init_checkpointer()

    # Warm the async Postgres pool and fail fast if the DB is unreachable.
    from app.db.database import get_engine, dispose_engine
    async with get_engine().connect() as conn:
        await conn.execute(text("SELECT 1"))
    print("[DB] Postgres async pool ready")

    # Warm the shared Redis active-exam store and fail fast if unreachable.
    from app.db.redis_client import get_redis, close_redis
    await get_redis().ping()
    print("[Redis] active-exam store ready")

    # Concurrency limiter is a stateless, self-healing Redis sorted-set — no init
    # needed; it shares the pool above. Log the active limit for visibility.
    print(f"[LLM] concurrency limit = {settings.llm_max_concurrency} "
          f"(acquire timeout {settings.llm_acquire_timeout_seconds}s)")

    # Backfill worker: grades/advances any answers persisted while the LLM was
    # down. Started after DB+Redis are up; stopped first on shutdown.
    from app.core import grading_backfill
    grading_backfill.start()
    print("[Backfill] grading worker started")

    print("\n🚀 QuantumMind backend starting...")
    print(f"   Environment : {settings.app_env}")
    print(f"   Model       : {settings.llm_model}")
    print(f"   Frontend URL: {settings.frontend_url}")
    print(f"   Docs        : http://localhost:8000/docs\n")
    yield
    await grading_backfill.stop()
    await close_redis()
    await dispose_engine()
    await close_checkpointer()
    print("\n👋 QuantumMind backend shutting down...")


app = FastAPI(
    title="QuantumMind API",
    description="AI-powered quantum computing learning backend",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health():
    return {"status": "ok", "environment": settings.app_env, "model": settings.llm_model}


@app.get("/")
async def root():
    return {"name": "QuantumMind API", "version": "0.1.0", "docs": "/docs"}


from app.routes.chat import router as chat_router
from app.routes.stream import router as stream_router
from app.routes.upload import router as upload_router
from app.routes.execute import router as execute_router
from app.routes.lesson import router as lesson_router
from app.routes.exam import router as exam_router

app.include_router(chat_router,   prefix="/api")
app.include_router(stream_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(execute_router, prefix="/api")
app.include_router(lesson_router,  prefix="/api")
app.include_router(exam_router,    prefix="/api")