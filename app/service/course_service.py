import datetime
import os
from pathlib import Path
from typing import Optional, Iterable
from urllib.parse import urlparse

from fastapi import HTTPException
from sqlalchemy.orm import Session
from starlette import status

from app.model import model as models
from app.model.model import Course
from app.schema import schema as schemas
from app.util.security import hash_certificate, verify_certificate


def _format_duration(seconds: Optional[int]) -> Optional[str]:
    if seconds is None:
        return None
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    if h and m and not s:
        return f"{h}h {m}m"
    if h and not m and not s:
        return f"{h}h"
    if m and not s and not h:
        return f"{m}m"
    return f"{seconds}s"


def _to_detail(course: models.Course, user_id: int) -> schemas.CourseDetailResponse:
    tags = [t.tag for t in (course.tags or [])] or None

    progress_val = 0
    is_downloaded_val = False
    if course.progress_items:
        user_progress = next((p for p in course.progress_items if p.user_id == user_id), None)
        if user_progress:
            progress_val = user_progress.progress
            is_downloaded_val = bool(user_progress.is_downloaded)

    return schemas.CourseDetailResponse(
        id=course.id,
        title=course.title,
        description=course.description,
        duration=_format_duration(course.duration_seconds),
        format=course.format,
        course_type=course.course_type,
        learning_goals=course.learning_goals,
        rating=round(course.rating_avg or 0.0, 2),
        is_downloaded=is_downloaded_val,
        progress=progress_val,
        title_image=course.title_image,
        thumbnail_url=course.thumbnail_url,
        download_url=course.download_url,
        tags=tags,
        requires_certificate=bool(course.requires_certificate),
    )


def _set_tags(course: models.Course, tags: Optional[Iterable[str]]):
    if tags is None:
        return
    clean = [t.strip() for t in tags if t and t.strip()]
    course.tags = [models.CourseTag(tag=t) for t in dict.fromkeys(clean)]


# --------- services ---------

def create_course(payload: schemas.CourseCreate, db: Session) -> models.Course:
    data = payload.model_dump()

    if data.get("id") is not None:
        existing = db.get(models.Course, data["id"])
        if existing:
            raise HTTPException(status_code=400, detail="ID de curso ya existe")

    course = models.Course(
        id=data.get("id"),
        title=data["title"],
        description=data.get("description"),
        duration_seconds=data.get("duration_seconds"),
        format=data.get("format") or "video",
        course_type=data.get("course_type") or "self_paced",
        learning_goals=data.get("learning_goals"),
        rating_avg=data.get("rating_avg") or 0.0,
        requires_certificate=bool(data.get("requires_certificate") or False),
        title_image=str(data["title_image"]) if data.get("title_image") else None,
        thumbnail_url=str(data["thumbnail_url"]) if data.get("thumbnail_url") else None,
        download_url=str(data["download_url"]) if data.get("download_url") else None,
        is_downloaded=bool(data.get("is_downloaded") or False),
    )

    _set_tags(course, data.get("tags"))

    course.progress = models.CourseProgress(progress=0)

    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def list_courses(db: Session, user_id) -> list[schemas.CourseDetailResponse]:
    courses = (
        db.query(models.Course)
        .order_by(models.Course.created_at.asc())
        .all()
    )
    return [_to_detail(course, user_id) for course in courses]


