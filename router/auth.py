from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["auth"])

class SignInReq(BaseModel):
    email: str
    password: str

@router.post('/login')
async def login(body: SignInReq):
    # TODO: Implement login service
    token = "igxApoxPwT66sYBzenkEUf6YMtzk8Zh7"
    return token