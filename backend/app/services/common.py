from datetime import datetime, timedelta
from statistics import mean

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.metrics import DAYLIGHT_LUX_THRESHOLD, Metric
from ..models import CareEvent, Plant, SensorReading

RANGE_FIELDS = {
    Metric.temperature: ("temp_min", "temp_max"),
    Metric.air_humidity: ("humidity_min", "humidity_max"),
    Metric.light: ("light_min", "light_max"),
    Metric.substrate_moisture: ("substrate_min", "substrate_max"),
}


def target_range(plant: Plant, metric: Metric) -> tuple[float | None, float | None]:
    if metric == Metric.pot_weight:
        if plant.pot_weight_dry and plant.pot_weight_wet:
            lo = plant.pot_weight_dry + 0.25 * (plant.pot_weight_wet - plant.pot_weight_dry)
            return round(lo), plant.pot_weight_wet
        return None, None
    lo, hi = RANGE_FIELDS[metric]
    return getattr(plant, lo), getattr(plant, hi)


def last_event(db: Session, plant_id: int, event_type: str) -> CareEvent | None:
    return db.scalars(select(CareEvent).where(CareEvent.plant_id == plant_id, CareEvent.event_type == event_type)
                      .order_by(CareEvent.timestamp.desc()).limit(1)).first()


def events_of(db: Session, plant_id: int, event_type: str, since: datetime | None = None) -> list[CareEvent]:
    q = select(CareEvent).where(CareEvent.plant_id == plant_id, CareEvent.event_type == event_type)
    if since:
        q = q.where(CareEvent.timestamp >= since)
    return list(db.scalars(q.order_by(CareEvent.timestamp)))


def daylight_stats(readings: list[SensorReading], step_hours: float) -> tuple[float | None, float | None]:
    """(световой день, ч; средняя освещённость в светлое время, lx) по ряду за сутки."""
    if not readings:
        return None, None
    light = [r.value for r in readings if r.value >= DAYLIGHT_LUX_THRESHOLD]
    hours = len(light) * step_hours
    return round(hours, 1), (round(mean(light)) if light else 0.0)


def bucketize(readings: list[SensorReading], start: datetime, bucket: timedelta):
    """Агрегация ряда по интервалам: [(t, avg, min, max)]."""
    buckets: dict[int, list[float]] = {}
    size = bucket.total_seconds()
    for r in readings:
        k = int((r.timestamp - start).total_seconds() // size)
        buckets.setdefault(k, []).append(r.value)
    out = []
    for k in sorted(buckets):
        vals = buckets[k]
        out.append((start + bucket * k + bucket / 2, mean(vals), min(vals), max(vals)))
    return out


def estimate_step_hours(readings: list[SensorReading]) -> float:
    if len(readings) < 2:
        return 0.5
    gaps = sorted((b.timestamp - a.timestamp).total_seconds() for a, b in zip(readings, readings[1:]))
    return max(1 / 60, min(3.0, gaps[len(gaps) // 2] / 3600))
