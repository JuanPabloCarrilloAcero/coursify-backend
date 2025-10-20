import os
from pathlib import Path
from typing import Optional, Iterable

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.model import model as models
from app.model.model import Course
from app.schema import schema as schemas


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
    if course.progress_items:
        user_progress = next((p for p in course.progress_items if p.user_id == user_id), None)
        if user_progress:
            progress_val = user_progress.progress

    return schemas.CourseDetailResponse(
        id=course.id,
        title=course.title,
        description=course.description,
        duration=_format_duration(course.duration_seconds),
        format=course.format,
        course_type=course.course_type,
        learning_goals=course.learning_goals,
        rating=round(course.rating_avg or 0.0, 2),
        is_downloaded=bool(course.is_downloaded),
        progress=progress_val,
        title_image=course.title_image,
        thumbnail_url=course.thumbnail_url,
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


def get_course_download(course_id: int, db: Session) -> schemas.CourseDownloadOut:
    course = get_course(course_id, db)
    dumb_url = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
    if not course.download_url:
        raise HTTPException(status_code=404, detail="Descarga no disponible para este curso")
    return schemas.CourseDownloadOut(course_id=course.id, download_url=dumb_url)


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
        return schemas.CourseProgressOut(course_id=course.id, progress=0)
    return schemas.CourseProgressOut(course_id=course.id, progress=progress.progress)


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
    return schemas.CourseProgressOut(course_id=course.id, progress=progress.progress)


UPLOAD_ROOT = Path("uploads/courses")


async def upload_course_file(course_id, file, db):
    course = get_course(course_id, db)

    dest_dir = UPLOAD_ROOT / str(course.id)
    dest_dir.mkdir(parents=True, exist_ok=True)

    # Save file locally
    file_ext = os.path.splitext(file.filename)[1]
    safe_name = f"course{file_ext or ''}"
    file_path = dest_dir / safe_name

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # Store local path as download_url (relative or absolute)
    # For now, local path; in the future, replace with GCP bucket URL.
    course.download_url = str(file_path)
    db.commit()
    db.refresh(course)

    return course
