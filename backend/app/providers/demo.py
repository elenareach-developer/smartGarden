"""DemoDataProvider — детерминированный генератор реалистичных измерений.

Это НЕ случайные числа: значения строятся из понятной модели (суточный ход температуры,
астрономическая длина дня, облачность, испарение воды из субстрата после поливов из журнала),
к которой добавлен небольшой воспроизводимый шум. Все записи помечаются source="demo".
"""
import math
import zlib
from bisect import bisect_right
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..domain.metrics import METRICS, DataSource, Metric
from ..models import CareEvent, Plant, SensorReading
from .base import DataProvider


def _noise(seed: int, key: str, ts: int, scale: float) -> float:
    """Воспроизводимый шум в диапазоне [-scale, scale]."""
    h = zlib.crc32(f"{seed}:{key}:{ts}".encode()) / 0xFFFFFFFF
    return (h * 2 - 1) * scale


def day_length_hours(lat_deg: float, day_of_year: int) -> float:
    """Астрономическая длина светового дня (формула склонения Солнца)."""
    decl = math.radians(23.44) * math.sin(2 * math.pi * (284 + day_of_year) / 365)
    x = -math.tan(math.radians(lat_deg)) * math.tan(decl)
    x = max(-1.0, min(1.0, x))
    return 2 * math.degrees(math.acos(x)) / 15


class DemoModel:
    """Физически осмысленная модель показателей для одного растения."""

    def __init__(self, plant: Plant, waterings: list[datetime]):
        p = plant.demo_profile or {}
        self.p = p
        self.seed = int(p.get("seed", plant.id))
        self.anchor = plant.created_at or datetime.now(timezone.utc)
        self.offset = timedelta(hours=p.get("utc_offset", 3))
        self.waterings = sorted(waterings)
        self._wts = [w.timestamp() for w in self.waterings]
        self.plant = plant

    def _days(self, t: datetime) -> float:
        d = (t - self.anchor).total_seconds() / 86400
        return max(-60.0, min(60.0, d))

    def _weather(self, t: datetime, key: str, amp: float) -> float:
        d = t.timestamp() / 86400
        ph1 = (self.seed * 1.7 + len(key)) % (2 * math.pi)
        ph2 = (self.seed * 0.9 + len(key) * 2) % (2 * math.pi)
        return amp * (0.6 * math.sin(2 * math.pi * d / 3.7 + ph1) + 0.4 * math.sin(2 * math.pi * d / 9.3 + ph2))

    def temperature(self, t: datetime) -> float:
        p = self.p
        local = t + self.offset
        h = local.hour + local.minute / 60
        daily = p.get("temp_amp", 2.0) * math.sin(2 * math.pi * (h - 9) / 24)
        v = (p.get("temp_base", 22.0) + p.get("temp_trend", 0.0) * self._days(t)
             + self._weather(t, "temp", p.get("weather_amp", 1.0)) + daily)
        return v + _noise(self.seed, "t", int(t.timestamp()), 0.15)

    def humidity(self, t: datetime) -> float:
        p = self.p
        temp_dev = self.temperature(t) - p.get("temp_base", 22.0)
        v = (p.get("hum_base", 55.0) + p.get("hum_trend", 0.0) * self._days(t)
             - temp_dev * 1.8 + self._weather(t, "hum", p.get("hum_weather_amp", 3.0)))
        return max(15.0, min(95.0, v + _noise(self.seed, "h", int(t.timestamp()), 0.8)))

    def light(self, t: datetime) -> float:
        p = self.p
        local = t + self.offset
        h = local.hour + local.minute / 60
        doy = local.timetuple().tm_yday
        length = day_length_hours(p.get("latitude", 55.75), doy)
        sunrise = 12.5 - length / 2   # солнечный полдень ≈ 12:30 местного времени
        lux = 0.0
        if sunrise <= h <= sunrise + length:
            x = (h - sunrise) / length
            cloud_key = local.strftime("%Y%m%d")
            cloud = 0.45 + 0.55 * (zlib.crc32(f"{self.seed}:cloud:{cloud_key}".encode()) / 0xFFFFFFFF)
            # зимой солнце ниже — пиковая освещённость у окна меньше
            season = 0.55 + 0.45 * (length - 7) / 10
            lux = p.get("light_peak", 8000) * max(0.0, math.sin(math.pi * x)) ** 1.3 * cloud * max(0.3, season)
        lamp = p.get("grow_light")
        if lamp and lamp["on"] <= h < lamp["off"]:
            lux += lamp["lux"]
        elif 18 <= h < 23:
            lux += p.get("room_light", 60)   # комнатное освещение вечером
        if lux <= 0:
            return 0.0
        return max(0.0, lux * (1 + _noise(self.seed, "l", int(t.timestamp()), 0.05)))

    def substrate(self, t: datetime) -> float:
        p = self.p
        ts = t.timestamp()
        i = bisect_right(self._wts, ts)
        if i == 0:
            last = ts - p.get("initial_hours_since_watering", 48) * 3600
        else:
            last = self._wts[i - 1]
        hours = (ts - last) / 3600
        wet, floor, k = p.get("moisture_wet", 85.0), p.get("moisture_floor", 8.0), p.get("dry_k", 0.007)
        # жара и сухой воздух ускоряют высыхание
        temp_f = 1 + 0.04 * (p.get("temp_base", 22) - 22)
        hum_f = 1 + (55 - p.get("hum_base", 55)) / 100
        v = floor + (wet - floor) * math.exp(-k * temp_f * hum_f * hours)
        return max(0.0, min(100.0, v + _noise(self.seed, "m", int(ts), 0.8)))

    def pot_weight(self, t: datetime) -> float:
        p = self.p
        m = self.substrate(t)
        dry = self.plant.pot_weight_dry or 600
        wet = self.plant.pot_weight_wet or dry + 250
        floor, top = p.get("moisture_floor", 8.0), p.get("moisture_wet", 85.0)
        v = dry + (wet - dry) * (m - floor) / (top - floor)
        return max(0.0, v + _noise(self.seed, "w", int(t.timestamp()), 2.0))

    def value(self, metric: Metric, t: datetime) -> float:
        fn = {
            Metric.temperature: self.temperature,
            Metric.air_humidity: self.humidity,
            Metric.light: self.light,
            Metric.substrate_moisture: self.substrate,
            Metric.pot_weight: self.pot_weight,
        }[metric]
        return round(fn(t), METRICS[metric].decimals + 1)


