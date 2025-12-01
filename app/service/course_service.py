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
from app.service.user_service import get_user


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
                                  issued_at: datetime, db: Session) -> bytes:
    # minimal reportlab PDF; add reportlab to your deps
    try:
        from io import BytesIO
        from reportlab.pdfgen import canvas
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.lib.utils import ImageReader
        from pathlib import Path

        PAGE_SIZE_16_9 = (1920, 1080)

        buf = BytesIO()
        c = canvas.Canvas(buf, pagesize=PAGE_SIZE_16_9)
        w, h = PAGE_SIZE_16_9

        BASE_DIR = Path(__file__).resolve().parent

        user_name = get_user(user_id, db).name if user_id else "No Name"
        font_path = (BASE_DIR.parent.parent / "assets" / "fonts").resolve()
        images_path = (BASE_DIR.parent.parent / "assets" / "images").resolve()

        pdfmetrics.registerFont(TTFont("Anton", os.path.join(font_path, "Anton-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Nunito", os.path.join(font_path, "Nunito-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("Nunito-Italic", os.path.join(font_path, "Nunito-Italic.ttf")))
        pdfmetrics.registerFont(TTFont("GreatVibes", os.path.join(font_path, "GreatVibes-Regular.ttf")))
        pdfmetrics.registerFont(TTFont("MomoTrustDisplay", os.path.join(font_path, "MomoTrustDisplay-Regular.ttf")))

        margin_ext = 50
        margin_int = 80

        c.setLineWidth(3)
        c.setStrokeColorRGB(34/255, 54/255, 111/255)
        c.rect(margin_ext, margin_ext, w - margin_ext * 2, h - margin_ext * 2, stroke=1, fill=0)

        c.setStrokeColorRGB(72/255, 171/255, 182/255)
        c.rect(margin_int, margin_int, w - margin_int * 2, h - margin_int * 2, stroke=1, fill=0)

        up_corner = ImageReader(os.path.join(images_path, "certificate_up_corner.png"))
        down_corner = ImageReader(os.path.join(images_path, "certificate_down_corner.png"))
        c.drawImage(up_corner, w - 1232, h - 286, width=1233, height=286, mask='auto')
        c.drawImage(down_corner, -1, -1, width=1233, height=286, mask='auto')

        c.setFont("Anton", 76.5)
        c.setFillColorRGB(34/255, 54/255, 111/255)
        c.drawCentredString(w / 2, h - 230, "CERTIFICATE OF COMPLETION")

        c.setFont("Nunito", 37)
        c.setFillColorRGB(34/255, 54/255, 111/255)
        c.drawCentredString(w / 2, h - 330, "This certificate is presented to:")

        c.setLineWidth(3)
        c.setStrokeColorRGB(72/255, 171/255, 182/255)
        c.line((w / 2 - (c.stringWidth(user_name, "GreatVibes", 104) / 2)), h - 515, (w / 2 + (c.stringWidth(user_name, "GreatVibes", 104) / 2)), h - 515)

        c.setFont("GreatVibes", 104)
        c.setFillColorRGB(34/255, 54/255, 111/255)
        c.drawCentredString(w / 2, h - 500, user_name)

        c.setFont("Nunito", 37)
        c.setFillColorRGB(34/255, 54/255, 111/255)
        c.drawCentredString(w / 2, h - 640, "For completing the course")

        c.setFont("Nunito-Italic", 47)
        c.setFillColorRGB(34/255, 54/255, 111/255)
        c.drawCentredString(w / 2, h - 710, course_title)

        logo = ImageReader(os.path.join(images_path, "certificate_coursify_logo.png"))
        spacing = 20
        logo_x = w / 2 - (100 / 2) - spacing - (c.stringWidth("COURSIFY", "Nunito", 37) / 2)
        c.drawImage(logo, logo_x, h - 893, width=100, height=100, mask='auto')

        c.setFont("MomoTrustDisplay", 37)
        c.setFillColorRGB(72/255, 171/255, 182/255)
        c.drawCentredString((w / 2) + 60, h - 860, "COURSIFY")

        c.setFont("Nunito", 15)
        c.setFillColorRGB(1, 1, 1)
        text = f"This certificate can be validated using the following code: {code}"
        c.drawString(10, 10, text)

        c.showPage()
        c.save()
        return buf.getvalue()
    except Exception as e:
        raise RuntimeError(f"PDF render failed: {e}")


async def download_certificate(course_id: int, user_id: int, db: Session, request):
    # 1) require 100% completion
    progress = get_progress(course_id, db, user_id=user_id)
    if (progress.progress or 0) < 100:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Requires 100% completion.")

    # 2) derive deterministic certificate code
    certificate_hash = hash_certificate(user_id, course_id)
    certificate_code = certificate_hash + "-" + user_id.__str__() + "-" + course_id.__str__()
    issued_at = datetime.datetime.utcnow()

    # 3) render PDF bytes
    course = get_course(course_id, db)
    pdf_bytes = _render_certificate_pdf_bytes(
        course_title=course.title,
        user_id=user_id,
        course_id=course_id,
        code=certificate_code,
        issued_at=issued_at,
        db=db,
    )

    # 4) upload to Buckjet (via app.state uploader)
    upload_fn = request.app.state.upload_bytes_to_gcs  # wired to Buckjet
    signed_url_fn = request.app.state.signed_url_for

    # path in bucket: certificates/<course_id>/<user_id>/certificate_<code>_<timestamp>.pdf
    timestamp = issued_at.strftime('%Y%m%dT%H%M%S')
    blob_path = (
        f"certificates/{course_id}/{user_id}/"
        f"certificate_{certificate_code}_{timestamp}.pdf"
    )

    upload_fn(blob_path, pdf_bytes, content_type="application/pdf")
    signed_url = signed_url_fn(blob_path)

    # 5) return payload (public/signed URL from Buckjet)
    return schemas.CertificateOut(
        user_id=user_id,
        course_id=course_id,
        pdf_url=signed_url,
        certificate_code=certificate_code,
        issued_at=issued_at,
    )


async def validate_certificate(certificate_code: str):
    user_id = int(certificate_code.split("-")[-2])
    course_id = int(certificate_code.split("-")[-1])
    certificate_hash = "-".join(certificate_code.split("-")[:-2])
    valid = verify_certificate(user_id, course_id, certificate_hash)
    return valid
