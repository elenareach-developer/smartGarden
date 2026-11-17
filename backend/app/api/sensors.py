from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..database import get_db
from ..domain.metrics import METRICS, SENSOR_METRICS, SensorType
from ..models import Sensor, SensorReading
from ..providers.iot import IngestError
from ..providers.registry import iot_provider
from ..schemas import ReadingIn, ReadingOut, ReadingsBatchIn, ReadingsBatchOut, SensorIn, SensorOut
from ..services.plants import get_plant

router = APIRouter(prefix="/api/sensors", tags=["sensors"])


@router.get("", response_model=list[SensorOut], summary="Список датчиков")
def list_sensors(plant_id: int | None = None, db: Session = Depends(get_db)):
    q = select(Sensor).order_by(Sensor.id)
    if plant_id is not None:
        q = q.where(Sensor.plant_id == plant_id)
    return list(db.scalars(q))


@router.post("", response_model=SensorOut, status_code=201, summary="Зарегистрировать IoT-датчик")
def register(data: SensorIn, db: Session = Depends(get_db)):
    get_plant(db, data.plant_id)
    if data.sensor_type in (SensorType.DEMO_VIRTUAL, SensorType.MANUAL):
        raise HTTPException(422, "Этот тип нельзя зарегистрировать как IoT-датчик")
    metrics = [m.value for m in (data.metrics or SENSOR_METRICS.get(data.sensor_type, []))]
    if not metrics:
        raise HTTPException(422, "Укажите metrics для датчика этого типа")
    if data.hardware_id and db.scalars(select(Sensor).where(Sensor.hardware_id == data.hardware_id)).first():
        raise HTTPException(409, "Датчик с таким hardware_id уже зарегистрирован")
    s = Sensor(plant_id=data.plant_id, name=data.name, sensor_type=data.sensor_type.value, metrics=metrics,
               source="iot", hardware_id=data.hardware_id)
    db.add(s)
    db.commit()
    return s


def _to_out(r: SensorReading) -> ReadingOut:
    return ReadingOut(id=r.id, plant_id=r.plant_id, sensor_id=r.sensor_id, metric=r.metric, value=r.value,
                      unit=r.unit, timestamp=r.timestamp, source=r.source, quality=r.quality)


@router.post("/readings", response_model=ReadingsBatchOut, status_code=201,
             summary="Принять измерения: ручной ввод (source=manual) или ESP32 (source=iot)")
def post_readings(body: ReadingIn | ReadingsBatchIn, db: Session = Depends(get_db)):
    items = body.readings if isinstance(body, ReadingsBatchIn) else [body]
    saved: list[SensorReading] = []
    now = datetime.now(timezone.utc)
    for i, r in enumerate(items):
        where = f"readings[{i}]: " if len(items) > 1 else ""
        plant = get_plant(db, r.plant_id)
        info = METRICS[r.metric]
        if r.unit and r.unit != info.unit:
            raise HTTPException(422, f"{where}единица для {r.metric.value} должна быть {info.unit}")
        if not info.valid_min <= r.value <= info.valid_max:
            raise HTTPException(422, f"{where}значение {r.value} вне допустимого диапазона "
                                     f"{info.valid_min}…{info.valid_max} {info.unit}")
        if r.timestamp and r.timestamp > now + timedelta(minutes=5):
            raise HTTPException(422, f"{where}время измерения в будущем")
        if r.source == "iot":
            try:
                sensor = iot_provider().resolve_sensor(db, plant.id, r.sensor_id, r.hardware_id)
                saved.append(iot_provider().ingest(db, plant, sensor, r.metric, r.value, r.timestamp, r.quality.value))
            except IngestError as e:
                db.rollback()
                raise HTTPException(e.status_code, f"{where}{e}")
        else:
            manual = db.scalars(select(Sensor).where(Sensor.plant_id == plant.id, Sensor.source == "manual")).first()
            if manual is None:
                manual = Sensor(plant_id=plant.id, name="Ручной ввод", sensor_type="MANUAL", source="manual", metrics=[])
                db.add(manual)
                db.flush()
            rec = SensorReading(sensor_id=manual.id, plant_id=plant.id, metric=r.metric.value, value=r.value,
                                unit=info.unit, timestamp=r.timestamp or now, source="manual",
                                quality=r.quality.value)
            db.add(rec)
            saved.append(rec)
    db.commit()
    return ReadingsBatchOut(accepted=len(saved), readings=[_to_out(r) for r in saved])
