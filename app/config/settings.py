import os
from datetime import timedelta

import google.generativeai as genai
from dotenv import load_dotenv
from fastapi import FastAPI, Request
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import storage
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.model.model import Base


def init_settings(app: FastAPI):
    load_dotenv(override=False)
    init_db(app)
    init_gcp(app)
    init_genai(app)


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


def init_gcp(app: FastAPI):
    bucket_name = os.getenv("GCS_BUCKET")
    if not bucket_name:
        raise RuntimeError("GCS_BUCKET not set. Add it to your .env")

    creds_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS_COURSIFY")
    if creds_path and not os.path.isfile(creds_path):
        raise RuntimeError(f"GOOGLE_APPLICATION_CREDENTIALS_COURSIFY points to a missing file: {creds_path}")

    try:
        storage_client = storage.Client.from_service_account_json(creds_path)
    except DefaultCredentialsError as e:
        raise RuntimeError(
            "No GCP credentials found. Set GOOGLE_APPLICATION_CREDENTIALS_COURSIFY or run where ADC is available."
        ) from e

    bucket = storage_client.lookup_bucket(bucket_name)
    if bucket is None:
        raise RuntimeError(f"GCS bucket '{bucket_name}' does not exist or is not accessible with current creds.")

    app.state.gcs_client = storage_client
    app.state.gcs_bucket = bucket

    def upload_bytes_to_gcs(blob_path: str, data: bytes, content_type: str | None = None) -> str:
        blob = bucket.blob(blob_path)
        blob.upload_from_string(data, content_type=content_type)
        return f"gs://{bucket_name}/{blob_path}"

    def signed_url_for(blob_path: str, ttl_seconds: int | None = None, method: str = "GET") -> str:
        name = blob_path.lstrip("/")
        blob = bucket.blob(name)

        if not ttl_seconds:
            ttl_seconds = int(os.getenv("GCS_SIGNED_URL_TTL", "3600"))

        return blob.generate_signed_url(
            version="v4",
            method=method,
            expiration=timedelta(seconds=ttl_seconds),
        )

    app.state.upload_bytes_to_gcs = upload_bytes_to_gcs
    app.state.signed_url_for = signed_url_for


def init_genai(app: FastAPI):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set. Add it to your .env")

    genai.configure(api_key=api_key)

    model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash-lite")
    app.state.genai_model = genai.GenerativeModel(model_name)


def get_genai(request: Request):
    model = getattr(request.app.state, "genai_model", None)
    if model is None:
        raise RuntimeError("Gemini is not initialized. Did you call init_genai(app) in init_settings?")
    return model
