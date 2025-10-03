# app/main.py
from fastapi import FastAPI
from app.utils.db import engine, Base
from app.routers import auth, sessions, threads, messages

app = FastAPI(title="Agent Chat API")

# Create tables on startup (dev). In production use Alembic
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)

# include routers
app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(threads.router)
app.include_router(messages.router)
