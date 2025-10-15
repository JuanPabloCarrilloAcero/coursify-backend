from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.model import model as models
from app.model.model import Watchlist
from app.schema import schema as schemas


def get_watchlist(db: Session, user_id: str) -> list[type[Watchlist]]:
    return (
        db.query(models.Watchlist)
        .filter(models.Watchlist.user_id == user_id)
        .order_by(models.Watchlist.created_at.desc())
        .all()
    )


def add_to_watchlist(payload: schemas.WatchlistCreate, db: Session) -> models.Watchlist:
    # Verify course exists
    course = db.get(models.Course, payload.course_id)
    if not course:
        raise HTTPException(status_code=404, detail="Curso no encontrado")

    # Prevent duplicates
    existing = (
        db.query(models.Watchlist)
        .filter(
            models.Watchlist.user_id == payload.user_id,
            models.Watchlist.course_id == payload.course_id,
        )
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Curso ya está en la lista")

    item = models.Watchlist(
        id=str(uuid4()),
        user_id=payload.user_id,
        course_id=payload.course_id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


def remove_from_watchlist(user_id: str, course_id: str, db: Session) -> None:
    record = (
        db.query(models.Watchlist)
        .filter(
            models.Watchlist.user_id == user_id,
            models.Watchlist.course_id == course_id,
        )
        .first()
    )
    if not record:
        raise HTTPException(status_code=404, detail="No encontrado en la lista")

    db.delete(record)
    db.commit()
