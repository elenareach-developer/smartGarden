from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.metrics import CARE_LABELS, CareType
from ..models import CareEvent, Plant
from ..schemas import CareEventIn, CareEventOut, CareOut, PlannedTask
from .fertilizer import next_window
from .forecast import ForecastService


def event_out(e: CareEvent) -> CareEventOut:
    return CareEventOut(id=e.id, plant_id=e.plant_id, event_type=e.event_type,
                        event_label=CARE_LABELS[CareType(e.event_type)], timestamp=e.timestamp,
                        amount_ml=e.amount_ml, method=e.method, notes=e.notes, source=e.source)


def planned_tasks(db: Session, plant: Plant, now: datetime) -> list[PlannedTask]:
    fc = ForecastService(db).build(plant, 3, now, save=False)
    w = fc.watering
    tasks = [PlannedTask(task="watering_check", title="Проверить субстрат / полив", due_at=w.next_check_at,
                         kind="forecast", explanation=w.explanation)]
    tasks.append(next_window(db, plant, now))
    due = (plant.observed_at + timedelta(days=14)) if plant.observed_at else now
    tasks.append(PlannedTask(task="inspection", title="Осмотр корней и листьев", due_at=max(due, now),
                             kind="derived", explanation="Регулярный осмотр раз в 2 недели обновляет наблюдения "
                                                          "о корнях и листьях, на которые опирается AI."))
    return sorted(tasks, key=lambda t: t.due_at or now + timedelta(days=365))


class CareService:
    def __init__(self, db: Session):
        self.db = db

    def list(self, plant: Plant, limit: int = 200, event_type: str | None = None) -> CareOut:
        q = select(CareEvent).where(CareEvent.plant_id == plant.id)
        if event_type:
            q = q.where(CareEvent.event_type == event_type)
        events = list(self.db.scalars(q.order_by(CareEvent.timestamp.desc()).limit(limit)))
        now = datetime.now(timezone.utc)
        return CareOut(plant_id=plant.id, events=[event_out(e) for e in events], planned=planned_tasks(self.db, plant, now))

    def add(self, plant: Plant, data: CareEventIn) -> CareEventOut:
        ts = data.timestamp or datetime.now(timezone.utc)
        ev = CareEvent(plant_id=plant.id, event_type=data.event_type.value, timestamp=ts,
                       amount_ml=data.amount_ml, method=data.method, notes=data.notes, source="user")
        self.db.add(ev)
        if data.event_type == CareType.inspection:
            if data.root_status:
                plant.root_status = data.root_status.value
            if data.leaf_status:
                plant.leaf_status = data.leaf_status.value
            plant.observed_at = ts
        self.db.commit()
        return event_out(ev)
