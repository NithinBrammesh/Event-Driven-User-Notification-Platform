import asyncio
import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

import app.service as notification_service_module
from app.db.session import Base
from app.models.notification import Notification
from app.service import NotificationService


class FakeMessage:
    def __init__(self, payload):
        self.data = json.dumps(payload).encode("utf-8")
        self.ack_count = 0

    async def ack(self):
        self.ack_count += 1


class FakeProvider:
    def __init__(self):
        self.calls = 0

    def send(self, email: str, message: str) -> bool:
        self.calls += 1
        return True


def create_test_session_factory():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    return sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=engine,
    )


def test_failed_notification_is_reused_and_retried(monkeypatch):
    SessionTest = create_test_session_factory()

    monkeypatch.setattr(
        notification_service_module,
        "SessionLocal",
        SessionTest,
    )

    db = SessionTest()

    event_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    failed_notification = Notification(
        event_id=event_id,
        user_id=1001,
        email="retry@example.com",
        status="failed",
        error_message="Mock provider failed",
        created_at=created_at,
        processed_at=None,
    )

    db.add(failed_notification)
    db.commit()

    original_id = failed_notification.id

    service = NotificationService(
        nats_url="nats://test",
        stream_name="user_events",
        subject="user.created",
    )

    provider = FakeProvider()
    service.provider = provider

    message = FakeMessage(
        {
            "event_id": event_id,
            "event_type": "user.created",
            "user_id": 1001,
            "email": "retry@example.com",
            "created_at": created_at.isoformat(),
        }
    )

    asyncio.run(service._process_message(message))

    db.expire_all()

    notifications = db.query(Notification).all()

    assert len(notifications) == 1
    assert notifications[0].id == original_id
    assert notifications[0].event_id == event_id
    assert notifications[0].status == "processed"
    assert notifications[0].error_message is None
    assert notifications[0].processed_at is not None

    assert provider.calls == 1
    assert message.ack_count == 1

    db.close()


def test_processed_duplicate_is_acked_without_provider_call(monkeypatch):
    SessionTest = create_test_session_factory()

    monkeypatch.setattr(
        notification_service_module,
        "SessionLocal",
        SessionTest,
    )

    db = SessionTest()

    event_id = str(uuid.uuid4())
    created_at = datetime.now(timezone.utc)

    notification = Notification(
        event_id=event_id,
        user_id=1002,
        email="duplicate@example.com",
        status="processed",
        error_message=None,
        created_at=created_at,
        processed_at=created_at,
    )

    db.add(notification)
    db.commit()

    service = NotificationService(
        nats_url="nats://test",
        stream_name="user_events",
        subject="user.created",
    )

    provider = FakeProvider()
    service.provider = provider

    message = FakeMessage(
        {
            "event_id": event_id,
            "event_type": "user.created",
            "user_id": 1002,
            "email": "duplicate@example.com",
            "created_at": created_at.isoformat(),
        }
    )

    asyncio.run(service._process_message(message))

    assert provider.calls == 0
    assert message.ack_count == 1
    assert db.query(Notification).count() == 1

    db.close()