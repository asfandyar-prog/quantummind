from fastapi import FastAPI
# FastAPI is the web framework. You create one app instance
# and attach all your routes to it.

from fastapi.middleware.cors import CORSMiddleware
# CORS = Cross-Origin Resource Sharing.
# Browsers block requests between different origins by default.
# Your frontend runs on localhost:5173
# Your backend runs on localhost:8000
# These are different origins → browser blocks the request.
# CORSMiddleware tells the browser: "yes, this origin is allowed."

from contextlib import asynccontextmanager
# Used to run code on startup and shutdown.
# We use it to print a confirmation message when the server starts.

from app.core.config import settings
# Our config file from the previous step.
# settings.frontend_url → used for CORS
# settings.app_env → used to show debug info in development


# ── Lifespan ──────────────────────────────────────────────────
# This runs ONCE when the server starts, and ONCE when it stops.
# Think of it like a constructor/destructor for your entire app.
# In the future we'll initialize ChromaDB and load models here.
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Everything BEFORE yield runs on startup
    print("\n🚀 QuantumMind backend starting...")
    print(f"   Environment : {settings.app_env}")
    print(f"   Model       : {settings.groq_model}")
    print(f"   Frontend URL: {settings.frontend_url}")
    print(f"   Docs        : http://localhost:8000/docs\n")

    yield
    # Everything AFTER yield runs on shutdown
    print("\n👋 QuantumMind backend shutting down...")


# ── App instance ──────────────────────────────────────────────
# This is the single FastAPI instance for the entire backend.
# Every route, middleware, and plugin attaches to this object.
app = FastAPI(
    title="QuantumMind API",
    description="AI-powered quantum computing learning backend",
    version="0.1.0",
    # lifespan wires up our startup/shutdown logic above
    lifespan=lifespan,
    # Only show interactive docs in development.
    # In production we disable them so they're not publicly visible.
    docs_url="/docs" if settings.app_env == "development" else None,
    redoc_url=None,
)


# ── CORS Middleware ───────────────────────────────────────────
# This must be added BEFORE any routes.
# Order of middleware registration matters in FastAPI.
app.add_middleware(
    CORSMiddleware,
    # allow_origins: which frontend URLs can call this backend.
    # We read this from .env so it works in both dev and production.
    allow_origins=[settings.frontend_url],
    # allow_credentials: lets the browser send cookies and auth headers.
    allow_credentials=True,
    # allow_methods: which HTTP methods are permitted.
    # ["*"] means GET, POST, PUT, DELETE, OPTIONS — everything.
    allow_methods=["*"],
    # allow_headers: which request headers the frontend can send.
    allow_headers=["*"],
)


# ── Health check ──────────────────────────────────────────────
# This is the first real route. It does one thing: confirm the
# server is alive. Used by Railway/Vercel to check deployment health.
# Also useful for you to test that the server started correctly.
@app.get("/health")
async def health():
    # async def means this function is non-blocking.
    # FastAPI is built on asyncio — always use async def for routes.
    # This lets the server handle thousands of requests concurrently
    # without waiting for each one to finish before starting the next.
    return {
        "status": "ok",
        "environment": settings.app_env,
        "model": settings.groq_model,
    }


# ── Root ──────────────────────────────────────────────────────
@app.get("/")
async def root():
    return {
        "name": "QuantumMind API",
        "version": "0.1.0",
        "docs": "/docs",
    }


# ── Routers (added as we build them) ─────────────────────────
# When we build the chat and stream routes, we'll register them here:
#
# from app.routes.chat import router as chat_router
# from app.routes.stream import router as stream_router
# app.include_router(chat_router,   prefix="/api")
# app.include_router(stream_router, prefix="/api")
#
# prefix="/api" means all routes in chat.py become /api/chat, /api/stream etc.
# This is a REST API best practice — namespacing your routes.


# ── Register routers ──────────────────────────────────────────
from app.routes.chat import router as chat_router
from app.routes.stream import router as stream_router

app.include_router(chat_router,   prefix="/api")
app.include_router(stream_router, prefix="/api")