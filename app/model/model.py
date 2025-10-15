from sqlalchemy import Integer, String, Boolean, Column, Text, DateTime, func, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# -------------------------------------------- USER --------------------------------------------
class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password: Mapped[str] = mapped_column(String)
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


# -------------------------------------------- COURSE --------------------------------------------
class Course(Base):
    __tablename__ = "courses"
    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text)
    thumbnail_url = Column(String)
    download_url = Column(String)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    progress = relationship("CourseProgress", back_populates="course", uselist=False)


class CourseProgress(Base):
    __tablename__ = "course_progress"
    course_id = Column(String, ForeignKey("courses.id"), primary_key=True)
    progress = Column(Integer, nullable=False, default=0)  # 0..100
    status = Column(String, nullable=False, default="in_progress")
    course = relationship("Course", back_populates="progress")


# -------------------------------------------- WATCHLIST --------------------------------------------
class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, nullable=False, index=True)
    course_id = Column(String, ForeignKey("courses.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    course = relationship("Course")
