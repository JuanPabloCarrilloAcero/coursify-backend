from fastapi import APIRouter

router = APIRouter()


@router.post('/send')
async def send_message(body: dict):
    return {'message': body['message']}
