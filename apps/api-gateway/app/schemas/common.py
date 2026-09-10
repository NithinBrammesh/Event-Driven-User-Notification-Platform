from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = Field(default="ok")
    service: str = Field(default="api-gateway")


class ErrorResponse(BaseModel):
    detail: str
