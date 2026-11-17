from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import sessionmaker

from app.database import Base, make_engine
from app.models import CareEvent, Plant, SensorReading
from app.providers.demo import day_length_hours
from app.providers.registry import demo_provider
from app.seed import seed_demo
from app.services.forecast import linreg


def _db():
    e = make_engine("sqlite://")
    Base.metadata.create_all(e)
    return sessionmaker(bind=e, expire_on_commit=False)()


def test_demo_is_deterministic_and_grows_with_time():
    now = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
    a, b = _db(), _db()
    seed_demo(a, now)
    seed_demo(b, now)
    va = [r.value for r in a.scalars(select(SensorReading).order_by(SensorReading.id).limit(200))]
    vb = [r.value for r in b.scalars(select(SensorReading).order_by(SensorReading.id).limit(200))]
    assert va == vb
    n0 = a.scalar(select(func.count(SensorReading.id)))
    plant = a.scalars(select(Plant)).first()
    added = demo_provider().sync(a, plant, now + timedelta(hours=3))
    assert added > 0 and a.scalar(select(func.count(SensorReading.id))) == n0 + added
    assert all(r.source == "demo" for r in a.scalars(select(SensorReading).limit(50)))


def test_watering_raises_demo_moisture():
    now = datetime(2026, 11, 17, 12, tzinfo=timezone.utc)
    db = _db()
    seed_demo(db, now)
    luna = db.scalars(select(Plant).where(Plant.name == "Луна")).one()
    before = demo_provider().latest(db, luna, __import__("app.domain.metrics", fromlist=["Metric"]).Metric.substrate_moisture).value
    db.add(CareEvent(plant_id=luna.id, event_type="watering", timestamp=now + timedelta(minutes=1)))
    db.commit()
    demo_provider().sync(db, luna, now + timedelta(hours=2))
    from app.domain.metrics import Metric
    after = demo_provider().latest(db, luna, Metric.substrate_moisture).value
    assert after > before + 15


def test_astronomy_and_regression():
    assert 6.5 < day_length_hours(55.75, 355) < 7.5     # зимнее солнцестояние, Москва
    assert 17 < day_length_hours(55.75, 172) < 18
    slope, icpt, r2, sd = linreg([0, 1, 2, 3], [1, 3, 5, 7])
    assert abs(slope - 2) < 1e-9 and abs(r2 - 1) < 1e-9
