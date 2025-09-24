from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.settings import get_db
from app.schema.schema import User as UserSchema
from app.service.user_service import create_user, get_user

router = APIRouter(tags=["auth"])


@router.post('/create')
async def create(body: UserSchema, db: Session = Depends(get_db)):
    return create_user(body, db)


@router.get('/get/{user_id}')
async def get(user_id: str, db: Session = Depends(get_db)):
    return get_user(user_id, db)
