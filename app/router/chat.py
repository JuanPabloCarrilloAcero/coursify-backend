from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.config.settings import get_genai, get_db
from app.service.chat_service import send_message_service

router = APIRouter()


@router.post('/send')
async def send_message(body: dict, genai=Depends(get_genai), db: Session = Depends(get_db)):
    message = body.get('message')
    if not message:
        return {"response": "Debes ingresar un mensaje."}

    return send_message_service(
        message,
        genai,
        db=db,
        course_id=body.get('course_id')
    )
