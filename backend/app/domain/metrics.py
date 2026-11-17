"""Справочник показателей: единицы, допустимые физические диапазоны, подписи."""
from dataclasses import dataclass
from enum import Enum


class Metric(str, Enum):
    temperature = "temperature"
    air_humidity = "air_humidity"
    light = "light"
    substrate_moisture = "substrate_moisture"
    pot_weight = "pot_weight"


@dataclass(frozen=True)
class MetricInfo:
    metric: Metric
    label: str
    unit: str
    valid_min: float  # физически возможный диапазон — значения вне него отклоняются
    valid_max: float
    decimals: int


METRICS: dict[Metric, MetricInfo] = {
    Metric.temperature: MetricInfo(Metric.temperature, "Температура", "°C", -20, 60, 1),
    Metric.air_humidity: MetricInfo(Metric.air_humidity, "Влажность воздуха", "%", 0, 100, 0),
    Metric.light: MetricInfo(Metric.light, "Освещённость", "lx", 0, 150_000, 0),
    Metric.substrate_moisture: MetricInfo(Metric.substrate_moisture, "Влажность субстрата", "%", 0, 100, 0),
    Metric.pot_weight: MetricInfo(Metric.pot_weight, "Масса горшка", "g", 0, 50_000, 0),
}

# Порог, выше которого считаем, что «светло» (для расчёта светового дня)
DAYLIGHT_LUX_THRESHOLD = 300.0


class DataSource(str, Enum):
    demo = "demo"      # сгенерировано DemoDataProvider
    iot = "iot"        # пришло от физического датчика
    manual = "manual"  # внесено пользователем вручную


class ReadingQuality(str, Enum):
    ok = "ok"
    suspect = "suspect"
    error = "error"


class SensorType(str, Enum):
    DHT22 = "DHT22"
    SHT31 = "SHT31"
    BH1750 = "BH1750"
    HX711 = "HX711"
    CAPACITIVE_SOIL = "CAPACITIVE_SOIL"
    DEMO_VIRTUAL = "DEMO_VIRTUAL"
    MANUAL = "MANUAL"
    OTHER = "OTHER"


SENSOR_METRICS: dict[SensorType, list[Metric]] = {
    SensorType.DHT22: [Metric.temperature, Metric.air_humidity],
    SensorType.SHT31: [Metric.temperature, Metric.air_humidity],
    SensorType.BH1750: [Metric.light],
    SensorType.HX711: [Metric.pot_weight],
    SensorType.CAPACITIVE_SOIL: [Metric.substrate_moisture],
}


class Stage(str, Enum):
    vegetative = "vegetative"
    spike = "spike"
    blooming = "blooming"
    resting = "resting"
    recovery = "recovery"


STAGE_LABELS = {
    Stage.vegetative: "Вегетация (рост листьев и корней)",
    Stage.spike: "Рост цветоноса",
    Stage.blooming: "Цветение",
    Stage.resting: "Период покоя",
    Stage.recovery: "Восстановление",
}


class RootStatus(str, Enum):
    healthy = "healthy"
    dry = "dry"
    damaged = "damaged"
    rotting = "rotting"
    unknown = "unknown"


ROOT_LABELS = {
    RootStatus.healthy: "Здоровые: плотные, зелёные/серебристые",
    RootStatus.dry: "Пересушены: сморщенные, ломкие",
    RootStatus.damaged: "Повреждены: часть корней утрачена",
    RootStatus.rotting: "Признаки гнили: мягкие, тёмные",
    RootStatus.unknown: "Не осматривались",
}


class LeafStatus(str, Enum):
    healthy = "healthy"
    wrinkled = "wrinkled"
    yellowing = "yellowing"
    spots = "spots"
    unknown = "unknown"


LEAF_LABELS = {
    LeafStatus.healthy: "Упругие, ровного цвета",
    LeafStatus.wrinkled: "Потеря тургора, морщинистые",
    LeafStatus.yellowing: "Желтеют",
    LeafStatus.spots: "Пятна на листьях",
    LeafStatus.unknown: "Не осматривались",
}


class CareType(str, Enum):
    watering = "watering"
    fertilizing = "fertilizing"
    misting = "misting"
    repotting = "repotting"
    inspection = "inspection"
    treatment = "treatment"
    other = "other"


CARE_LABELS = {
    CareType.watering: "Полив",
    CareType.fertilizing: "Подкормка",
    CareType.misting: "Опрыскивание",
    CareType.repotting: "Пересадка",
    CareType.inspection: "Осмотр",
    CareType.treatment: "Обработка",
    CareType.other: "Другое",
}
