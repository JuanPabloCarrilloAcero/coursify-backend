from datetime import datetime, timedelta
import secrets
import string

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.model import model as models
from app.util.security import hash_password, verify_password


RESET_CODE_TTL_MINUTES = 10


def login_service(email: str, password: str, db):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not verify_password(password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = 'igxApoxPwT66sYBzenkEUf6YMtzk8Zh7'
    return {"access_token": token, "user_id": user.id, }


def _require_user(email: str, db: Session) -> models.User:
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def _generate_numeric_code(length: int = 4) -> str:
    pool = string.digits
    return ''.join(secrets.choice(pool) for _ in range(length))


def request_password_reset(email: str, db: Session) -> tuple[str, int]:
    user = _require_user(email, db)

    db.query(models.PasswordResetToken).filter(
        models.PasswordResetToken.user_id == user.id,
        models.PasswordResetToken.used.is_(False),
    ).update({models.PasswordResetToken.used: True})

    code = _generate_numeric_code()
    expires_at = datetime.utcnow() + timedelta(minutes=RESET_CODE_TTL_MINUTES)

    token = models.PasswordResetToken(
        user_id=user.id,
        code=code,
        expires_at=expires_at,
    )
    db.add(token)
    db.commit()

    return code, RESET_CODE_TTL_MINUTES


def _get_active_token(user_id: int, code: str, db: Session) -> models.PasswordResetToken:
    token = (
        db.query(models.PasswordResetToken)
        .filter(
            models.PasswordResetToken.user_id == user_id,
            models.PasswordResetToken.code == code,
            models.PasswordResetToken.used.is_(False),
        )
        .order_by(models.PasswordResetToken.created_at.desc())
        .first()
    )

    if not token or token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Código inválido o expirado")

    return token


def verify_reset_code(email: str, code: str, db: Session) -> None:
    user = _require_user(email, db)
    _get_active_token(user.id, code, db)


def reset_password_with_code(email: str, code: str, password: str, db: Session) -> None:
    user = _require_user(email, db)
    token = _get_active_token(user.id, code, db)

    user.password = hash_password(password)
    token.used = True
    db.commit()
