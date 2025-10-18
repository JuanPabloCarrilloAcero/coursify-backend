from datetime import datetime
from typing import Optional, List, Literal

from pydantic import BaseModel, ConfigDict, Field, EmailStr


# -------------------------------------------- USER --------------------------------------------
class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    phone: Optional[str] = None
    website: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[Literal["male", "female", "other"]] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    password: Optional[str] = None
    phone: Optional[str] = None
    website: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[Literal["male", "female", "other"]] = None
    active: Optional[bool] = None


class UserProfileResponse(BaseModel):
    id: int
    name: str
    email: str
    phone: Optional[str] = None
    website: Optional[str] = None
    bio: Optional[str] = None
    gender: Optional[Literal["male", "female", "other"]] = None
    avatar_url: Optional[str] = None
    avatar_thumbnail_url: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True  # Pydantic v2


# -------------------------------------------- COURSE --------------------------------------------
FormatLiteral = Literal["video", "xapi", "pdf"]
CourseTypeLiteral = Literal["self_paced", "instructor_led"]


# Incoming create/update payloads
class CourseCreate(BaseModel):
    id: Optional[int] = None
    title: str
    description: Optional[str] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    format: Optional[FormatLiteral] = "video"
    course_type: Optional[CourseTypeLiteral] = "self_paced"
    learning_goals: Optional[list[str]] = []
    rating_avg: Optional[float] = Field(0.0, ge=0, le=5)
    requires_certificate: Optional[bool] = False
    title_image: Optional[str] = None
    thumbnail_url: Optional[str] = None
    download_url: Optional[str] = None
    is_downloaded: Optional[bool] = False
    tags: Optional[List[str]] = None


class CourseUpdate(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    duration_seconds: Optional[int] = Field(None, ge=0)
    format: Optional[FormatLiteral] = None
    course_type: Optional[CourseTypeLiteral] = None
    learning_goals: Optional[list[str]] = []
    rating_avg: Optional[float] = Field(None, ge=0, le=5)
    requires_certificate: Optional[bool] = None
    title_image: Optional[str] = None
    thumbnail_url: Optional[str] = None
    download_url: Optional[str] = None
    is_downloaded: Optional[bool] = None
    tags: Optional[List[str]] = None


# Progress I/O (progress is a different entity)
class CourseProgressIn(BaseModel):
    progress: Optional[int] = Field(None, ge=0, le=100)


class CourseProgressOut(BaseModel):
    course_id: int
    progress: int


# “Slim” out
class CourseOut(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    title_image: Optional[str] = None
    thumbnail_url: Optional[str] = None
    download_url: Optional[str] = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


# Full DTO aligned to your required response
class CourseDetailResponse(BaseModel):
    id: int
    title: str
    description: Optional[str] = None
    duration: Optional[str] = None  # "1h 30m" or "5400s"
    format: FormatLiteral
    course_type: CourseTypeLiteral
    learning_goals: Optional[list[str]] = []
    rating: float  # 1..5 average
    is_downloaded: bool
    progress: int  # 0..100
    title_image: Optional[str] = None
    thumbnail_url: Optional[str] = None
    tags: Optional[List[str]] = None
    requires_certificate: bool
    model_config = ConfigDict(from_attributes=True)


class CourseDownloadOut(BaseModel):
    course_id: int  # use str if you kept UUID PKs
    download_url: str


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
