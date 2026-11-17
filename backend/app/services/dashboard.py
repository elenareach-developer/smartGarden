from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..domain.metrics import CARE_LABELS, CareType
from ..models import CareEvent, Plant
from ..schemas import DashboardOut, DashboardPlant
from .care import planned_tasks
from .plants import plant_card


def summary(db: Session) -> DashboardOut:
    now = datetime.now(timezone.utc)
    plants = list(db.scalars(select(Plant).order_by(Plant.id)))
    cards = [plant_card(db, p) for p in plants]
    upcoming = []
    for p in plants:
        for t in planned_tasks(db, p, now):
            if t.due_at and t.due_at <= now + timedelta(days=7):
                upcoming.append(dict(plant_id=p.id, plant_name=p.name, **t.model_dump(mode="json")))
            elif not t.due_at:
                upcoming.append(dict(plant_id=p.id, plant_name=p.name, **t.model_dump(mode="json")))
    upcoming.sort(key=lambda x: x["due_at"] or "9999")
    names = {p.id: p.name for p in plants}
    recent = list(db.scalars(select(CareEvent).where(CareEvent.timestamp >= now - timedelta(days=14))
                             .order_by(CareEvent.timestamp.desc()).limit(15)))
    sources: dict[str, int] = {}
    for p in plants:
        sources[p.data_source] = sources.get(p.data_source, 0) + 1
    return DashboardOut(
        generated_at=now, plants_total=len(plants),
        needs_attention=sum(c.attention != "ok" for c in cards),
        critical=sum(c.attention == "critical" for c in cards),
        ai_mode=get_settings().effective_ai_mode, data_sources=sources,
        plants=[DashboardPlant(id=c.plant.id, name=c.plant.name, photo_url=c.plant.photo_url,
                               attention=c.attention, attention_reasons=c.attention_reasons, summary=c.summary)
                for c in cards],
        upcoming=upcoming,
        recent_events=[dict(id=e.id, plant_id=e.plant_id, plant_name=names.get(e.plant_id), event_type=e.event_type,
                            event_label=CARE_LABELS[CareType(e.event_type)], timestamp=e.timestamp.isoformat(),
                            notes=e.notes, source=e.source) for e in recent],
    )
