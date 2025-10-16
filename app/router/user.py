from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from starlette import status

from app.config.settings import get_db
from app.schema import schema as schemas
from app.service.user_service import create_user, get_user, edit_user

router = APIRouter(tags=["auth"])


@router.post("/create", response_model=schemas.UserProfileResponse, status_code=status.HTTP_201_CREATED)
def create(payload: schemas.UserCreate, db: Session = Depends(get_db)):
    return create_user(payload, db)


@router.patch("/edit/{user_id}", response_model=schemas.UserProfileResponse)
def edit(user_id: int, payload: schemas.UserUpdate, db: Session = Depends(get_db)):
    return edit_user(user_id, payload, db)


@router.get("/get/{user_id}", response_model=schemas.UserProfileResponse)
def get(user_id: int, db: Session = Depends(get_db)):
    user = get_user(user_id, db)
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    return user
