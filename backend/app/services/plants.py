from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.metrics import LEAF_LABELS, ROOT_LABELS, STAGE_LABELS, LeafStatus, RootStatus, Stage
from ..models import Plant, Sensor
from ..schemas import PlantCard, PlantOut, PlantUpdate, Targets
from .common import last_event
from .monitoring import MonitoringService


class NotFound(LookupError):
    pass


def get_plant(db: Session, plant_id: int) -> Plant:
    p = db.get(Plant, plant_id)
    if p is None:
        raise NotFound(f"Растение {plant_id} не найдено")
    return p


def plant_out(p: Plant) -> PlantOut:
    return PlantOut(
        id=p.id, name=p.name, species=p.species, variety=p.variety, photo_url=p.photo_url,
        stage=p.stage, stage_label=STAGE_LABELS[Stage(p.stage)], location=p.location, pot=p.pot,
        substrate=p.substrate, notes=p.notes, acquired_at=p.acquired_at,
        root_status=p.root_status, root_label=ROOT_LABELS[RootStatus(p.root_status)],
        leaf_status=p.leaf_status, leaf_label=LEAF_LABELS[LeafStatus(p.leaf_status)],
        observed_at=p.observed_at, data_source=p.data_source,
        targets=Targets(**{k: getattr(p, k) for k in Targets.model_fields}),
        created_at=p.created_at, updated_at=p.updated_at,
    )


def summary_text(attention: str, reasons: list[str]) -> str:
    if not reasons:
        return "Все показатели в норме"
    head = reasons[0]
    return head if len(reasons) == 1 else f"{head} и ещё {len(reasons) - 1}"


def plant_card(db: Session, p: Plant) -> PlantCard:
    mon = MonitoringService(db).snapshot(p)
    lw, lf = last_event(db, p.id, "watering"), last_event(db, p.id, "fertilizing")
    sensors = [s.name for s in db.scalars(select(Sensor).where(Sensor.plant_id == p.id, Sensor.source == p.data_source))]
    return PlantCard(plant=plant_out(p), summary=summary_text(mon.attention, mon.attention_reasons),
                     attention=mon.attention, attention_reasons=mon.attention_reasons,
                     last_watering=lw.timestamp if lw else None, last_fertilizing=lf.timestamp if lf else None,
                     sensors=sensors)


def update_plant(db: Session, p: Plant, data: PlantUpdate) -> Plant:
    fields = data.model_dump(exclude_unset=True, exclude={"targets"})
    for k, v in fields.items():
        if k in ("name", "species") and v is None:
            continue
        setattr(p, k, v.value if hasattr(v, "value") else v)
    if "root_status" in fields or "leaf_status" in fields:
        p.observed_at = datetime.now(timezone.utc)
    if data.targets:
        for k, v in data.targets.model_dump().items():
            setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p
