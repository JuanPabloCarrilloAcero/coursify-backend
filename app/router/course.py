from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from starlette import status

from app.config.settings import get_db
from app.schema.schema import CourseOut, CourseDownloadOut, CourseDetailResponse, CourseProgressOut, CourseProgressIn, \
    CourseCreate
from app.service import course_service

router = APIRouter()


@router.get("/", response_model=list[CourseDetailResponse])
async def get_all(db: Session = Depends(get_db)):
    courses = course_service.list_courses(db)
    return courses


@router.get("/{course_id}", response_model=CourseDetailResponse)
async def get_detail(course_id: int, db: Session = Depends(get_db)):
    return course_service.get_course_detail(course_id, db)


@router.get("/{course_id}/download", response_model=CourseDownloadOut)
async def download_by_id(course_id: int, db: Session = Depends(get_db)):
    return course_service.get_course_download(course_id, db)


@router.get("/{course_id}/progress", response_model=CourseProgressOut)
async def progress_by_id(course_id: int, db: Session = Depends(get_db)):
    return course_service.get_progress(course_id, db)


@router.patch("/{course_id}/progress", response_model=CourseProgressOut)
async def progress_update(course_id: int, payload: CourseProgressIn, db: Session = Depends(get_db)):
    return course_service.upsert_progress(course_id, payload, db)


@router.post("/", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def create_course(payload: CourseCreate, db: Session = Depends(get_db)):
    course = course_service.create_course(payload, db)
    return course


@router.post("/{course_id}/upload", response_model=CourseOut, status_code=status.HTTP_201_CREATED)
async def upload_course_file(
        course_id: int,
        file: UploadFile = File(...),
        db: Session = Depends(get_db),
):
    return await course_service.upload_course_file(course_id, file, db)
