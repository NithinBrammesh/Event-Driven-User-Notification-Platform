from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes.health import router as health_router
from app.api.routes.users import router as users_router

app = FastAPI(title="API Gateway")


@app.exception_handler(Exception)
async def global_exception_handler(_, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(health_router)
app.include_router(users_router, prefix="/api")