class DemoDataProvider(DataProvider):
    source = DataSource.demo

    def __init__(self, step_minutes: int | None = None, history_days: int | None = None):
        s = get_settings()
        self.step = timedelta(minutes=step_minutes or s.demo_step_minutes)
        self.history_days = history_days or s.demo_history_days

    def _waterings(self, db: Session, plant: Plant) -> list[datetime]:
        return list(db.scalars(select(CareEvent.timestamp).where(
            CareEvent.plant_id == plant.id, CareEvent.event_type == "watering")))

    def sync(self, db: Session, plant: Plant, until: datetime) -> int:
        sensors = self.sensors(db, plant)
        if not sensors:
            return 0
        last = db.scalar(select(func.max(SensorReading.timestamp)).where(
            SensorReading.plant_id == plant.id, SensorReading.source == self.source.value))
        step_s = int(self.step.total_seconds())
        if last is None:
            start = until - timedelta(days=self.history_days)
        else:
            start = last + self.step
        # выравнивание по сетке шага
        start = datetime.fromtimestamp((int(start.timestamp()) + step_s - 1) // step_s * step_s, timezone.utc)
        if start > until:
            return 0

        model = DemoModel(plant, self._waterings(db, plant))
        rows = []
        t = start
        while t <= until:
            for sensor in sensors:
                for m in sensor.metrics:
                    metric = Metric(m)
                    rows.append(dict(
                        sensor_id=sensor.id, plant_id=plant.id, metric=metric.value,
                        value=model.value(metric, t), unit=METRICS[metric].unit,
                        timestamp=t.replace(tzinfo=None), source=self.source.value, quality="ok",
                    ))
            t += self.step
        if rows:
            db.execute(insert(SensorReading), rows)
            db.commit()
        return len(rows)
