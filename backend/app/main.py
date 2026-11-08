"""Run:  uvicorn app.main:app --reload   (from the backend folder). API docs at /docs."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from . import config, models  # noqa: F401  (registers the tables)
from .db import Base, engine
from .routers import admin, applications, auth, jobs


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    yield


app = FastAPI(title="HireMind Intelligence Platform API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5500", "http://127.0.0.1:5500"],
                   allow_methods=["*"], allow_headers=["*"])
for r in (auth.router, jobs.router, applications.router, admin.router):
    app.include_router(r)


@app.get("/api/health")
def health():
    return {"status": "ok"}


if config.FRONTEND_DIR.exists():
    app.mount("/", StaticFiles(directory=config.FRONTEND_DIR, html=True), name="frontend")
