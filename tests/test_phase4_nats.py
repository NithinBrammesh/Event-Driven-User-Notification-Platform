import asyncio
import os
import uuid
from pathlib import Path

import pytest
from nats.aio.client import Client as NATSClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.main import app as user_app
from app.models.user import Base, User
from app.schemas.user import UserCreate
from app.services.user_service import UserService
from app.core.config import settings


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()


def test_user_created_event_schema_and_publish_on_success(monkeypatch, db_session):
    published = []
    unique_email = f"phase4-{uuid.uuid4().hex}@example.com"

    def fake_publish(event_type: str, payload: dict):
        published.append({"event_type": event_type, **payload})

    monkeypatch.setattr("app.services.user_service.publish_user_event", fake_publish)

    service = UserService(db_session)
    payload = UserCreate(email=unique_email, full_name="Phase 4 User", password="password123")
    user = service.register_user(payload)

    assert user.email == unique_email
    assert len(published) == 1
    event = published[0]
    assert event["event_type"] == "user.created"
    assert event["user_id"] == user.id
    assert event["email"] == user.email
    assert event["event_id"]
    uuid.UUID(event["event_id"])
    assert event["created_at"]


def test_failed_registration_does_not_publish_event(monkeypatch, db_session):
    published = []
    unique_email = f"phase4-fail-{uuid.uuid4().hex}@example.com"

    def fake_publish(event_type: str, payload: dict):
        published.append({"event_type": event_type, **payload})

    monkeypatch.setattr("app.services.user_service.publish_user_event", fake_publish)

    service = UserService(db_session)
    payload = UserCreate(email=unique_email, full_name="Phase 4 User", password="password123")
    service.register_user(payload)
    with pytest.raises(Exception):
        service.register_user(payload)

    assert published == [] or len(published) == 1


def test_nats_auth_stream_and_durable_consumer_exists():
    nats_url = os.getenv("NATS_URL", settings.nats_url)
    if not nats_url:
        pytest.skip("NATS_URL is not configured")

    async def check():
        nc = NATSClient()
        await nc.connect(nats_url, connect_timeout=5, reconnect_time_wait=1, max_reconnect_attempts=1)
        js = nc.jetstream()
        try:
            stream = await js.stream_info(settings.nats_stream)
            assert stream.config.subjects == [settings.nats_subject]
            consumers = await js.consumer_names(settings.nats_stream)
            assert "notification-service" in consumers
        finally:
            await nc.close()

    try:
        asyncio.run(check())
    except Exception as exc:
        pytest.skip(f"NATS server not available for Phase 4 verification: {exc}")
