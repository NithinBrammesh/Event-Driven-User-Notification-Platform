import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "user-service"
    host: str = "0.0.0.0"
    port: int = 8001
    database_url: str = "postgresql+psycopg://postgres:change_me@postgres:5432/user_service_db"
    nats_url: str = "nats://nats:4222"
    nats_username: str = ""
    nats_password: str = ""
    nats_stream: str = "user_events"
    nats_subject: str = "user.created"
    nats_consumer_name: str = "notification-service"
    jwt_secret: str = "replace_with_secure_secret"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60


settings = Settings(
    app_name=os.getenv("APP_NAME", "user-service"),
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8001")),
    database_url=os.getenv("DATABASE_URL", "postgresql+psycopg://postgres:change_me@postgres:5432/user_service_db"),
    nats_url=os.getenv("NATS_URL", "nats://nats:4222"),
    nats_username=os.getenv("NATS_USERNAME", ""),
    nats_password=os.getenv("NATS_PASSWORD", ""),
    nats_stream=os.getenv("NATS_STREAM", "user_events"),
    nats_subject=os.getenv("NATS_SUBJECT", "user.created"),
    nats_consumer_name=os.getenv("NATS_CONSUMER_NAME", "notification-service"),
    jwt_secret=os.getenv("JWT_SECRET", "replace_with_secure_secret"),
    jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    jwt_expiration_minutes=int(os.getenv("JWT_EXPIRATION_MINUTES", "60")),
)
