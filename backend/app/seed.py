"""Создание трёх демонстрационных орхидей, их DEMO-датчиков и истории ухода."""
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .database import Base
from .domain.metrics import SENSOR_METRICS, SensorType
from .models import CareEvent, Fertilizer, FertilizerApplication, Plant, Sensor
from .providers.registry import demo_provider

PLANTS = [
    dict(
        key="luna",
        name="Луна",
        species="Phalaenopsis (фаленопсис)",
        variety="Гибрид-мультифлора, белые цветки с розовой губой",
        photo_url="/photos/luna.svg",
        stage="blooming",
        location="Восточное окно в гостиной, фитолампа 08:00–20:00",
        pot="Прозрачный пластиковый горшок 12 см",
        substrate="Сосновая кора средней фракции + немного сфагнума",
        notes="Цветёт второй месяц, на цветоносе 9 цветков. Состояние стабильное.",
        acquired_days_ago=420,
        root_status="healthy", leaf_status="healthy", observed_days_ago=5,
        targets=dict(temp_min=18, temp_max=28, humidity_min=50, humidity_max=70,
                     light_min=3000, light_max=12000, photoperiod_min=10, photoperiod_max=14,
                     substrate_min=25, substrate_max=80, watering_interval_days=7,
                     fertilizing_interval_days=14),
        sensors=[("Климат SHT31 (DEMO)", SensorType.SHT31), ("Свет BH1750 (DEMO)", SensorType.BH1750),
                 ("Ёмкостный датчик влажности (DEMO)", SensorType.CAPACITIVE_SOIL)],
        profile=dict(seed=101, temp_base=23.0, temp_amp=1.8, hum_base=57, light_peak=7000,
                     grow_light={"on": 8, "off": 20, "lux": 3500}, dry_k=0.0069,
                     moisture_wet=85, moisture_floor=8, weather_amp=0.8),
        waterings=dict(every=7, last_days_ago=3, amount=300, method="Погружение на 15 минут"),
        feedings=dict(every=14, last_days_ago=10, fert=0, dilution="Как указано на этикетке для орхидей"),
        extra=[(5, "inspection", "Корни плотные, серебристо-зелёные. Листья упругие.")],
    ),
    dict(
        key="caramel",
        name="Карамель",
        species="Cattleya (каттлея)",
        variety="Гибрид, жёлто-оранжевые ароматные цветки",
        photo_url="/photos/caramel.svg",
        stage="vegetative",
        location="Северное окно в спальне, без досветки",
        pot="Пластиковый горшок 14 см с боковыми прорезями, стоит на весах",
        substrate="Крупная сосновая кора",
        notes="Хорошо растёт новый псевдобульб, но не цвела больше года.",
        acquired_days_ago=600,
        root_status="healthy", leaf_status="healthy", observed_days_ago=12,
        targets=dict(temp_min=18, temp_max=29, humidity_min=45, humidity_max=65,
                     light_min=10000, light_max=30000, photoperiod_min=11, photoperiod_max=14,
                     substrate_min=20, substrate_max=75, pot_weight_dry=820, pot_weight_wet=1080,
                     watering_interval_days=8, fertilizing_interval_days=14),
        sensors=[("Климат DHT22 (DEMO)", SensorType.DHT22), ("Свет BH1750 (DEMO)", SensorType.BH1750),
                 ("Весы HX711 (DEMO)", SensorType.HX711)],
        profile=dict(seed=202, temp_base=21.5, temp_amp=1.5, hum_base=52, light_peak=3200,
                     dry_k=0.006, moisture_wet=85, moisture_floor=8, weather_amp=1.0),
        waterings=dict(every=8, last_days_ago=6, amount=350, method="Полив сверху до стока"),
        feedings=dict(every=14, last_days_ago=20, fert=0, dilution="Как указано на этикетке"),
        extra=[(12, "inspection", "Новый псевдобульб 6 см, корни растут. Листья светло-зелёные.")],
    ),
    dict(
        key="emerald",
        name="Изумруд",
        species="Oncidium (онцидиум)",
        variety="Миниатюрный гибрид Twinkle",
        photo_url="/photos/emerald.svg",
        stage="recovery",
        location="Южный подоконник над радиатором отопления",
        pot="Прозрачный горшок 9 см (после пересадки)",
        substrate="Мелкая кора + сфагнум",
        notes="Три недели назад пересажена: удалены загнившие корни. Листья потеряли упругость.",
        acquired_days_ago=200,
        root_status="damaged", leaf_status="wrinkled", observed_days_ago=2,
        targets=dict(temp_min=16, temp_max=26, humidity_min=50, humidity_max=70,
                     light_min=8000, light_max=20000, photoperiod_min=10, photoperiod_max=14,
                     substrate_min=25, substrate_max=80, watering_interval_days=5,
                     fertilizing_interval_days=14),
        sensors=[("Климат DHT22 (DEMO)", SensorType.DHT22)],
        profile=dict(seed=303, temp_base=25.5, temp_amp=2.5, hum_base=34, hum_trend=-0.25,
                     light_peak=9000, weather_amp=1.2),
        waterings=dict(every=5, last_days_ago=6, amount=120, method="Аккуратный полив по краю горшка"),
        feedings=dict(every=0, last_days_ago=40, fert=1, dilution="Как указано на этикетке"),
        extra=[
            (21, "repotting", "Пересадка: удалено около половины корней с признаками гнили."),
            (21, "treatment", "Срезы корней подсушены и присыпаны толчёным углём."),
            (2, "inspection", "Корней мало, 2 новых кончика. Нижний лист морщинистый, желтеет у основания."),
        ],
    ),
]

