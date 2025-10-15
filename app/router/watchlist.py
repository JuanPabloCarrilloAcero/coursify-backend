from fastapi import APIRouter, Depends, status, Query
from sqlalchemy.orm import Session

from app.config.settings import get_db
from app.schema import schema as schemas
from app.service import watchlist_service

router = APIRouter()


@router.get("/get", response_model=list[schemas.WatchlistOut])
async def get_watchlist(
        user_id: str = Query(..., description="ID del usuario"),
        db: Session = Depends(get_db),
):
    items = watchlist_service.get_watchlist(db, user_id)
    return [schemas.WatchlistOut.model_validate(i) for i in items]


@router.post("/", response_model=schemas.WatchlistOut, status_code=status.HTTP_201_CREATED)
async def add_watchlist(payload: schemas.WatchlistCreate, db: Session = Depends(get_db)):
    item = watchlist_service.add_to_watchlist(payload, db)
    return schemas.WatchlistOut.model_validate(item)


@router.delete("/", status_code=status.HTTP_204_NO_CONTENT)
async def delete_watchlist(
        user_id: str = Query(...),
        course_id: str = Query(...),
        db: Session = Depends(get_db),
):
    watchlist_service.remove_from_watchlist(user_id, course_id, db)
    return
