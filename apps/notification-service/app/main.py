import os

from fastapi import FastAPI

from app.db.session import Base, engine
from app.models.notification import Notification
from app.service import NotificationService

app = FastAPI(title="Notification Service")

nats_url = os.getenv("NATS_URL", "nats://nats:4222")
stream_name = os.getenv("NATS_STREAM", "user_events")
subject = os.getenv("NATS_SUBJECT", "user.created")
consumer_name = os.getenv("NATS_CONSUMER_NAME", "notification-service")
service = NotificationService(
    nats_url=nats_url,
    stream_name=stream_name,
    subject=subject,
    consumer_name=consumer_name,
    nats_username=os.getenv("NATS_USERNAME", ""),
    nats_password=os.getenv("NATS_PASSWORD", ""),
)


@app.on_event("startup")
async def startup_event() -> None:
    Base.metadata.create_all(bind=engine)
    await service.start()


@app.on_event("shutdown")
async def shutdown_event() -> None:
    await service.stop()


@app.get("/health")
def health() -> dict:
    return {"status": "ok", "service": "notification-service"}


@app.get("/notifications/last-event")
def last_event() -> dict:
    return {"event": service.last_event}
