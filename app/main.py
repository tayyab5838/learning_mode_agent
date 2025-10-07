# app/main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
# from app.utils.db import engine, Base
from app.routers import auth, sessions, threads, messages
from app.utils.db import init_db, close_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events"""
    # Startup
    print("🚀 Starting up...")
    await init_db()
    print("✅ Database initialized")
    yield
    # Shutdown
    print("🛑 Shutting down...")
    await close_db()
    print("✅ Database connections closed")


app = FastAPI(
    title="Learning Mode Agent API",
    description="API for Learning Mode Agent",
    version="1.0.0",
    lifespan=lifespan
)

# include routers
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(threads.router)
app.include_router(messages.router)
