"""IoTDataProvider — приём измерений от физических датчиков (ESP32 + DHT22/SHT31, BH1750, HX711 ...).

На этапе MVP физического подключения нет: устройство будет отправлять POST /api/sensors/readings
с source="iot" и sensor_id или hardware_id. Здесь — валидация и запись в общий формат SensorReading.
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.metrics import METRICS, DataSource, Metric
from ..models import Plant, Sensor, SensorReading
from .base import DataProvider


class IngestError(ValueError):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


class IoTDataProvider(DataProvider):
    source = DataSource.iot

    def sync(self, db: Session, plant: Plant, until: datetime) -> int:
        # Данные приходят push-методом от устройства, синхронизировать нечего.
        return 0

    def resolve_sensor(self, db: Session, plant_id: int, sensor_id: int | None,
                       hardware_id: str | None) -> Sensor:
        sensor = None
        if sensor_id is not None:
            sensor = db.get(Sensor, sensor_id)
        elif hardware_id:
            sensor = db.scalars(select(Sensor).where(Sensor.hardware_id == hardware_id)).first()
        if sensor is None:
            raise IngestError("Датчик не найден: зарегистрируйте его через POST /api/sensors", 404)
        if sensor.source != DataSource.iot.value:
            raise IngestError("Этот датчик не является IoT-датчиком")
        if sensor.plant_id != plant_id:
            raise IngestError("Датчик привязан к другому растению")
        if not sensor.is_active:
            raise IngestError("Датчик отключён")
        return sensor

    def ingest(self, db: Session, plant: Plant, sensor: Sensor, metric: Metric, value: float,
               timestamp: datetime | None, quality: str) -> SensorReading:
        if metric.value not in sensor.metrics:
            raise IngestError(f"Датчик {sensor.sensor_type} не измеряет {metric.value}")
        reading = SensorReading(
            sensor_id=sensor.id, plant_id=plant.id, metric=metric.value, value=value,
            unit=METRICS[metric].unit, timestamp=timestamp or datetime.now(timezone.utc),
            source=self.source.value, quality=quality,
        )
        db.add(reading)
        return reading