FERTILIZERS = [
    dict(name="Пример A: комплексное жидкое для орхидей (демо-запись)", npk_n=4, npk_p=4, npk_k=4,
         micronutrients="Fe, Mn, B, Zn, Cu, Mo — по данным этикетки (демо)", form="жидкое",
         concentration="Не внесено — проверьте этикетку", labeled_for_orchids=True,
         manufacturer_instructions=None),
    dict(name="Пример B: для цветения (демо-запись)", npk_n=3, npk_p=6, npk_k=7,
         micronutrients="Mg, Fe — по данным этикетки (демо)", form="жидкое",
         concentration="Не внесено — проверьте этикетку", labeled_for_orchids=True,
         manufacturer_instructions=None),
]


def _events(plant: Plant, spec: dict, now: datetime, ferts: list[Fertilizer], db: Session):
    w = spec["waterings"]
    d = w["last_days_ago"]
    i = 0
    while d <= 45:
        jitter_h = ((plant.id * 7 + i * 5) % 9) - 4
        db.add(CareEvent(plant_id=plant.id, event_type="watering", source="demo", amount_ml=w["amount"],
                         method=w["method"], timestamp=now - timedelta(days=d, hours=jitter_h)))
        d += w["every"]
        i += 1
    f = spec["feedings"]
    d = f["last_days_ago"]
    while d <= 60:
        ts = now - timedelta(days=d, hours=1)
        ev = CareEvent(plant_id=plant.id, event_type="fertilizing", source="demo", timestamp=ts,
                       notes=f"Подкормка: {ferts[f['fert']].name}")
        db.add(ev)
        db.flush()
        db.add(FertilizerApplication(plant_id=plant.id, fertilizer_id=ferts[f["fert"]].id,
                                     care_event_id=ev.id, applied_at=ts, dilution=f["dilution"],
                                     stage_at_application=plant.stage if d < 30 else "vegetative",
                                     source="demo"))
        if not f["every"]:
            break
        d += f["every"]
    for days, kind, note in spec["extra"]:
        db.add(CareEvent(plant_id=plant.id, event_type=kind, source="demo", notes=note,
                         timestamp=now - timedelta(days=days, hours=2)))


def seed_demo(db: Session, now: datetime | None = None) -> bool:
    if db.scalar(select(func.count(Plant.id))):
        return False
    now = now or datetime.now(timezone.utc)
    ferts = [Fertilizer(**f) for f in FERTILIZERS]
    db.add_all(ferts)
    db.flush()
    plants = []
    for spec in PLANTS:
        p = Plant(
            name=spec["name"], species=spec["species"], variety=spec["variety"],
            photo_url=spec["photo_url"], stage=spec["stage"], location=spec["location"], pot=spec["pot"],
            substrate=spec["substrate"], notes=spec["notes"],
            acquired_at=now - timedelta(days=spec["acquired_days_ago"]),
            root_status=spec["root_status"], leaf_status=spec["leaf_status"],
            observed_at=now - timedelta(days=spec["observed_days_ago"], hours=2),
            data_source="demo", demo_profile=spec["profile"], created_at=now, **spec["targets"],
        )
        db.add(p)
        db.flush()
        for name, stype in spec["sensors"]:
            db.add(Sensor(plant_id=p.id, name=name, sensor_type=stype.value, source="demo",
                          metrics=[m.value for m in SENSOR_METRICS[stype]]))
        db.add(Sensor(plant_id=p.id, name="Ручной ввод", sensor_type=SensorType.MANUAL.value,
                      source="manual", metrics=[]))
        _events(p, spec, now, ferts, db)
        plants.append(p)
    db.commit()
    for p in plants:
        demo_provider().sync(db, p, now)
    return True


def reset_demo(db: Session) -> None:
    bind = db.get_bind()
    db.close()
    Base.metadata.drop_all(bind)
    Base.metadata.create_all(bind)
    seed_demo(db)
