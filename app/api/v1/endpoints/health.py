from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()

@router.get("/health")
async def health_check():
    return {
        "status": "ok",
        "service": "MeetingOS AI Worker Service",
        "version": "1.0.0",
        "provider": settings.AI_PROVIDER,
        "environment": settings.ENVIRONMENT,
    }
