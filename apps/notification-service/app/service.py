import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Any

from nats.aio.client import Client as NATSClient
from nats.js.api import AckPolicy, ConsumerConfig, DeliverPolicy
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.models.notification import Notification
from app.providers.mock_provider import MockNotificationProvider
from app.repositories.notification_repository import NotificationRepository
from app.schemas.event import UserCreatedEvent

logger = logging.getLogger(__name__)


class NotificationService:
    def __init__(
        self,
        nats_url: str,
        stream_name: str,
        subject: str,
        consumer_name: str = "notification-service",
        nats_username: str = "",
        nats_password: str = "",
    ):
        self.nats_url = nats_url
        self.stream_name = stream_name
        self.subject = subject
        self.consumer_name = consumer_name
        self.nats_username = nats_username
        self.nats_password = nats_password

        self._client: NATSClient | None = None
        self._consumer_task: asyncio.Task | None = None
        self._last_event: dict[str, Any] | None = None
        self._seen_event_ids: set[str] = set()

        self.provider = MockNotificationProvider()

    async def start(self) -> None:
        try:
            client = NATSClient()

            await client.connect(
                self.nats_url,
                user=self.nats_username or None,
                password=self.nats_password or None,
                connect_timeout=5,
                reconnect_time_wait=1,
                max_reconnect_attempts=1,
            )

            self._client = client

            js = self._client.jetstream()

            try:
                await js.stream_info(self.stream_name)
            except Exception:
                await js.add_stream(
                    name=self.stream_name,
                    subjects=[self.subject],
                )

            try:
                await js.consumer_info(
                    self.stream_name,
                    self.consumer_name,
                )
            except Exception:
                config = ConsumerConfig(
                    durable_name=self.consumer_name,
                    ack_policy=AckPolicy.EXPLICIT,
                    deliver_policy=DeliverPolicy.ALL,
                    filter_subject=self.subject,
                )

                await js.add_consumer(
                    self.stream_name,
                    config,
                )

            self._consumer_task = asyncio.create_task(
                self._consume_loop(js)
            )

        except Exception:
            logger.exception("Failed to start Notification Service")
            self._client = None
            self._consumer_task = None

    async def stop(self) -> None:
        if self._consumer_task is not None:
            self._consumer_task.cancel()

            try:
                await self._consumer_task
            except asyncio.CancelledError:
                pass

            self._consumer_task = None

        if self._client is not None:
            await self._client.close()
            self._client = None

    async def _consume_loop(self, js) -> None:
        try:
            sub = await js.pull_subscribe(
                self.subject,
                stream=self.stream_name,
                durable=self.consumer_name,
            )

            while True:
                try:
                    msgs = await sub.fetch(1, timeout=5)
                except TimeoutError:
                    continue

                for msg in msgs:
                    await self._process_message(msg)

        except asyncio.CancelledError:
            raise

        except Exception:
            logger.exception(
                "Notification consumer stopped unexpectedly"
            )

    async def _process_message(self, msg) -> None:
        try:
            payload = json.loads(
                msg.data.decode("utf-8")
            )

            event = UserCreatedEvent.model_validate(payload)

            if event.event_type != "user.created":
                logger.warning(
                    "Ignoring unsupported event type: %s",
                    event.event_type,
                )
                await msg.ack()
                return

            event_id = str(event.event_id)

            # Fast in-memory duplicate check.
            if event_id in self._seen_event_ids:
                await msg.ack()
                return

            db: Session = SessionLocal()

            try:
                repo = NotificationRepository(db)

                existing = repo.get_by_event_id(event_id)

                # Durable idempotency:
                # already successfully processed -> duplicate.
                if existing is not None and existing.status == "processed":
                    self._seen_event_ids.add(event_id)
                    await msg.ack()
                    return

                # If the event was previously failed/pending,
                # reuse the existing row instead of inserting
                # another row with the same unique event_id.
                if existing is not None:
                    notification = existing
                    notification.status = "pending"
                    notification.error_message = None
                    notification.processed_at = None
                    db.commit()

                else:
                    notification = Notification(
                        event_id=event_id,
                        user_id=event.user_id,
                        email=event.email,
                        status="pending",
                        error_message=None,
                        created_at=event.created_at,
                        processed_at=None,
                    )

                    repo.create(notification)

                try:
                    delivered = self.provider.send(
                        event.email,
                        "Welcome! Your account has been created.",
                    )

                    if not delivered:
                        notification.status = "failed"
                        notification.error_message = (
                            "Mock provider failed"
                        )
                        db.commit()

                        # Do NOT ACK.
                        # JetStream will redeliver the message.
                        return

                    notification.status = "processed"
                    notification.error_message = None
                    notification.processed_at = (
                        datetime.now(timezone.utc)
                    )

                    db.commit()

                    self._seen_event_ids.add(event_id)
                    self._last_event = payload

                    # ACK only after successful persistence.
                    await msg.ack()

                except Exception as exc:
                    notification.status = "failed"
                    notification.error_message = str(exc)
                    db.commit()

                    logger.exception(
                        "Notification provider failed for event %s",
                        event_id,
                    )

                    # Do NOT ACK.
                    # JetStream will redeliver the message.

            finally:
                db.close()

        except (json.JSONDecodeError, ValidationError) as exc:
            logger.error(
                "Invalid user.created event: %s",
                exc,
            )

            # Invalid/poison message should not be retried forever.
            await msg.ack()

        except Exception:
            logger.exception(
                "Failed to process notification message"
            )

    def is_duplicate_event(
        self,
        event_id: str | None,
    ) -> bool:
        return bool(
            event_id
            and event_id in self._seen_event_ids
        )

    @property
    def last_event(self) -> dict[str, Any] | None:
        return self._last_event