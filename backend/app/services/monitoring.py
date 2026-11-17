"""Сервис мониторинга: текущее состояние растения по данным любого DataProvider."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..domain.metrics import (
    LEAF_LABELS, METRICS, ROOT_LABELS, LeafStatus, Metric, RootStatus,
)
from ..models import Plant, SensorReading
from ..providers.registry import manual_provider, provider_for
from ..schemas import HistoryOut, HistoryPoint, HistorySeries, MetricState, MonitoringOut, Observation, Reading
from .common import bucketize, daylight_stats, estimate_step_hours, last_event, target_range

STALE_AFTER = timedelta(hours=3)
PERIODS = {"24h": (timedelta(hours=24), timedelta(minutes=30)),
           "7d": (timedelta(days=7), timedelta(hours=2)),
           "30d": (timedelta(days=30), timedelta(hours=6))}


def _reading(r: SensorReading | None) -> Reading | None:
    if r is None:
        return None
    return Reading(value=r.value, unit=r.unit, timestamp=r.timestamp, source=r.source, quality=r.quality)


def _status(value: float | None, lo: float | None, hi: float | None) -> str:
    if value is None:
        return "no_data"
    if lo is not None and value < lo:
        return "low"
    if hi is not None and value > hi:
        return "high"
    return "ok"


STATUS_TEXT = {"ok": "В целевом диапазоне", "low": "Ниже целевого диапазона", "high": "Выше целевого диапазона",
               "no_data": "Нет данных", "stale": "Данные устарели", "night": "Тёмное время суток"}


def sync(db: Session, plant: Plant, now: datetime | None = None) -> None:
    provider_for(plant).sync(db, plant, now or datetime.now(timezone.utc))


class MonitoringService:
    def __init__(self, db: Session):
        self.db = db

    def snapshot(self, plant: Plant, now: datetime | None = None) -> MonitoringOut:
        now = now or datetime.now(timezone.utc)
        sync(self.db, plant, now)
        provider = provider_for(plant)
        available = provider.available_metrics(self.db, plant)
        day = now - timedelta(hours=24)
        states: list[MetricState] = []

        for metric in [Metric.temperature, Metric.air_humidity, Metric.light,
                       Metric.substrate_moisture, Metric.pot_weight]:
            info = METRICS[metric]
            lo, hi = target_range(plant, metric)
            latest = provider.latest(self.db, plant, metric) if metric in available else None
            manual = manual_provider().latest(self.db, plant, metric)
            series = provider.series(self.db, plant, metric, day, now) if latest else []
            spark = [round(v, 1) for _, v, _, _ in bucketize(series, day, timedelta(hours=1))]
            note = None
            if latest is None:
                status = "no_data"
                text = ("Датчик не подключён" if metric not in available else "Нет измерений")
                if metric == Metric.substrate_moisture:
                    note = "Для измерения нужен ёмкостный датчик влажности субстрата."
                if metric == Metric.pot_weight:
                    note = "Для измерения нужны весы HX711 под горшком."
            elif now - latest.timestamp > STALE_AFTER:
                status, text = "stale", f"Последнее измерение {latest.timestamp:%d.%m %H:%M} UTC"
            elif metric == Metric.light:
                _, day_mean = daylight_stats(series, estimate_step_hours(series))
                status = _status(day_mean, lo, hi)
                text = f"Средняя в светлое время за 24 ч: {day_mean:.0f} lx (расчёт) — {STATUS_TEXT[status].lower()}"
                if latest.value < 50:
                    note = "Сейчас тёмное время суток; статус оценивается по средней дневной освещённости."
            else:
                status = _status(latest.value, lo, hi)
                text = STATUS_TEXT[status]
            states.append(MetricState(
                metric=metric.value, label=info.label, unit=info.unit, kind="measured",
                available=metric in available, current=_reading(latest), manual_latest=_reading(manual),
                target_min=lo, target_max=hi, status=status, status_text=text, note=note, sparkline=spark,
            ))

        # Расчётный показатель: продолжительность светового дня
        light_series = provider.series(self.db, plant, Metric.light, day, now) if Metric.light in available else []
        hours, _ = daylight_stats(light_series, estimate_step_hours(light_series))
        if light_series:
            st = _status(hours, plant.photoperiod_min, plant.photoperiod_max)
            photo_text = f"Часы с освещённостью > 300 lx за последние 24 ч — {STATUS_TEXT[st].lower()}"
            current = Reading(value=hours, unit="h", timestamp=light_series[-1].timestamp,
                              source=light_series[-1].source, quality="ok")
        else:
            st, photo_text, current = "no_data", "Нет датчика освещённости — рассчитать нельзя", None
        states.insert(3, MetricState(
            metric="photoperiod", label="Световой день", unit="h", kind="derived",
            available=bool(light_series), current=current, target_min=plant.photoperiod_min,
            target_max=plant.photoperiod_max, status=st, status_text=photo_text,
            note="Расчётный показатель на основе измерений освещённости." if light_series else None,
        ))

        observations = [
            Observation(key="root_status", label="Состояние корней", value=plant.root_status,
                        value_label=ROOT_LABELS[RootStatus(plant.root_status)], observed_at=plant.observed_at,
                        status=_obs_status(plant.root_status)),
            Observation(key="leaf_status", label="Состояние листьев", value=plant.leaf_status,
                        value_label=LEAF_LABELS[LeafStatus(plant.leaf_status)], observed_at=plant.observed_at,
                        status=_obs_status(plant.leaf_status)),
        ]
        attention, reasons = assess_attention(self.db, plant, states, now)
        return MonitoringOut(
            plant_id=plant.id, data_source=plant.data_source, is_demo=plant.data_source == "demo",
            generated_at=now, metrics=states, observations=observations,
            attention=attention, attention_reasons=reasons,
        )

    def history(self, plant: Plant, period: str, metrics: list[str] | None = None,
                now: datetime | None = None) -> HistoryOut:
        now = now or datetime.now(timezone.utc)
        sync(self.db, plant, now)
        span, bucket = PERIODS[period]
        start = now - span
        provider = provider_for(plant)
        wanted = [Metric(m) for m in metrics if m in Metric._value2member_map_] if metrics else list(Metric)
        series, manual = [], []
        for metric in wanted:
            info = METRICS[metric]
            lo, hi = target_range(plant, metric)
            rows = provider.series(self.db, plant, metric, start, now)
            if rows:
                pts = [HistoryPoint(t=t, value=round(v, 2), min=round(a, 2), max=round(b, 2))
                       for t, v, a, b in bucketize(rows, start, bucket)]
                vals = [r.value for r in rows]
                series.append(HistorySeries(
                    metric=metric.value, label=info.label, unit=info.unit, kind="measured",
                    source=provider.source.value, bucket_minutes=int(bucket.total_seconds() // 60),
                    target_min=lo, target_max=hi, points=pts,
                    stats={"min": round(min(vals), 2), "max": round(max(vals), 2),
                           "avg": round(sum(vals) / len(vals), 2), "count": len(vals)},
                ))
            mrows = manual_provider().series(self.db, plant, metric, start, now)
            if mrows:
                manual.append(HistorySeries(
                    metric=metric.value, label=info.label, unit=info.unit, kind="measured", source="manual",
                    bucket_minutes=0, target_min=lo, target_max=hi,
                    points=[HistoryPoint(t=r.timestamp, value=r.value) for r in mrows],
                    stats={"count": len(mrows)},
                ))
        # Световой день по суткам (расчётный)
        if (not metrics or "photoperiod" in metrics) and Metric.light in provider.available_metrics(self.db, plant):
            pts = []
            day_start = (now - span).replace(hour=0, minute=0, second=0, microsecond=0)
            d = day_start
            while d + timedelta(days=1) <= now:
                rows = provider.series(self.db, plant, Metric.light, d, d + timedelta(days=1))
                if rows:
                    h, _ = daylight_stats(rows, estimate_step_hours(rows))
                    pts.append(HistoryPoint(t=d + timedelta(hours=12), value=h))
                d += timedelta(days=1)
            if pts:
                vals = [p.value for p in pts]
                series.append(HistorySeries(
                    metric="photoperiod", label="Световой день", unit="h", kind="derived",
                    source=provider.source.value, bucket_minutes=1440, target_min=plant.photoperiod_min,
                    target_max=plant.photoperiod_max, points=pts,
                    stats={"min": min(vals), "max": max(vals), "avg": round(sum(vals) / len(vals), 2),
                           "count": len(vals)},
                ))
        return HistoryOut(plant_id=plant.id, period=period, start=start, end=now, series=series, manual=manual)


def _obs_status(value: str) -> str:
    if value in ("healthy",):
        return "ok"
    if value in ("rotting", "damaged"):
        return "critical"
    if value == "unknown":
        return "unknown"
    return "attention"


def assess_attention(db: Session, plant: Plant, states: list[MetricState], now: datetime):
    reasons: list[str] = []
    critical = False
    by = {s.metric: s for s in states}

    def out(metric, label):
        s = by.get(metric)
        if s and s.status in ("low", "high"):
            word = "ниже" if s.status == "low" else "выше"
            reasons.append(f"{label} {word} нормы")
            return s
        return None

    t = out("temperature", "Температура")
    if t and t.current and (t.current.value < plant.temp_min - 4 or t.current.value > plant.temp_max + 4):
        critical = True
    h = out("air_humidity", "Влажность воздуха")
    if h and h.current and h.current.value < plant.humidity_min - 10:
        critical = True
    out("light", "Освещённость")
    out("photoperiod", "Световой день")
    out("substrate_moisture", "Влажность субстрата")
    out("pot_weight", "Масса горшка (субстрат пересыхает)")
    if all(by[m].status == "no_data" for m in ("temperature", "air_humidity", "light")):
        reasons.append("Нет данных от датчиков")
    if any(s.status == "stale" for s in states):
        reasons.append("Данные датчиков устарели")

    if plant.root_status in ("damaged", "rotting"):
        reasons.append("Корни повреждены — нужен щадящий уход")
        critical = True
    elif plant.root_status == "dry":
        reasons.append("Корни пересушены")
    if plant.leaf_status in ("wrinkled", "yellowing", "spots"):
        reasons.append({"wrinkled": "Листья потеряли тургор", "yellowing": "Желтеют листья",
                        "spots": "Пятна на листьях"}[plant.leaf_status])

    lw = last_event(db, plant.id, "watering")
    has_moisture_sensor = by["substrate_moisture"].status != "no_data" or by["pot_weight"].status != "no_data"
    if not has_moisture_sensor:
        if lw is None or (now - lw.timestamp).total_seconds() / 86400 > plant.watering_interval_days:
            reasons.append("Пора проверить субстрат: интервал полива истёк")

    if plant.observed_at is None or now - plant.observed_at > timedelta(days=30):
        reasons.append("Давно не было осмотра корней и листьев")

    level = "critical" if critical else ("attention" if reasons else "ok")
    return level, reasons
