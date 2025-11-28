from fastapi import APIRouter, BackgroundTasks, Depends
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from app.config.settings import get_db
from app.service.auth_service import (
    login_service,
    request_password_reset,
    reset_password_with_code,
    verify_reset_code,
)
from app.util.email_sender import send_password_reset_email

router = APIRouter()


class SignInReq(BaseModel):
    email: str
    password: str


class PasswordResetReq(BaseModel):
    email: EmailStr


class PasswordResetCodeReq(BaseModel):
    email: EmailStr
    code: str = Field(min_length=4, max_length=8, pattern=r"^\d{4,8}$")


class PasswordResetConfirmReq(PasswordResetCodeReq):
    new_password: str = Field(min_length=8, max_length=128)


@router.post('/login')
async def login(body: SignInReq, db: Session = Depends(get_db)):
    token = login_service(body.email, body.password, db)
    return token


@router.post('/password-reset/request')
async def password_reset_request(
    body: PasswordResetReq,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    code, ttl = request_password_reset(body.email, db)
    background_tasks.add_task(send_password_reset_email, body.email, code, ttl_minutes=ttl)
    return {"detail": "Código enviado"}


@router.post('/password-reset/verify')
async def password_reset_verify(body: PasswordResetCodeReq, db: Session = Depends(get_db)):
    verify_reset_code(body.email, body.code, db)
    return {"detail": "Código válido"}


@router.post('/password-reset/confirm')
async def password_reset_confirm(body: PasswordResetConfirmReq, db: Session = Depends(get_db)):
    reset_password_with_code(body.email, body.code, body.new_password, db)
    return {"detail": "Contraseña actualizada"}
