from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from starlette import status

from app.config.settings import get_db
from app.schema import schema as schemas
from app.service import course_service

router = APIRouter()


@router.get("/", response_model=list[schemas.CourseOut])
async def get_all(db: Session = Depends(get_db)):
    courses = course_service.list_courses(db)
    return [schemas.CourseOut.model_validate(c) for c in courses]


@router.get("/info/{course_id}", response_model=schemas.CourseOut)
async def info_by_id(course_id: str, db: Session = Depends(get_db)):
    course = course_service.get_course(course_id, db)
    return schemas.CourseOut.model_validate(course)


@router.get("/download/{course_id}", response_model=schemas.CourseDownloadOut)
async def download_by_id(course_id: str, db: Session = Depends(get_db)):
    return course_service.get_course_download(course_id, db)


@router.get("/progress/{course_id}", response_model=schemas.CourseProgressOut)
async def progress_by_id(course_id: str, db: Session = Depends(get_db)):
    return course_service.get_progress(course_id, db)


@router.post("/progress/{course_id}", response_model=schemas.CourseProgressOut)
async def progress_by_id_post(
        course_id: str, payload: schemas.CourseProgressIn, db: Session = Depends(get_db)
):
    return course_service.upsert_progress(course_id, payload, db)


@router.post("/", response_model=schemas.CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(payload: schemas.CourseCreate, db: Session = Depends(get_db)):
    course = course_service.create_course(payload, db)
    return schemas.CourseOut.model_validate(course)
