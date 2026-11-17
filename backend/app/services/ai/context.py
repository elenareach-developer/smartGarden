"""Контекст растения для AI. Содержит только реально существующие данные и явный список
отсутствующих — чтобы ни Claude, ни демо-движок не «додумывали» измерения."""
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ...domain.metrics import LEAF_LABELS, ROOT_LABELS, STAGE_LABELS, LeafStatus, RootStatus, Stage
from ...models import Plant
from ..common import events_of
from ..fertilizer import last_application
from ..forecast import ForecastService
from ..monitoring import MonitoringService

SEASONS = {12: "winter", 1: "winter", 2: "winter", 3: "spring", 4: "spring", 5: "spring",
           6: "summer", 7: "summer", 8: "summer", 9: "autumn", 10: "autumn", 11: "autumn"}
SEASON_NOTES = {
    "winter": "Зима: короткий день, отопление сушит воздух; рост замедляется, полив и подкормки обычно реже.",
    "spring": "Весна: день удлиняется, начинается активный рост; потребность в воде и питании растёт.",
    "summer": "Лето: много света, риск перегрева и ожогов на южных окнах; субстрат сохнет быстрее.",
    "autumn": "Осень: день сокращается, начинается отопительный сезон — воздух суше, света меньше.",
}


def season_of(now: datetime) -> tuple[str, str]:
    s = SEASONS[now.month]
    return s, SEASON_NOTES[s]


def build_context(db: Session, plant: Plant, now: datetime | None = None) -> dict:
    now = now or datetime.now(timezone.utc)
    mon = MonitoringService(db).snapshot(plant, now)
    fc = ForecastService(db).build(plant, 7, now, save=False)
    season, season_note = season_of(now)

    measured, missing = [], []
    for m in mon.metrics:
        if m.current:
            measured.append(dict(
                metric=m.metric, label=m.label, kind=m.kind, value=m.current.value, unit=m.current.unit,
                timestamp=m.current.timestamp.isoformat(), source=str(getattr(m.current.source, 'value', m.current.source)), status=m.status,
                status_text=m.status_text, target=[m.target_min, m.target_max]))
        else:
            missing.append(m.label)
        if m.manual_latest:
            measured.append(dict(metric=m.metric, label=m.label + " (ручное измерение)", kind="measured",
                                 value=m.manual_latest.value, unit=m.manual_latest.unit,
                                 timestamp=m.manual_latest.timestamp.isoformat(), source="manual"))

    waterings = events_of(db, plant.id, "watering", since=now - timedelta(days=45))
    feedings = events_of(db, plant.id, "fertilizing", since=now - timedelta(days=90))
    others = [e for t in ("inspection", "repotting", "treatment", "misting")
              for e in events_of(db, plant.id, t, since=now - timedelta(days=60))]
    la = last_application(db, plant.id)

    return dict(
        now=now.isoformat(),
        season=season, season_note=season_note,
        data_source=plant.data_source,
        is_demo=plant.data_source == "demo",
        plant=dict(
            id=plant.id, name=plant.name, species=plant.species, variety=plant.variety,
            stage=plant.stage, stage_label=STAGE_LABELS[Stage(plant.stage)], location=plant.location,
            pot=plant.pot, substrate=plant.substrate, notes=plant.notes,
            root_status=plant.root_status, root_label=ROOT_LABELS[RootStatus(plant.root_status)],
            leaf_status=plant.leaf_status, leaf_label=LEAF_LABELS[LeafStatus(plant.leaf_status)],
            observed_at=plant.observed_at.isoformat() if plant.observed_at else None,
            targets=dict(temperature=[plant.temp_min, plant.temp_max],
                         air_humidity=[plant.humidity_min, plant.humidity_max],
                         light_day_mean=[plant.light_min, plant.light_max],
                         photoperiod=[plant.photoperiod_min, plant.photoperiod_max],
                         substrate_moisture=[plant.substrate_min, plant.substrate_max],
                         watering_interval_days=plant.watering_interval_days,
                         fertilizing_interval_days=plant.fertilizing_interval_days),
        ),
        measured=measured,
        missing_measurements=missing,
        attention=dict(level=mon.attention, reasons=mon.attention_reasons),
        care=dict(
            waterings=[dict(t=e.timestamp.isoformat(), amount_ml=e.amount_ml, method=e.method) for e in waterings],
            feedings=[dict(t=e.timestamp.isoformat(), notes=e.notes) for e in feedings],
            last_fertilizer=(dict(name=la.fertilizer.name, applied_at=la.applied_at.isoformat(),
                                  npk=[la.fertilizer.npk_n, la.fertilizer.npk_p, la.fertilizer.npk_k])
                             if la else None),
            other=[dict(type=e.event_type, t=e.timestamp.isoformat(), notes=e.notes)
                   for e in sorted(others, key=lambda x: x.timestamp)],
        ),
        forecast_7d=dict(
            metrics=[dict(metric=m.metric, current_mean=m.current_mean, expected_mean=m.expected_mean,
                          trend_per_day=m.trend_per_day, confidence=m.confidence_label) for m in fc.metrics],
            watering_check=dict(at=fc.watering.next_check_at.isoformat() if fc.watering.next_check_at else None,
                                confidence=fc.watering.confidence_label, explanation=fc.watering.explanation),
            risks=[dict(title=r.title, level=r.level, kind=r.kind, explanation=r.explanation) for r in fc.risks],
            dynamics=dict(trajectory=fc.dynamics.trajectory, title=fc.dynamics.title),
        ),
    )
