import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..database import get_db
from ..models import AIConsultation, Fertilizer, FertilizerApplication, Plant, Sensor
from ..schemas import (
    CareEventIn, CareEventOut, CareOut, ConsultationOut, FertilizerOut, FertilizerRequest, FertilizerResult,
    FertilizersOut, ForecastOut, HistoryOut, MonitoringOut, PlantCard, PlantOut, PlantUpdate, SensorOut,
)
from ..services import fertilizer as fert_svc
from ..services.care import CareService
from ..services.forecast import ForecastService
from ..services.monitoring import MonitoringService
from ..services.plants import plant_card, plant_out, update_plant
from .deps import plant_dep

router = APIRouter(prefix="/api/plants", tags=["plants"])


@router.get("", response_model=list[PlantCard], summary="Коллекция орхидей (карточки)")
def list_plants(db: Session = Depends(get_db)):
    return [plant_card(db, p) for p in db.scalars(select(Plant).order_by(Plant.id))]


@router.get("/{plant_id}", response_model=PlantCard, summary="Профиль растения")
def get_plant(plant: Plant = Depends(plant_dep), db: Session = Depends(get_db)):
    return plant_card(db, plant)


@router.put("/{plant_id}", response_model=PlantOut, summary="Редактировать паспорт и условия")
def put_plant(data: PlantUpdate, plant: Plant = Depends(plant_dep), db: Session = Depends(get_db)):
    return plant_out(update_plant(db, plant, data))


ALLOWED_IMAGES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


@router.post("/{plant_id}/photo", response_model=PlantOut, summary="Загрузить фото растения")
async def upload_photo(file: UploadFile = File(...), plant: Plant = Depends(plant_dep), db: Session = Depends(get_db)):
    ext = ALLOWED_IMAGES.get(file.content_type or "")
    if not ext:
        raise HTTPException(415, "Поддерживаются JPEG, PNG и WebP")
    data = await file.read()
    if len(data) > 5 * 1024 * 1024:
        raise HTTPException(413, "Файл больше 5 МБ")
    d = get_settings().upload_dir
    d.mkdir(parents=True, exist_ok=True)
    name = f"plant{plant.id}-{uuid.uuid4().hex[:8]}{ext}"
    (d / name).write_bytes(data)
    plant.photo_url = f"/uploads/{name}"
    db.commit()
    return plant_out(plant)


@router.get("/{plant_id}/monitoring", response_model=MonitoringOut, summary="Текущее состояние")
def monitoring(plant: Plant = Depends(plant_dep), db: Session = Depends(get_db)):
    return MonitoringService(db).snapshot(plant)


@router.get("/{plant_id}/history", response_model=HistoryOut, summary="История измерений")
def history(period: Literal["24h", "7d", "30d"] = "24h",
            metrics: str | None = Query(None, description="через запятую: temperature,air_humidity,..."),
            plant: Plant = Depends(plant_dep), db: Session = Depends(get_db)):
    ms = [m.strip() for m in metrics.split(",")] if metrics else None
    return MonitoringService(db).history(plant, period, ms)


@router.get("/{plant_id}/forecast", response_model=ForecastOut, summary="Прогноз на 3/7/14 дней")
def forecast(horizon: int = Query(7, description="Горизонт: 3, 7 или 14 дней"),
             plant: Plant = Depends(plant_dep), db: Session = Depends(get_db)):
    if horizon not in (3, 7, 14):
        raise HTTPException(422, "horizon должен быть 3, 7 или 14")
    return ForecastService(db).build(plant, horizon)


@router.get("/{plant_id}/care", response_model=CareOut, summary="Журнал ухода и план")
def care(event_type: str | None = None, limit: int = Query(200, ge=1, le=1000),
         plant: Plant = Depends(plant_dep), db: Session = Depends(get_db)):
    return CareService(db).list(plant, limit, event_type)


@router.post("/{plant_id}/care", response_model=CareEventOut, status_code=201, summary="Добавить событие ухода")
def add_care(data: CareEventIn, plant: Plant = Depends(plant_dep), db: Session = Depends(get_db)):
    return CareService(db).add(plant, data)


@router.get("/{plant_id}/fertilizers", response_model=FertilizersOut, summary="Удобрения и история подкормок")
def fertilizers(plant: Plant = Depends(plant_dep), db: Session = Depends(get_db)):
    lib = list(db.scalars(select(Fertilizer).order_by(Fertilizer.id)))
    apps = list(db.scalars(select(FertilizerApplication).where(FertilizerApplication.plant_id == plant.id)
                           .order_by(FertilizerApplication.applied_at.desc())))
    return FertilizersOut(plant_id=plant.id, library=[FertilizerOut.model_validate(f) for f in lib],
                          applications=[fert_svc.application_out(a) for a in apps],
                          last_fertilized_at=apps[0].applied_at if apps else None,
                          next_window=fert_svc.next_window(db, plant, datetime.now(timezone.utc)))


@router.post("/{plant_id}/fertilizers", response_model=FertilizerResult, status_code=201,
             summary="Fertilizer Advisor: оценить удобрение и (опционально) записать подкормку")
def add_fertilizer(req: FertilizerRequest, plant: Plant = Depends(plant_dep), db: Session = Depends(get_db)):
    try:
        fert = fert_svc.get_or_create(db, req.fertilizer_id, req.fertilizer)
    except LookupError as e:
        raise HTTPException(404, str(e))
    assessment = fert_svc.assess(db, plant, fert, req.stage.value if req.stage else None, req.last_fertilized_at)
    application = None
    if req.record_application:
        application = fert_svc.record(db, plant, fert, req.applied_at, req.dilution, req.notes,
                                      req.stage.value if req.stage else plant.stage)
    db.commit()
    return FertilizerResult(fertilizer=FertilizerOut.model_validate(fert), assessment=assessment,
                            application=fert_svc.application_out(application) if application else None)


@router.get("/{plant_id}/consultations", response_model=list[ConsultationOut], summary="История консультаций AI")
def consultations(plant: Plant = Depends(plant_dep), db: Session = Depends(get_db)):
    return list(db.scalars(select(AIConsultation).where(AIConsultation.plant_id == plant.id)
                           .order_by(AIConsultation.created_at.desc()).limit(50)))


@router.get("/{plant_id}/sensors", response_model=list[SensorOut], summary="Датчики растения")
def plant_sensors(plant: Plant = Depends(plant_dep), db: Session = Depends(get_db)):
    return list(db.scalars(select(Sensor).where(Sensor.plant_id == plant.id).order_by(Sensor.id)))
