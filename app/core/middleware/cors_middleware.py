from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI
from app.core.config import settings

def register_cors(app: FastAPI) -> None:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )