import os

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "api-gateway"
    host: str = "0.0.0.0"
    port: int = 8000
    user_service_url: str = "http://user-service:8001"
    notification_service_url: str = "http://notification-service:8002"
    jwt_secret: str = "replace_with_secure_secret"
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = 60


settings = Settings(
    app_name=os.getenv("APP_NAME", "api-gateway"),
    host=os.getenv("HOST", "0.0.0.0"),
    port=int(os.getenv("PORT", "8000")),
    user_service_url=os.getenv("USER_SERVICE_URL", "http://user-service:8001"),
    notification_service_url=os.getenv("NOTIFICATION_SERVICE_URL", "http://notification-service:8002"),
    jwt_secret=os.getenv("JWT_SECRET", "replace_with_secure_secret"),
    jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
    jwt_expiration_minutes=int(os.getenv("JWT_EXPIRATION_MINUTES", "60")),
)
