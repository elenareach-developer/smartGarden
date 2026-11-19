"""ORM-модели. Паспорт растения (Plant) хранится отдельно от истории наблюдений
(SensorReading, CareEvent, FertilizerApplication, Forecast, AIConsultation)."""
from datetime import datetime

from sqlalchemy import JSON, Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base, UTCDateTime, utcnow


class Plant(Base):
    __tablename__ = "plants"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(60))
    species: Mapped[str] = mapped_column(String(120))          # род/вид
    variety: Mapped[str | None] = mapped_column(String(120))   # сорт/гибрид
    photo_url: Mapped[str | None] = mapped_column(String(500))
    stage: Mapped[str] = mapped_column(String(20))
    location: Mapped[str | None] = mapped_column(String(200))
    pot: Mapped[str | None] = mapped_column(String(200))
    substrate: Mapped[str | None] = mapped_column(String(200))
    notes: Mapped[str | None] = mapped_column(Text)
    acquired_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # Последние результаты осмотра (качественные наблюдения пользователя)
    root_status: Mapped[str] = mapped_column(String(20), default="unknown")
    leaf_status: Mapped[str] = mapped_column(String(20), default="unknown")
    observed_at: Mapped[datetime | None] = mapped_column(UTCDateTime)

    # Индивидуальные целевые условия
    temp_min: Mapped[float] = mapped_column(Float)
    temp_max: Mapped[float] = mapped_column(Float)
    humidity_min: Mapped[float] = mapped_column(Float)
    humidity_max: Mapped[float] = mapped_column(Float)
    light_min: Mapped[float] = mapped_column(Float)   # средняя дневная освещённость, lx
    light_max: Mapped[float] = mapped_column(Float)
    photoperiod_min: Mapped[float] = mapped_column(Float)
    photoperiod_max: Mapped[float] = mapped_column(Float)
    substrate_min: Mapped[float] = mapped_column(Float, default=25)
    substrate_max: Mapped[float] = mapped_column(Float, default=80)
    pot_weight_dry: Mapped[float | None] = mapped_column(Float)   # масса сухого горшка, г
    pot_weight_wet: Mapped[float | None] = mapped_column(Float)   # сразу после полива, г
    watering_interval_days: Mapped[float] = mapped_column(Float, default=7)
    fertilizing_interval_days: Mapped[float] = mapped_column(Float, default=14)

    data_source: Mapped[str] = mapped_column(String(10), default="demo")  # demo | iot
    demo_profile: Mapped[dict | None] = mapped_column(JSON)  # параметры генератора DEMO

    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, onupdate=utcnow)

    sensors: Mapped[list["Sensor"]] = relationship(back_populates="plant", cascade="all, delete-orphan")
    care_events: Mapped[list["CareEvent"]] = relationship(back_populates="plant", cascade="all, delete-orphan")


class Sensor(Base):
    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(primary_key=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(80))
    sensor_type: Mapped[str] = mapped_column(String(30))
    metrics: Mapped[list[str]] = mapped_column(JSON)   # какие показатели измеряет
    source: Mapped[str] = mapped_column(String(10))    # demo | iot | manual
    hardware_id: Mapped[str | None] = mapped_column(String(80), unique=True)  # напр. MAC ESP32 + канал
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    plant: Mapped[Plant] = relationship(back_populates="sensors")


class SensorReading(Base):
    __tablename__ = "sensor_readings"
    __table_args__ = (Index("ix_readings_plant_metric_source_ts", "plant_id", "metric", "source", "timestamp"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    sensor_id: Mapped[int | None] = mapped_column(ForeignKey("sensors.id", ondelete="SET NULL"))
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id", ondelete="CASCADE"))
    metric: Mapped[str] = mapped_column(String(30))
    value: Mapped[float] = mapped_column(Float)
    unit: Mapped[str] = mapped_column(String(10))
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime)
    source: Mapped[str] = mapped_column(String(10))      # demo | iot | manual
    quality: Mapped[str] = mapped_column(String(10), default="ok")  # ok | suspect | error


class CareEvent(Base):
    __tablename__ = "care_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id", ondelete="CASCADE"), index=True)
    event_type: Mapped[str] = mapped_column(String(20))
    timestamp: Mapped[datetime] = mapped_column(UTCDateTime, index=True)
    amount_ml: Mapped[float | None] = mapped_column(Float)
    method: Mapped[str | None] = mapped_column(String(80))   # погружение, полив сверху...
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(10), default="user")  # demo | user
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)

    plant: Mapped[Plant] = relationship(back_populates="care_events")


