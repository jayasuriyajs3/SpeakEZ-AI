from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.settings import settings
from app.ws import router as ws_router
from app.db import init_db
from app.api import router as api_router


def create_app() -> FastAPI:
    app = FastAPI(title="SPEAKEZ AI API", version="0.1.0")

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_allow_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health():
        return {"ok": True}

    app.include_router(ws_router)
    app.include_router(api_router)
    init_db()
    return app


app = create_app()

