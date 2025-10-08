from fastapi import HTTPException, status

from app.model import model as models
from app.util.security import verify_password


def login_service(email: str, password: str, db):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    if not verify_password(password, user.password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = 'igxApoxPwT66sYBzenkEUf6YMtzk8Zh7'
    return {"access_token": token}
