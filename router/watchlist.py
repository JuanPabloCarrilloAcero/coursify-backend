from fastapi import APIRouter

router = APIRouter()


@router.get('/get')
async def get_watchlist():
    return {'message': 'Watchlist'}
