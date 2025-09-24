import os

from fastapi import FastAPI, Request
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.model.model import Base


def init_settings(app: FastAPI):
    init_db(app)


def init_db(app: FastAPI):
    db_url = os.getenv("DATABASE_URL", "sqlite:///./app.db")
    connect_args = {"check_same_thread": False} if db_url.startswith("sqlite") else {}
    engine = create_engine(db_url, future=True, echo=False, connect_args=connect_args)
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    app.state.DATABASE_URL = db_url
    app.state.engine = engine
    app.state.SessionLocal = SessionLocal

    Base.metadata.create_all(bind=engine)


def get_db(request: Request):
    db = request.app.state.SessionLocal()
    try:
        yield db
    finally:
        db.close()
