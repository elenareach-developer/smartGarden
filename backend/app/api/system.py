from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import Plant, SensorReading
from ..schemas import DashboardOut
from ..seed import reset_demo
from ..services.dashboard import summary

router = APIRouter(prefix="/api", tags=["system"])


@router.get("/dashboard/summary", response_model=DashboardOut, summary="Сводка по коллекции")
def dashboard(db: Session = Depends(get_db)):
    return summary(db)


@router.get("/health", summary="Проверка работоспособности")
def health():
    return {"status": "ok"}


@router.get("/system/status", summary="Конфигурация и источники данных")
def system_status(db: Session = Depends(get_db)):
    s = get_settings()
    counts = dict(db.execute(select(SensorReading.source, func.count()).group_by(SensorReading.source)).all())
    return {
        "app": s.app_name,
        "database": s.database_url.split("://")[0],
        "ai_mode": s.effective_ai_mode,
        "ai_configured_mode": s.ai_mode,
        "claude_model": s.claude_model,
        "api_key_configured": bool(s.anthropic_api_key),
        "plants": db.scalar(select(func.count(Plant.id))),
        "readings_by_source": counts,
        "providers": ["DemoDataProvider", "IoTDataProvider"],
    }


@router.post("/system/reset-demo", summary="Пересоздать демонстрационные данные")
def reset(db: Session = Depends(get_db)):
    reset_demo(db)
    return {"status": "reset"}
