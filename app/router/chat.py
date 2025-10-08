from fastapi import APIRouter

from app.service.chat_service import send_message_service

router = APIRouter()


@router.post('/send')
async def send_message(body: dict):
    return send_message_service(body['message'])
