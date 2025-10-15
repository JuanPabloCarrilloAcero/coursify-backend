from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.model import model as models
from app.schema import schema as schemas


def create_course(payload: schemas.CourseCreate, db: Session) -> models.Course:
    data = payload.model_dump()

    # if client provided id, ensure it's free; else generate one
    course_id = data.get("id") or str(uuid4())
    exists = db.get(models.Course, course_id)
    if exists:
        raise HTTPException(status_code=400, detail="ID de curso ya existe")

    course = models.Course(
        id=course_id,
        title=data["title"],
        description=data.get("description"),
        thumbnail_url=str(data["thumbnail_url"]) if data.get("thumbnail_url") else None,
        download_url=str(data["download_url"]) if data.get("download_url") else None,
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course


def list_courses(db: Session) -> list[models.Course]:
    return db.query(models.Course).order_by(models.Course.created_at.desc()).all()


def get_course(course_id: str, db: Session) -> models.Course:
    course = db.get(models.Course, course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")
    return course


def get_course_download(course_id: str, db: Session) -> schemas.CourseDownloadOut:
    course = get_course(course_id, db)
    if not course.download_url:
        raise HTTPException(status_code=404, detail="Descarga no disponible para este curso")
    return schemas.CourseDownloadOut(course_id=course.id, download_url=course.download_url)


def get_progress(course_id: str, db: Session) -> schemas.CourseProgressOut:
    course = get_course(course_id, db)
    progress = (
        db.query(models.CourseProgress)
        .filter(models.CourseProgress.course_id == course.id)
        .one_or_none()
    )
    if not progress:
        # 0% by default if never tracked
        return schemas.CourseProgressOut(course_id=course.id, progress=0, status="not_started")
    return schemas.CourseProgressOut(
        course_id=course.id, progress=progress.progress, status=progress.status
    )


def upsert_progress(course_id: str, payload: schemas.CourseProgressIn, db: Session) -> schemas.CourseProgressOut:
    course = get_course(course_id, db)

    if payload.progress is not None and not (0 <= payload.progress <= 100):
        raise HTTPException(status_code=422, detail="progress debe estar entre 0 y 100")

    progress = (
        db.query(models.CourseProgress)
        .filter(models.CourseProgress.course_id == course.id)
        .one_or_none()
    )

    if progress:
        if payload.progress is not None:
            progress.progress = payload.progress
        if payload.status is not None:
            progress.status = payload.status
    else:
        progress = models.CourseProgress(
            course_id=course.id,
            progress=payload.progress or 0,
            status=payload.status or "in_progress",
        )
        db.add(progress)

    db.commit()
    db.refresh(progress)

    return schemas.CourseProgressOut(
        course_id=course.id, progress=progress.progress, status=progress.status
    )
