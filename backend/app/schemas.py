"""Pydantic-схемы API: валидация входа и форма ответов."""
from datetime import datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .domain.metrics import (
    CareType, DataSource, LeafStatus, Metric, ReadingQuality, RootStatus, SensorType, Stage,
)

DataKind = Literal["measured", "derived", "forecast", "hypothesis", "observation"]
Status = Literal["ok", "low", "high", "no_data", "stale", "night"]
Attention = Literal["ok", "attention", "critical"]


class ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


def _aware(v: datetime | None) -> datetime | None:
    if v is not None and v.tzinfo is None:
        return v.replace(tzinfo=timezone.utc)
    return v


# ---------- Plant ----------

class Targets(BaseModel):
    temp_min: float = Field(ge=-5, le=45)
    temp_max: float = Field(ge=-5, le=45)
    humidity_min: float = Field(ge=0, le=100)
    humidity_max: float = Field(ge=0, le=100)
    light_min: float = Field(ge=0, le=150_000)
    light_max: float = Field(ge=0, le=150_000)
    photoperiod_min: float = Field(ge=0, le=24)
    photoperiod_max: float = Field(ge=0, le=24)
    substrate_min: float = Field(ge=0, le=100)
    substrate_max: float = Field(ge=0, le=100)
    pot_weight_dry: float | None = Field(default=None, ge=0, le=50_000)
    pot_weight_wet: float | None = Field(default=None, ge=0, le=50_000)
    watering_interval_days: float = Field(ge=1, le=60)
    fertilizing_interval_days: float = Field(ge=3, le=120)


class PlantOut(ORM):
    id: int
    name: str
    species: str
    variety: str | None
    photo_url: str | None
    stage: Stage
    stage_label: str
    location: str | None
    pot: str | None
    substrate: str | None
    notes: str | None
    acquired_at: datetime | None
    root_status: RootStatus
    root_label: str
    leaf_status: LeafStatus
    leaf_label: str
    observed_at: datetime | None
    data_source: Literal["demo", "iot"]
    targets: Targets
    created_at: datetime
    updated_at: datetime


class PlantCard(BaseModel):
    plant: PlantOut
    summary: str
    attention: Attention
    attention_reasons: list[str]
    last_watering: datetime | None
    last_fertilizing: datetime | None
    sensors: list[str]


