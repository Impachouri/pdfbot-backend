import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routes import router
from app.database import init_db
from dotenv import load_dotenv

load_dotenv()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield
    # Any cleanup code here

app = FastAPI(lifespan=lifespan)
FrontEnd = os.getenv("FrontEnd")
origins = [
    FrontEnd,  
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)
