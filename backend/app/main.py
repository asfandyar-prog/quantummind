from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.core.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    from app.core.memory import init_checkpointer
    await init_checkpointer()
    print("\n🚀 QuantumMind backend starting...")
    print(f"   Environment : {settings.app_env}")
    print(f"   Model       : {settings.groq_model}")
    print(f"   Frontend URL: {settings.frontend_url}")
    print(f"   Docs        : http://localhost:8000/docs\n")
    yield
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
    return {"status": "ok", "environment": settings.app_env, "model": settings.groq_model}


@app.get("/")
async def root():
    return {"name": "QuantumMind API", "version": "0.1.0", "docs": "/docs"}


from app.routes.chat import router as chat_router
from app.routes.stream import router as stream_router
from app.routes.upload import router as upload_router
from app.routes.execute import router as execute_router
from app.routes.lesson import router as lesson_router

app.include_router(chat_router,   prefix="/api")
app.include_router(stream_router, prefix="/api")
app.include_router(upload_router, prefix="/api")
app.include_router(execute_router, prefix="/api")
app.include_router(lesson_router,  prefix="/api")