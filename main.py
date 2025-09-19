from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

from middleware.verify_middleware import VerifyTokenMiddleware
from router import auth, watchlist, course, chat, user
from util.log_time import log_time


@asynccontextmanager
async def lifespan(appFastAPI: FastAPI):
    log_time("🔄:       Initializing application...")
    log_time("✅:       Startup complete. Global dependencies initialized.")

    yield

    log_time("⚠️:       Cleanup: Application is shutting down...")


app = FastAPI(lifespan=lifespan)

app.add_middleware(VerifyTokenMiddleware)
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'],
                   allow_headers=['*'])

app.include_router(auth.router, prefix='/auth')
app.include_router(chat.router, prefix='/chat')
app.include_router(course.router, prefix='/course')
app.include_router(user.router, prefix='/user')
app.include_router(watchlist.router, prefix='/watchlist')


@app.get("/ping")
async def ping():
    return {"ping": "pong!"}
