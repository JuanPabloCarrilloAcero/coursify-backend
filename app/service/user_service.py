from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.model import model as models
from app.schema import schema as schemas


def create_user(user: schemas.User, db: Session):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email ya registrado")

    data = user.model_dump()
    data["password"] = hash(data["password"])
    user = models.User(**data)

    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(user_id: str, db: Session) -> models.User | None:
    return db.get(models.User, user_id)
