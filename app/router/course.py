from fastapi import APIRouter, Depends, UploadFile, File
from sqlalchemy.orm import Session
from starlette import status

from app.config.settings import get_db
from app.schema.schema import CourseOut, CourseDownloadOut, CourseDetailResponse, CourseProgressOut, CourseProgressIn, \
    CourseCreate, CourseDownloadStatusIn
from app.service import course_service

router = APIRouter()


@router.get("/{user_id}", response_model=list[CourseDetailResponse])
async def get_all(user_id: int, db: Session = Depends(get_db)):
    courses = course_service.list_courses(db, user_id)
    return courses


@router.get("/detail/{course_id}/{user_id}", response_model=CourseDetailResponse)
async def get_detail(course_id: int, user_id: int, db: Session = Depends(get_db)):
    return course_service.get_course_detail(course_id, user_id, db)


@router.get("/{course_id}/download", response_model=CourseDownloadOut)
async def download_by_id(course_id: int, db: Session = Depends(get_db)):
    return course_service.get_course_download(course_id, db)


@router.get("/{course_id}/progress/{user_id}", response_model=CourseProgressOut)
async def progress_by_id(course_id: int, user_id: int, db: Session = Depends(get_db)) -> CourseProgressOut:
    return course_service.get_progress(course_id, db, user_id=user_id)


@router.patch("/{course_id}/progress/{user_id}", response_model=CourseProgressOut)
async def progress_update(course_id: int, user_id: int, payload: CourseProgressIn,
                          db: Session = Depends(get_db)) -> CourseProgressOut:
    return course_service.upsert_progress(course_id, payload, db, user_id=user_id)


@router.patch("/{course_id}/download/{user_id}", response_model=CourseProgressOut)
async def update_download_status(
    course_id: int,
    user_id: int,
    payload: CourseDownloadStatusIn,
    db: Session = Depends(get_db)
) -> CourseProgressOut:
    return course_service.update_download_status(course_id, user_id, payload, db)


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
