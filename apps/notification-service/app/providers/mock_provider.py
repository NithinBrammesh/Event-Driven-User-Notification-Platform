import logging
import os

logger = logging.getLogger(__name__)


class MockNotificationProvider:
    def __init__(self):
        self.fail_once = os.getenv("MOCK_PROVIDER_FAIL_ONCE", "false").lower() == "true"
        self._failed = False

    def send(self, email: str, message: str) -> bool:
        if self.fail_once and not self._failed:
            self._failed = True
            logger.warning(
                "MOCK PROVIDER: intentional failure for retry test, email=%s",
                email,
            )
            return False

        logger.info(
            "MOCK NOTIFICATION: email=%s message=%s",
            email,
            message,
        )
        return True