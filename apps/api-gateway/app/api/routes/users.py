from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

import httpx

from app.auth.dependencies import get_current_user
from app.core.config import settings

router = APIRouter()


async def proxy_to_user_service(method: str, path: str, payload: dict[str, Any] | None = None, token: str | None = None) -> tuple[dict[str, Any], int]:
    headers: dict[str, str] = {}
    if payload is not None:
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.request(
                method=method,
                url=f"{settings.user_service_url}{path}",
                json=payload,
                headers=headers,
                timeout=30,
            )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="User Service unavailable") from exc

    try:
        body = response.json()
    except ValueError:
        body = {"detail": response.text}

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=body.get("detail", body))
    return body, response.status_code


@router.get("/internal/user-service/health")
async def get_user_service_health() -> dict:
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{settings.user_service_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=503, detail="User Service unavailable") from exc


@router.post("/users")
async def register_user(payload: dict[str, Any]) -> JSONResponse:
    body, status_code = await proxy_to_user_service("POST", "/users", payload=payload)
    return JSONResponse(content=body, status_code=status_code)


@router.post("/users/login")
async def login_user(payload: dict[str, Any]) -> JSONResponse:
    body, status_code = await proxy_to_user_service("POST", "/users/login", payload=payload)
    return JSONResponse(content=body, status_code=status_code)


@router.get("/users/me")
def get_current_user_profile(user: dict = Depends(get_current_user)) -> dict:
    return {"user": user}


@router.get("/users/{user_id}")
async def get_user_by_id(
    user_id: int,
    user: dict = Depends(get_current_user),
) -> JSONResponse:
    body, status_code = await proxy_to_user_service("GET", f"/users/{user_id}")
    return JSONResponse(content=body, status_code=status_code)
