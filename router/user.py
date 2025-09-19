from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["auth"])

class UserReq(BaseModel):
    name: str
    email: str
    password: str

@router.post('/create')
async def create(body: UserReq):
    # TODO: Implement login service
    token = "igxApoxPwT66sYBzenkEUf6YMtzk8Zh7"
    return {token: token, **body.model_dump()}
