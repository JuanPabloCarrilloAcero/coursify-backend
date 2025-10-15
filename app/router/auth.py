from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config.settings import get_db
from app.service.auth_service import login_service

router = APIRouter()


class SignInReq(BaseModel):
    email: str
    password: str


@router.post('/login')
async def login(body: SignInReq, db: Session = Depends(get_db)):
    token = login_service(body.email, body.password, db)
    return token
