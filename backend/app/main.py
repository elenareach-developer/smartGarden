from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import ai, plants, sensors, system
from .config import get_settings
from .database import Base, SessionLocal, engine
from .seed import seed_demo
from .services.plants import NotFound

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    if settings.seed_on_startup:
        with SessionLocal() as db:
            seed_demo(db)
    yield


app = FastAPI(
    title="Smart Orchid API",
    version="0.1.0",
    description=("Мониторинг, прогноз и уход за орхидеями. Измерения помечены источником "
                 "(demo / iot / manual), прогнозы и AI-гипотезы — отдельным типом данных."),
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=settings.cors_origin_list, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(NotFound)
async def not_found(_: Request, exc: NotFound):
    return JSONResponse(status_code=404, content={"detail": str(exc), "code": "not_found"})


@app.exception_handler(RequestValidationError)
async def validation(_: Request, exc: RequestValidationError):
    errors = [{"field": ".".join(str(x) for x in e["loc"][1:]), "message": e["msg"]} for e in exc.errors()]
    return JSONResponse(status_code=422, content={"detail": "Ошибка валидации данных", "code": "validation_error",
                                                  "errors": errors})


for r in (plants.router, ai.router, sensors.router, system.router):
    app.include_router(r)

settings.upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.upload_dir), name="uploads")
