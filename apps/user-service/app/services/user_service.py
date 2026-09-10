import asyncio
import inspect
import logging
import uuid
from datetime import datetime, timezone

from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.schemas.user import UserCreate, UserLogin, UserOut
from app.services.auth_service import create_token
from app.services.nats_service import publish_user_event

logger = logging.getLogger(__name__)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class UserService:
    def __init__(self, db: Session):
        self.repo = UserRepository(db)
        self.db = db

    def register_user(self, payload: UserCreate) -> UserOut:
        if self.repo.get_by_email(payload.email):
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already exists")

        user = User(
            email=str(payload.email),
            full_name=payload.full_name,
            password_hash=pwd_context.hash(payload.password),
            is_active=True,
        )
        created = self.repo.create(user)
        event_payload = {
            "event_id": str(uuid.uuid4()),
            "event_type": "user.created",
            "user_id": created.id,
            "email": created.email,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            result = publish_user_event("user.created", event_payload)
            if inspect.isawaitable(result):
                result = asyncio.run(result)
            if result is False:
                logger.warning("User registration succeeded but user.created event was not published")
        except Exception:
            logger.warning("User registration succeeded but NATS publish failed", exc_info=True)
        return UserOut.model_validate(created)

    def login_user(self, payload: UserLogin) -> dict:
        user = self.repo.get_by_email(str(payload.email))
        if not user or not pwd_context.verify(payload.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        token = create_token(str(user.id))
        return {"access_token": token, "token_type": "bearer"}

    def get_user_by_id(self, user_id: int) -> UserOut:
        user = self.repo.get_by_id(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        return UserOut.model_validate(user)
