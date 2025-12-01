from fastapi import APIRouter, Depends

from app.config.settings import get_genai
from app.service.chat_service import send_message_service

router = APIRouter()


@router.post('/send')
async def send_message(body: dict, genai=Depends(get_genai)):
    return send_message_service(body['message'], genai)
