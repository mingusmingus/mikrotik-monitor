from fastapi import FastAPI
from app.core.config import settings
from app.core.logging import configure_logging
from app.api.router import api_router

app = FastAPI(title=settings.APP_NAME, debug=settings.DEBUG)
configure_logging(app)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)

@app.get("/health", tags=["system"])
def health():
    return {"status": "ok", "env": settings.ENV}