class Fertilizer(Base):
    """Удобрение из библиотеки пользователя. Состав вносит пользователь — система его не придумывает."""

    __tablename__ = "fertilizers"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    manufacturer: Mapped[str | None] = mapped_column(String(120))
    npk_n: Mapped[float | None] = mapped_column(Float)
    npk_p: Mapped[float | None] = mapped_column(Float)
    npk_k: Mapped[float | None] = mapped_column(Float)
    micronutrients: Mapped[str | None] = mapped_column(String(300))
    concentration: Mapped[str | None] = mapped_column(String(200))   # как указано на этикетке
    form: Mapped[str | None] = mapped_column(String(40))             # жидкое, порошок, палочки...
    labeled_for_orchids: Mapped[bool | None] = mapped_column(Boolean)
    manufacturer_instructions: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class FertilizerApplication(Base):
    __tablename__ = "fertilizer_applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id", ondelete="CASCADE"), index=True)
    fertilizer_id: Mapped[int] = mapped_column(ForeignKey("fertilizers.id", ondelete="RESTRICT"))
    care_event_id: Mapped[int | None] = mapped_column(ForeignKey("care_events.id", ondelete="SET NULL"))
    applied_at: Mapped[datetime] = mapped_column(UTCDateTime)
    dilution: Mapped[str | None] = mapped_column(String(200))   # фактическое разведение со слов пользователя
    stage_at_application: Mapped[str] = mapped_column(String(20))
    notes: Mapped[str | None] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(10), default="user")

    fertilizer: Mapped[Fertilizer] = relationship()


class Forecast(Base):
    """Сохранённый прогноз (снимок расчёта) — для истории и сравнения с фактом."""

    __tablename__ = "forecasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id", ondelete="CASCADE"), index=True)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)
    horizon_days: Mapped[int] = mapped_column(Integer)
    method: Mapped[str] = mapped_column(String(80))
    data_source: Mapped[str] = mapped_column(String(10))
    payload: Mapped[dict] = mapped_column(JSON)


class AIConsultation(Base):
    __tablename__ = "ai_consultations"

    id: Mapped[int] = mapped_column(primary_key=True)
    plant_id: Mapped[int] = mapped_column(ForeignKey("plants.id", ondelete="CASCADE"), index=True)
    topic: Mapped[str] = mapped_column(String(30))
    question: Mapped[str] = mapped_column(Text)
    answer: Mapped[str] = mapped_column(Text)
    mode: Mapped[str] = mapped_column(String(10))   # demo | claude
    model: Mapped[str | None] = mapped_column(String(60))
    context_snapshot: Mapped[dict] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow)


class SpyInvestigation(Base):
    """Botanical Spy: расследование по фотографии. Растение необязательно (фото может быть «чужим»)."""

    __tablename__ = "spy_investigations"

    id: Mapped[int] = mapped_column(primary_key=True)
    plant_id: Mapped[int | None] = mapped_column(ForeignKey("plants.id", ondelete="SET NULL"), index=True)
    photo_url: Mapped[str | None] = mapped_column(String(500))
    photo_source: Mapped[str] = mapped_column(String(20))   # upload | collection | illustration | none
    codename: Mapped[str] = mapped_column(String(160))
    mode: Mapped[str] = mapped_column(String(10))           # demo | claude
    model: Mapped[str | None] = mapped_column(String(60))
    result: Mapped[dict] = mapped_column(JSON)              # досье: факты, гипотезы, неизвестное
    crosscheck: Mapped[list] = mapped_column(JSON)          # сверка с реальными датчиками
    image_stats: Mapped[dict | None] = mapped_column(JSON)  # измерения по пикселям
    context_snapshot: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(UTCDateTime, default=utcnow, index=True)