class PlantUpdate(BaseModel):
    """Частичное обновление паспорта и условий растения."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, min_length=1, max_length=60)
    species: str | None = Field(default=None, min_length=1, max_length=120)
    variety: str | None = Field(default=None, max_length=120)
    photo_url: str | None = Field(default=None, max_length=500)
    stage: Stage | None = None
    location: str | None = Field(default=None, max_length=200)
    pot: str | None = Field(default=None, max_length=200)
    substrate: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=4000)
    root_status: RootStatus | None = None
    leaf_status: LeafStatus | None = None
    data_source: Literal["demo", "iot"] | None = None
    targets: Targets | None = None

    @model_validator(mode="after")
    def _ranges(self):
        t = self.targets
        if t:
            for lo, hi in [("temp_min", "temp_max"), ("humidity_min", "humidity_max"),
                           ("light_min", "light_max"), ("photoperiod_min", "photoperiod_max"),
                           ("substrate_min", "substrate_max")]:
                if getattr(t, lo) > getattr(t, hi):
                    raise ValueError(f"{lo} не может быть больше {hi}")
        return self


# ---------- Monitoring ----------

class Reading(BaseModel):
    value: float
    unit: str
    timestamp: datetime
    source: DataSource
    quality: ReadingQuality


class MetricState(BaseModel):
    metric: str
    label: str
    unit: str
    kind: DataKind
    available: bool
    current: Reading | None
    manual_latest: Reading | None = None
    target_min: float | None
    target_max: float | None
    status: Status
    status_text: str
    note: str | None = None
    sparkline: list[float] = []


class Observation(BaseModel):
    key: Literal["root_status", "leaf_status"]
    label: str
    value: str
    value_label: str
    kind: DataKind = "observation"
    observed_at: datetime | None
    status: Literal["ok", "attention", "critical", "unknown"]


class MonitoringOut(BaseModel):
    plant_id: int
    data_source: Literal["demo", "iot"]
    is_demo: bool
    generated_at: datetime
    metrics: list[MetricState]
    observations: list[Observation]
    attention: Attention
    attention_reasons: list[str]


class HistoryPoint(BaseModel):
    t: datetime
    value: float
    min: float | None = None
    max: float | None = None


class HistorySeries(BaseModel):
    metric: str
    label: str
    unit: str
    kind: DataKind
    source: str
    bucket_minutes: int
    target_min: float | None
    target_max: float | None
    points: list[HistoryPoint]
    stats: dict[str, float | None]


class HistoryOut(BaseModel):
    plant_id: int
    period: Literal["24h", "7d", "30d"]
    start: datetime
    end: datetime
    series: list[HistorySeries]
    manual: list[HistorySeries]


# ---------- Forecast ----------

class ForecastPoint(BaseModel):
    t: datetime
    value: float
    low: float
    high: float


class MetricForecast(BaseModel):
    metric: str
    label: str
    unit: str
    kind: DataKind = "forecast"
    method: str
    trend_per_day: float | None
    current_mean: float | None
    expected_mean: float | None
    points: list[ForecastPoint]
    history: list[HistoryPoint]
    confidence: float | None
    confidence_label: str
    explanation: str


class WateringForecast(BaseModel):
    kind: DataKind = "forecast"
    next_check_at: datetime | None
    method: str
    based_on: str
    confidence: float | None
    confidence_label: str
    explanation: str


class Risk(BaseModel):
    code: str
    title: str
    level: Literal["low", "medium", "high"]
    kind: DataKind
    explanation: str
    based_on: list[str]
    suggestion: str


class Dynamics(BaseModel):
    kind: DataKind = "hypothesis"
    trajectory: Literal["improving", "stable", "declining", "uncertain"]
    title: str
    explanation: str
    factors: list[str]


class ForecastOut(BaseModel):
    plant_id: int
    horizon_days: Literal[3, 7, 14]
    generated_at: datetime
    data_source: str
    is_demo: bool
    method_summary: str
    metrics: list[MetricForecast]
    derived: list[dict]
    watering: WateringForecast
    risks: list[Risk]
    dynamics: Dynamics
    disclaimer: str
    forecast_id: int | None = None


# ---------- Care ----------

class CareEventIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: CareType
    timestamp: datetime | None = None
    amount_ml: float | None = Field(default=None, ge=0, le=5000)
    method: str | None = Field(default=None, max_length=80)
    notes: str | None = Field(default=None, max_length=2000)
    # для осмотра можно сразу обновить наблюдения
    root_status: RootStatus | None = None
    leaf_status: LeafStatus | None = None

    @field_validator("timestamp")
    @classmethod
    def _not_future(cls, v):
        v = _aware(v)
        if v and v > datetime.now(timezone.utc).replace(microsecond=0) + timedelta(minutes=5):
            raise ValueError("Дата события не может быть в будущем")
        return v

    @model_validator(mode="after")
    def _check(self):
        if self.event_type == CareType.fertilizing:
            raise ValueError("Подкормку вносите через /fertilizers — так сохраняется состав удобрения")
        if self.event_type != CareType.inspection and (self.root_status or self.leaf_status):
            raise ValueError("root_status/leaf_status допустимы только для осмотра (inspection)")
        return self


class CareEventOut(ORM):
    id: int
    plant_id: int
    event_type: CareType
    event_label: str
    timestamp: datetime
    amount_ml: float | None
    method: str | None
    notes: str | None
    source: str


class PlannedTask(BaseModel):
    task: str
    title: str
    due_at: datetime | None
    kind: DataKind
    explanation: str


class CareOut(BaseModel):
    plant_id: int
    events: list[CareEventOut]
    planned: list[PlannedTask]


# ---------- Fertilizers ----------

class FertilizerIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=120)
    manufacturer: str | None = Field(default=None, max_length=120)
    npk_n: float | None = Field(default=None, ge=0, le=100)
    npk_p: float | None = Field(default=None, ge=0, le=100)
    npk_k: float | None = Field(default=None, ge=0, le=100)
    micronutrients: str | None = Field(default=None, max_length=300)
    concentration: str | None = Field(default=None, max_length=200)
    form: str | None = Field(default=None, max_length=40)
    labeled_for_orchids: bool | None = None
    manufacturer_instructions: str | None = Field(default=None, max_length=4000)


class FertilizerOut(ORM):
    id: int
    name: str
    manufacturer: str | None
    npk_n: float | None
    npk_p: float | None
    npk_k: float | None
    micronutrients: str | None
    concentration: str | None
    form: str | None
    labeled_for_orchids: bool | None
    manufacturer_instructions: str | None


class FertilizerRequest(BaseModel):
    """Оценить удобрение и (по желанию пользователя) записать факт подкормки."""

    model_config = ConfigDict(extra="forbid")

    fertilizer_id: int | None = None
    fertilizer: FertilizerIn | None = None
    stage: Stage | None = None                   # если отличается от текущей
    last_fertilized_at: datetime | None = None   # если пользователь знает точнее, чем журнал
    record_application: bool = False
    applied_at: datetime | None = None
    dilution: str | None = Field(default=None, max_length=200)
    notes: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def _one(self):
        if (self.fertilizer_id is None) == (self.fertilizer is None):
            raise ValueError("Укажите либо fertilizer_id, либо данные нового удобрения fertilizer")
        self.last_fertilized_at = _aware(self.last_fertilized_at)
        self.applied_at = _aware(self.applied_at)
        return self


class Assessment(BaseModel):
    kind: DataKind = "derived"
    verdict: Literal["suitable", "conditional", "not_now", "insufficient_data"]
    verdict_label: str
    composition_type: str | None
    reasons: list[str]
    when_to_use: str
    precautions: list[str]
    blockers: list[str]
    questions: list[str]
    data_used: list[str]


class ApplicationOut(BaseModel):
    id: int
    fertilizer: FertilizerOut
    applied_at: datetime
    dilution: str | None
    stage_at_application: str
    notes: str | None
    source: str


class FertilizerResult(BaseModel):
    fertilizer: FertilizerOut
    assessment: Assessment
    application: ApplicationOut | None


class FertilizersOut(BaseModel):
    plant_id: int
    library: list[FertilizerOut]
    applications: list[ApplicationOut]
    last_fertilized_at: datetime | None
    next_window: PlannedTask | None


# ---------- AI ----------

Topic = Literal["feeding", "watering", "yellow_leaves", "no_bloom", "roots", "disease",
                "conditions", "fertilizer", "general"]


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ConsultIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_id: int
    topic: Topic = "general"
    question: str = Field(min_length=1, max_length=4000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)
    fertilizer_id: int | None = None
    force_demo: bool = False


class ConsultOut(BaseModel):
    consultation_id: int
    plant_id: int
    topic: Topic
    mode: Literal["demo", "claude"]
    model: str | None
    answer: str
    clarifying_questions: list[str]
    data_used: list[str]
    missing_data: list[str]
    warnings: list[str]
    created_at: datetime


class ConsultationOut(ORM):
    id: int
    plant_id: int
    topic: str
    question: str
    answer: str
    mode: str
    model: str | None
    created_at: datetime


# ---------- Sensors ----------

class SensorIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_id: int
    name: str = Field(min_length=1, max_length=80)
    sensor_type: SensorType
    hardware_id: str | None = Field(default=None, max_length=80)
    metrics: list[Metric] | None = None


class SensorOut(ORM):
    id: int
    plant_id: int
    name: str
    sensor_type: str
    metrics: list[str]
    source: str
    hardware_id: str | None
    is_active: bool


class ReadingIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_id: int
    metric: Metric
    value: float
    unit: str | None = None
    timestamp: datetime | None = None
    sensor_id: int | None = None
    hardware_id: str | None = None
    source: Literal["iot", "manual"] = "manual"
    quality: ReadingQuality = ReadingQuality.ok

    @field_validator("timestamp")
    @classmethod
    def _tz(cls, v):
        return _aware(v)


class ReadingsBatchIn(BaseModel):
    readings: list[ReadingIn] = Field(min_length=1, max_length=500)


class ReadingOut(BaseModel):
    id: int
    plant_id: int
    sensor_id: int | None
    metric: str
    value: float
    unit: str
    timestamp: datetime
    source: str
    quality: str


class ReadingsBatchOut(BaseModel):
    accepted: int
    readings: list[ReadingOut]


# ---------- Dashboard ----------

class DashboardPlant(BaseModel):
    id: int
    name: str
    photo_url: str | None
    attention: Attention
    attention_reasons: list[str]
    summary: str


class DashboardOut(BaseModel):
    generated_at: datetime
    plants_total: int
    needs_attention: int
    critical: int
    ai_mode: Literal["demo", "claude"]
    data_sources: dict[str, int]
    plants: list[DashboardPlant]
    upcoming: list[dict]
    recent_events: list[dict]


# ---------- Botanical Spy ----------

SpyConfidence = Literal["высокая", "средняя", "низкая"]
SpyDirection = Literal["climate", "scene", "biology", "owner"]
SpyFactSource = Literal["photo", "pixel_stats", "profile", "sensor", "observation", "care_history", "knowledge"]


class SpyFact(BaseModel):
    text: str
    source: SpyFactSource


class SpyHypothesis(BaseModel):
    text: str
    confidence: SpyConfidence
    evidence: list[str]
    how_to_verify: str


class SpySensorTip(BaseModel):
    sensor: str
    purpose: str


class SpySection(BaseModel):
    direction: SpyDirection
    title: str
    facts: list[SpyFact]
    hypotheses: list[SpyHypothesis]
    unknowns: list[str]
    data_needed: list[str]
    sensors: list[SpySensorTip]


class SpyIdentification(BaseModel):
    name: str
    confidence: SpyConfidence
    basis: str


class SpyVisualEstimates(BaseModel):
    light_level: Literal["low", "medium", "high", "unknown"]
    humidity_level: Literal["low", "medium", "high", "unknown"]
    setting: Literal["indoor", "outdoor", "greenhouse", "unknown"]


class SpyResult(BaseModel):
    codename: str
    summary: str
    identification: SpyIdentification
    sections: list[SpySection]
    clues: list[str]
    to_check: list[str]
    visual_estimates: SpyVisualEstimates
    photo_note: str


class SpyCrosscheck(BaseModel):
    metric: str
    label: str
    visual: str
    measured: str | None
    measured_at: datetime | None
    source: str | None
    verdict: Literal["consistent", "contradicts", "no_data"]
    note: str


class SpyInvestigationOut(BaseModel):
    id: int
    plant_id: int | None
    plant_name: str | None
    photo_url: str | None
    photo_source: Literal["upload", "collection", "illustration", "none"]
    codename: str
    mode: Literal["demo", "claude"]
    model: str | None
    result: SpyResult
    crosscheck: list[SpyCrosscheck]
    image_stats: dict | None
    warnings: list[str] = []
    created_at: datetime


class SpyInvestigationBrief(BaseModel):
    id: int
    plant_id: int | None
    plant_name: str | None
    photo_url: str | None
    photo_source: str
    codename: str
    summary: str
    mode: str
    created_at: datetime
