from datetime import datetime

from sqlalchemy import Integer, String, Boolean, Column, DateTime, func, ForeignKey, Enum, Text, Float, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# -------------------------------------------- USER --------------------------------------------
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password: Mapped[str] = mapped_column(String, nullable=False)
    phone: Mapped[str | None] = mapped_column(String, nullable=True)
    website: Mapped[str | None] = mapped_column(String, nullable=True)
    bio: Mapped[str | None] = mapped_column(String, nullable=True)
    gender: Mapped[str | None] = mapped_column(String, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


# -------------------------------------------- COURSE --------------------------------------------
CourseFormat = Enum("video", "xapi", "pdf", name="course_format")
CourseType = Enum("self_paced", "instructor_led", name="course_type")


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    duration_seconds = Column(Integer, nullable=True)
    format = Column(CourseFormat, nullable=False, default="video")
    course_type = Column(CourseType, nullable=False, default="self_paced")
    learning_goals = Column(Text)
    rating_avg = Column(Float, nullable=False, default=0.0)
    requires_certificate = Column(Boolean, nullable=False, default=False)
    title_image = Column(String)
    thumbnail_url = Column(String)
    download_url = Column(String)
    is_downloaded = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    progress = relationship("CourseProgress", back_populates="course", uselist=False, cascade="all, delete-orphan")
    tags = relationship("CourseTag", back_populates="course", cascade="all, delete-orphan")


class CourseProgress(Base):
    __tablename__ = "course_progress"

    course_id = Column(Integer, ForeignKey("courses.id"), primary_key=True)
    progress = Column(Integer, nullable=False, default=0)
    course = relationship("Course", back_populates="progress")


class CourseTag(Base):
    __tablename__ = "course_tags"

    id = Column(Integer, primary_key=True, autoincrement=True)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False, index=True)
    tag = Column(String, nullable=False)
    __table_args__ = (UniqueConstraint("course_id", "tag", name="uq_course_tag"),)
    course = relationship("Course", back_populates="tags")


# -------------------------------------------- WATCHLIST --------------------------------------------
class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course")
