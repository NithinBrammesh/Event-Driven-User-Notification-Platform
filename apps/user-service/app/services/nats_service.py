import json
import logging
from typing import Any

from nats.aio.client import Client as NATSClient

from app.core.config import settings
from app.schemas.event import UserCreatedEvent

logger = logging.getLogger(__name__)


async def ensure_jetstream_stream(js) -> None:
    try:
        await js.stream_info(settings.nats_stream)
        return
    except Exception:
        pass

    await js.add_stream(
        name=settings.nats_stream,
        subjects=[settings.nats_subject],
    )


async def publish_user_event(
    event_type: str,
    user_data: dict[str, Any],
) -> bool:
    client = NATSClient()

    try:
        await client.connect(
            settings.nats_url,
            user=settings.nats_username or None,
            password=settings.nats_password or None,
            connect_timeout=5,
            reconnect_time_wait=1,
            max_reconnect_attempts=1,
        )

        js = client.jetstream()

        await ensure_jetstream_stream(js)

        payload = UserCreatedEvent.model_validate(
            {
                "event_id": user_data.get("event_id"),
                "event_type": event_type,
                "user_id": user_data.get("user_id"),
                "email": user_data.get("email"),
                "created_at": user_data.get("created_at"),
            }
        ).model_dump(mode="json")

        ack = await js.publish(
            settings.nats_subject,
            json.dumps(payload).encode("utf-8"),
        )

        logger.info(
            "Published %s event_id=%s stream=%s seq=%s",
            event_type,
            payload["event_id"],
            ack.stream,
            ack.seq,
        )

        return True

    except Exception:
        logger.exception(
            "Failed to publish %s event",
            event_type,
        )
        return False

    finally:
        try:
            await client.close()
        except Exception:
            pass
