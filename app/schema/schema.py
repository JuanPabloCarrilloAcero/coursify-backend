from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, HttpUrl


# -------------------------------------------- USER --------------------------------------------
class User(BaseModel):
    name: str
    email: str
    password: str


# -------------------------------------------- COURSE --------------------------------------------
class CourseCreate(BaseModel):
    id: Optional[str] = None
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[HttpUrl] = None
    download_url: Optional[HttpUrl] = None


class CourseOut(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    thumbnail_url: Optional[HttpUrl] = None
    download_url: Optional[HttpUrl] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CourseDownloadOut(BaseModel):
    course_id: str
    download_url: HttpUrl


class CourseProgressIn(BaseModel):
    progress: Optional[int] = None  # 0..100
    status: Optional[str] = None  # e.g., not_started | in_progress | completed


class CourseProgressOut(BaseModel):
    course_id: str
    progress: int
    status: str


# -------------------------------------------- WATCHLIST --------------------------------------------
class WatchlistCreate(BaseModel):
    course_id: str
    user_id: str


class WatchlistOut(BaseModel):
    id: str
    course_id: str
    user_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
