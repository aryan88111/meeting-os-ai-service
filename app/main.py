from fastapi import FastAPI
from contextlib import asynccontextmanager
import logging
from app.core.config import settings
from app.api.v1.router import api_router
from app.worker.consumer import worker_consumer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("meetingos-ai-worker")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing MeetingOS AI Worker service...")
    try:
        # Start RabbitMQ async consumer
        await worker_consumer.start()
        yield
    finally:
        logger.info("Shutting down MeetingOS AI Worker service...")
        await worker_consumer.stop()

app = FastAPI(
    title="MeetingOS AI Worker Service",
    description="Enterprise AI meeting extraction, semantic chunking, embeddings, and document generation service",
    version="1.0.0",
    lifespan=lifespan,
)

# Register API v1 router
app.include_router(api_router, prefix="/api/v1")

@app.get("/health")
async def root_health():
    return {
        "status": "ok",
        "service": "MeetingOS AI Worker Service",
        "version": "1.0.0",
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=settings.WORKER_PORT, reload=True)
