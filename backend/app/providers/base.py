"""Абстракция источника измерений.

Сервисы мониторинга и прогноза работают только через этот интерфейс и не знают,
откуда пришли данные: из генератора DEMO или с ESP32. Каждый провайдер читает и пишет
только измерения своего источника, поэтому DEMO и реальные данные никогда не смешиваются.
"""
from abc import ABC, abstractmethod
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.metrics import DataSource, Metric
from ..models import Plant, Sensor, SensorReading


class DataProvider(ABC):
    source: DataSource

    @abstractmethod
    def sync(self, db: Session, plant: Plant, until: datetime) -> int:
        """Обновить данные до момента until. Возвращает число новых измерений."""

    def sensors(self, db: Session, plant: Plant) -> list[Sensor]:
        return list(db.scalars(select(Sensor).where(
            Sensor.plant_id == plant.id, Sensor.source == self.source.value, Sensor.is_active.is_(True))))

    def available_metrics(self, db: Session, plant: Plant) -> set[Metric]:
        out: set[Metric] = set()
        for s in self.sensors(db, plant):
            out.update(Metric(m) for m in s.metrics)
        return out

    def latest(self, db: Session, plant: Plant, metric: Metric) -> SensorReading | None:
        return db.scalars(
            select(SensorReading)
            .where(SensorReading.plant_id == plant.id, SensorReading.metric == metric.value,
                   SensorReading.source == self.source.value)
            .order_by(SensorReading.timestamp.desc()).limit(1)
        ).first()

    def series(self, db: Session, plant: Plant, metric: Metric, start: datetime,
               end: datetime) -> list[SensorReading]:
        return list(db.scalars(
            select(SensorReading)
            .where(SensorReading.plant_id == plant.id, SensorReading.metric == metric.value,
                   SensorReading.source == self.source.value,
                   SensorReading.timestamp >= start, SensorReading.timestamp <= end)
            .order_by(SensorReading.timestamp)
        ))


class ManualReadings(DataProvider):
    """Ручные измерения пользователя — отдельный источник, только чтение/запись в БД."""

    source = DataSource.manual

    def sync(self, db, plant, until) -> int:
        return 0

    def available_metrics(self, db, plant) -> set[Metric]:
        return set(Metric)