def get_course(course_id: int, db: Session) -> type[Course]:
    course = db.get(models.Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return course


def get_course_detail(course_id: int, user_id: int, db: Session) -> schemas.CourseDetailResponse:
    course = (
        db.query(models.Course)
        .filter(models.Course.id == course_id)
        .first()
    )
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return _to_detail(course, user_id)

def _extract_blob_path(value: str, expected_bucket: str) -> str:
    if value.startswith("gs://"):
        _, rest = value.split("gs://", 1)
        bucket, obj = rest.split("/", 1)
        if bucket != expected_bucket:
            raise HTTPException(status_code=400, detail="Bucket mismatch for stored URL")
        return obj
    if value.startswith("http://") or value.startswith("https://"):
        u = urlparse(value)
        if u.netloc.endswith(".storage.googleapis.com"):
            bucket = u.netloc.split(".storage.googleapis.com")[0]
            obj = u.path.lstrip("/")
        else:
            parts = u.path.lstrip("/").split("/", 1)
            if len(parts) < 2:
                raise HTTPException(status_code=400, detail="Invalid stored URL format")
            bucket, obj = parts[0], parts[1]
        if bucket != expected_bucket:
            raise HTTPException(status_code=400, detail="Bucket mismatch for stored URL")
        return obj
    return value.lstrip("/")

def get_course_download(course_id: int, db: Session, request) -> schemas.CourseDownloadOut:
    course = get_course(course_id, db)
    if not course.download_url:
        raise HTTPException(status_code=404, detail="Descarga no disponible para este curso")

    bucket_name = request.app.state.gcs_bucket.name
    blob_path = _extract_blob_path(course.download_url, expected_bucket=bucket_name)

    signed_url = request.app.state.signed_url_for(blob_path, ttl_seconds=3600, method="GET")

    return schemas.CourseDownloadOut(course_id=course.id, download_url=signed_url)


def get_progress(course_id: int, db: Session, user_id: int) -> schemas.CourseProgressOut:
    course = get_course(course_id, db)
    progress = (
        db.query(models.CourseProgress)
        .filter(
            models.CourseProgress.course_id == course.id,
            models.CourseProgress.user_id == user_id,
        )
        .one_or_none()
    )
    if not progress:
        return schemas.CourseProgressOut(course_id=course.id, progress=0, is_downloaded=False)
    return schemas.CourseProgressOut(
        course_id=course.id,
        progress=progress.progress,
        is_downloaded=bool(progress.is_downloaded)
    )


def upsert_progress(course_id: int, payload: schemas.CourseProgressIn, db: Session,
                    user_id: int) -> schemas.CourseProgressOut:
    course = get_course(course_id, db)

    if payload.progress is not None and not (0 <= payload.progress <= 100):
        raise HTTPException(status_code=422, detail="progress debe estar entre 0 y 100")

    progress = (
        db.query(models.CourseProgress)
        .filter(
            models.CourseProgress.course_id == course.id,
            models.CourseProgress.user_id == user_id,
        )
        .one_or_none()
    )

    if progress:
        if payload.progress is not None:
            progress.progress = payload.progress
    else:
        progress = models.CourseProgress(
            course_id=course.id,
            user_id=user_id,
            progress=payload.progress or 0,
        )
        db.add(progress)

    db.commit()
    db.refresh(progress)
    return schemas.CourseProgressOut(
        course_id=course.id,
        progress=progress.progress,
        is_downloaded=bool(progress.is_downloaded)
    )


def update_download_status(
        course_id: int,
        user_id: int,
        payload: schemas.CourseDownloadStatusIn,
        db: Session
) -> schemas.CourseProgressOut:
    """Update the download status for a specific user and course."""
    course = get_course(course_id, db)

    progress = (
        db.query(models.CourseProgress)
        .filter(
            models.CourseProgress.course_id == course.id,
            models.CourseProgress.user_id == user_id,
        )
        .one_or_none()
    )

    if progress:
        progress.is_downloaded = payload.is_downloaded
    else:
        # Create progress record if it doesn't exist
        progress = models.CourseProgress(
            course_id=course.id,
            user_id=user_id,
            progress=0,
            is_downloaded=payload.is_downloaded,
        )
        db.add(progress)

    db.commit()
    db.refresh(progress)
    return schemas.CourseProgressOut(
        course_id=course.id,
        progress=progress.progress,
        is_downloaded=bool(progress.is_downloaded)
    )


UPLOAD_ROOT = Path("uploads/courses")


async def upload_course_file(course_id, file, db, request):
    course = get_course(course_id, db)

    _, file_ext = os.path.splitext(file.filename or "")
    safe_name = f"course{file_ext}"
    blob_path = f"courses/{course.id}/{safe_name}"

    upload_fn = request.app.state.upload_bytes_to_gcs
    signed_url_fn = request.app.state.signed_url_for

    data = await file.read()
    upload_fn(blob_path, data, content_type=file.content_type)
    signed_url = signed_url_fn(blob_path)

    course.download_url = signed_url
    db.commit()
    db.refresh(course)
    return course


def _ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def _render_certificate_pdf_bytes(*, course_title: str, user_id: int, course_id: int, code: str,
                                  issued_at: datetime) -> bytes:
    # minimal reportlab PDF; add reportlab to your deps
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=A4)
        w, h = A4

        c.setFont("Helvetica-Bold", 24)
        c.drawCentredString(w / 2, h - 120, "Certificate of Completion")

        c.setFont("Helvetica", 16)
        c.drawCentredString(w / 2, h - 170, course_title)

        c.setFont("Helvetica", 12)
        c.drawCentredString(w / 2, h - 220, f"User ID: {user_id}  •  Course ID: {course_id}")

        c.setFont("Helvetica-Oblique", 11)
        c.drawCentredString(w / 2, 120, f"Code: {code}  •  Issued: {issued_at.isoformat(timespec='seconds')}")

        c.showPage()
        c.save()
        return buf.getvalue()
    except Exception as e:
        raise RuntimeError(f"PDF render failed: {e}")


async def download_certificate(course_id: int, user_id: int, db: Session):
    # 1) require 100% completion
    progress = get_progress(course_id, db, user_id=user_id)
    if (progress.progress or 0) < 100:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires 100% completion.")

    # 2) derive deterministic certificate code
    certificate_code = hash_certificate(user_id, course_id)
    issued_at = datetime.datetime.utcnow()

    # 3) render and save locally every time
    CERT_UPLOAD_ROOT = Path("uploads/certificates")

    course = get_course(course_id, db)
    rel_dir = CERT_UPLOAD_ROOT / str(course_id) / str(user_id)
    _ensure_dir(rel_dir)
    filename = f"certificate_{certificate_code}_{issued_at.strftime('%Y%m%dT%H%M%S')}.pdf"
    file_path = rel_dir / filename

    pdf_bytes = _render_certificate_pdf_bytes(
        course_title=course.title, user_id=user_id, course_id=course_id, code=certificate_code, issued_at=issued_at
    )
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    # 4) return payload (local path; your GCP uploader can read and push this file later)
    return schemas.CertificateOut(
        user_id=user_id,
        course_id=course_id,
        pdf_url=str(file_path),
        certificate_code=certificate_code,
        issued_at=issued_at,
    )


async def validate_certificate(course_id: int, user_id: int, certificate_code: str):
    valid = verify_certificate(user_id, course_id, certificate_code)
    return valid
