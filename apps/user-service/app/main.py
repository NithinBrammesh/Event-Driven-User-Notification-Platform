from fastapi import FastAPI
from fastapi.responses import JSONResponse

from app.api.routes.users import router as users_router
from app.db.session import Base, engine

app = FastAPI(title="User Service")


@app.on_event("startup")
def startup_event() -> None:
    Base.metadata.create_all(bind=engine)


@app.exception_handler(Exception)
async def global_exception_handler(_, exc):
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(users_router)
