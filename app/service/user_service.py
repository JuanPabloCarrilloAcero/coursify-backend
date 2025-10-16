from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from starlette import status

from app.model import model as models
from app.schema import schema as schemas
from app.util.security import hash_password


def _to_profile_response(user: models.User) -> schemas.UserProfileResponse:
    return schemas.UserProfileResponse.model_validate(user, from_attributes=True)


def create_user(user_in: schemas.UserCreate, db: Session) -> schemas.UserProfileResponse:
    new_user = models.User(
        name=user_in.name.strip(),
        email=user_in.email.strip().lower(),
        password=hash_password(user_in.password),
        phone=(user_in.phone.strip() if user_in.phone else None),
        website=(user_in.website.strip() if user_in.website else None),
        bio=(user_in.bio.strip() if user_in.bio else None),
        gender=(user_in.gender if user_in.gender else None),
    )

    db.add(new_user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ya registrado")

    db.refresh(new_user)
    return _to_profile_response(new_user)


def edit_user(user_id: int, user_in: schemas.UserUpdate, db: Session) -> schemas.UserProfileResponse:
    user: models.User | None = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Usuario no encontrado")

    # Email
    if user_in.email is not None:
        user.email = user_in.email.strip().lower()

    # Name
    if user_in.name is not None:
        user.name = user_in.name.strip()

    # Password
    if user_in.password is not None and user_in.password != "":
        user.password = hash_password(user_in.password)

    # Optionals
    if user_in.phone is not None:
        user.phone = user_in.phone.strip() if user_in.phone != "" else None

    if user_in.website is not None:
        user.website = user_in.website.strip() if user_in.website != "" else None

    if user_in.bio is not None:
        user.bio = user_in.bio.strip() if user_in.bio != "" else None

    if user_in.gender is not None:
        user.gender = user_in.gender

    if user_in.active is not None:
        user.active = bool(user_in.active)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email ya registrado")

    db.refresh(user)
    return _to_profile_response(user)


def get_user(user_id: int, db: Session) -> schemas.UserProfileResponse | None:
    user = db.get(models.User, user_id)
    if not user:
        return None
    return _to_profile_response(user)
