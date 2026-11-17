"""Прогноз на 3/7/14 дней по истории показателей и простым прозрачным правилам.

Методика (одинакова для DEMO и IoT):
  * дневные средние за последние ≤14 полных суток → линейный тренд (МНК);
  * тренд затухает (φ=0.85 в сутки): краткосрочные изменения редко продолжаются бесконечно;
  * к уровню добавляется средний суточный профиль за 7 дней (по 3-часовым окнам);
  * интервал = ±1.64·σ остатков, расширяется с горизонтом (~90 % для нормальных остатков);
  * для света учитывается астрономическое изменение длины дня (детерминированный расчёт);
  * уверенность выводится из объёма данных, качества подгонки и горизонта.
Модель не использует случайные значения.
"""
import math
from datetime import datetime, timedelta, timezone
from statistics import mean, median, pstdev

from sqlalchemy.orm import Session

from ..domain.metrics import METRICS, Metric
from ..models import Forecast, Plant, SensorReading
from ..providers.demo import day_length_hours
from ..providers.registry import provider_for
from ..schemas import (
    Dynamics, ForecastOut, ForecastPoint, HistoryPoint, MetricForecast, Risk, WateringForecast,
)
from .common import daylight_stats, estimate_step_hours, events_of, last_event, target_range
from .monitoring import sync

PHI = 0.85
Z90 = 1.64
LOCAL_OFFSET = timedelta(hours=3)   # часовой пояс пользователя для суточного профиля
LATITUDE = 55.75


def conf_label(c: float | None) -> str:
    if c is None:
        return "нет данных для оценки"
    if c >= 0.7:
        return "высокая"
    if c >= 0.45:
        return "средняя"
    return "низкая"


def linreg(xs: list[float], ys: list[float]):
    n = len(xs)
    mx, my = mean(xs), mean(ys)
    sxx = sum((x - mx) ** 2 for x in xs)
    if sxx == 0:
        return 0.0, my, 0.0, 0.0
    slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
    icpt = my - slope * mx
    res = [y - (icpt + slope * x) for x, y in zip(xs, ys)]
    ss_tot = sum((y - my) ** 2 for y in ys)
    r2 = 1 - sum(r * r for r in res) / ss_tot if ss_tot else 1.0
    sd = math.sqrt(sum(r * r for r in res) / max(1, n - 2))
    return slope, icpt, r2, sd


def damped_sum(d: float) -> float:
    return sum(PHI ** i for i in range(1, int(d) + 1)) + (d - int(d)) * PHI ** (int(d) + 1)


class ForecastService:
    def __init__(self, db: Session):
        self.db = db

    # ---------- общий прогноз ряда ----------
    def _daily_means(self, rows: list[SensorReading], now: datetime, metric: Metric):
        days: dict[datetime, list[SensorReading]] = {}
        for r in rows:
            local_day = (r.timestamp + LOCAL_OFFSET).date()
            days.setdefault(local_day, []).append(r)
        today = (now + LOCAL_OFFSET).date()
        out = []
        for d in sorted(days):
            if d == today:
                continue  # неполные сутки искажают среднее
            vals = days[d]
            if metric == Metric.light:
                _, v = daylight_stats(vals, estimate_step_hours(vals))
            else:
                v = mean(x.value for x in vals)
            if len(vals) >= 12:
                out.append((d, v))
        return out[-14:]

    def _profile(self, rows: list[SensorReading], metric: Metric) -> dict[int, float]:
        """Средний суточный профиль (отклонение от суточного среднего) по 3-часовым окнам."""
        if metric == Metric.light:
            return {}
        by_day: dict = {}
        for r in rows:
            local = r.timestamp + LOCAL_OFFSET
            by_day.setdefault(local.date(), []).append((local.hour // 3, r.value))
        acc: dict[int, list[float]] = {}
        for vals in by_day.values():
            if len(vals) < 12:
                continue
            m = mean(v for _, v in vals)
            for slot, v in vals:
                acc.setdefault(slot, []).append(v - m)
        return {k: mean(v) for k, v in acc.items()}

    def metric_forecast(self, plant: Plant, metric: Metric, horizon: int, now: datetime) -> MetricForecast | None:
        provider = provider_for(plant)
        if metric not in provider.available_metrics(self.db, plant):
            return None
        info = METRICS[metric]
        rows = provider.series(self.db, plant, metric, now - timedelta(days=15), now)
        daily = self._daily_means(rows, now, metric)
        label = info.label if metric != Metric.light else "Средняя дневная освещённость"
        if len(daily) < 3:
            return MetricForecast(
                metric=metric.value, label=label, unit=info.unit, method="недостаточно данных",
                trend_per_day=None, current_mean=None, expected_mean=None, points=[], history=[],
                confidence=None, confidence_label=conf_label(None),
                explanation="Нужно не меньше 3 полных суток измерений, чтобы строить прогноз.",
            )
        xs = list(range(len(daily)))
        ys = [v for _, v in daily]
        slope, icpt, r2, sd = linreg(xs, ys)
        level = mean(ys[-3:])
        history = [HistoryPoint(t=datetime.combine(d, datetime.min.time(), timezone.utc) + timedelta(hours=12),
                                value=round(v, 2)) for d, v in daily]

        # сезонная поправка для света: отношение длины дня
        today_len = day_length_hours(LATITUDE, (now + LOCAL_OFFSET).timetuple().tm_yday)
        lamp = (plant.demo_profile or {}).get("grow_light") if plant.data_source == "demo" else None

        profile = self._profile(rows[-7 * 48 * 2:], metric)
        points = []
        step = timedelta(hours=3)
        start = (now + LOCAL_OFFSET).replace(minute=0, second=0, microsecond=0)
        start = start - timedelta(hours=start.hour % 3) + step - LOCAL_OFFSET
        t = start
        end = now + timedelta(days=horizon)
        while t <= end:
            d = (t - now).total_seconds() / 86400
            lvl = level + slope * damped_sum(max(d, 0))
            if metric == Metric.light:
                fut_len = day_length_hours(LATITUDE, (t + LOCAL_OFFSET).timetuple().tm_yday)
                ratio = fut_len / today_len if not lamp else 1 + 0.3 * (fut_len / today_len - 1)
                lvl = level * ratio
            slot = (t + LOCAL_OFFSET).hour // 3
            val = lvl + profile.get(slot, 0.0)
            width = Z90 * max(sd, 0.05 * abs(level) if metric == Metric.light else sd) * math.sqrt(1 + d / 3)
            lo_v, hi_v = val - width, val + width
            if metric in (Metric.air_humidity, Metric.substrate_moisture):
                val, lo_v, hi_v = (max(0, min(100, x)) for x in (val, lo_v, hi_v))
            if metric == Metric.light:
                val, lo_v, hi_v = (max(0, x) for x in (val, lo_v, hi_v))
            points.append(ForecastPoint(t=t, value=round(val, 2), low=round(lo_v, 2), high=round(hi_v, 2)))
            t += step

        expected = level + slope * damped_sum(horizon)
        if metric == Metric.light:
            fut_len = day_length_hours(LATITUDE, (end + LOCAL_OFFSET).timetuple().tm_yday)
            expected = level * (fut_len / today_len if not lamp else 1 + 0.3 * (fut_len / today_len - 1))

        sufficiency = min(1.0, len(daily) / 10)
        spread = sd / max(1e-6, abs(level)) if metric == Metric.light else sd / max(0.5, abs(level) * 0.1)
        fit = max(0.2, 1 - min(1.0, spread) * 0.6)
        horizon_f = {3: 0.95, 7: 0.82, 14: 0.65}[horizon]
        conf = round(sufficiency * fit * horizon_f, 2)

        unit = info.unit
        dec = 0 if metric == Metric.light else 1
        if metric == Metric.light:
            fut_len = day_length_hours(LATITUDE, (end + LOCAL_OFFSET).timetuple().tm_yday)
            expl = (f"Уровень — средняя освещённость в светлое время за последние 3 суток ({level:.0f} lx). "
                    f"Астрономическая длина дня изменится с {today_len:.1f} до {fut_len:.1f} ч"
                    + (", но досветка фитолампой сглаживает этот эффект" if lamp else "")
                    + f". Разброс по дням ±{sd:.0f} lx (зависит от облачности, которую мы не прогнозируем).")
        else:
            trend_txt = (f"тренд {slope:+.2f} {unit}/сут (R²={r2:.2f})" if abs(slope) > 1e-3 else "тренда нет")
            expl = (f"По {len(daily)} суткам: среднее за последние 3 дня {level:.{dec}f} {unit}, {trend_txt}. "
                    f"Тренд затухает со временем, поэтому к концу горизонта изменение не превышает "
                    f"{slope * damped_sum(horizon):+.{dec}f} {unit}. Разброс дневных средних ±{sd:.{dec}f} {unit}. "
                    f"Суточные колебания взяты из профиля за 7 дней.")
        return MetricForecast(
            metric=metric.value, label=label, unit=unit, method="damped_linear_trend+daily_profile",
            trend_per_day=round(slope, 3), current_mean=round(level, 2), expected_mean=round(expected, 2),
            points=points, history=history, confidence=conf, confidence_label=conf_label(conf), explanation=expl,
        )

    # ---------- полив ----------
    def watering(self, plant: Plant, now: datetime, metric_fc: dict[str, MetricForecast]) -> WateringForecast:
        provider = provider_for(plant)
        available = provider.available_metrics(self.db, plant)
        lw = last_event(self.db, plant.id, "watering")
        caution = (" Корни повреждены: перед поливом обязательно проверьте субстрат и корни, "
                   "не поливайте по расписанию." if plant.root_status in ("damaged", "rotting") else "")

        def decay_fit(metric: Metric, threshold: float, floor: float, label: str, unit: str):
            if lw is None:
                return None
            rows = [r for r in provider.series(self.db, plant, metric, lw.timestamp + timedelta(hours=6), now)
                    if r.value - floor > 0.5]
            if len(rows) < 12:
                return None
            xs = [(r.timestamp - now).total_seconds() / 3600 for r in rows]
            ys = [math.log(r.value - floor) for r in rows]
            slope, icpt, r2, _ = linreg(xs, ys)
            current = rows[-1].value
            if current <= threshold:
                return WateringForecast(
                    next_check_at=now, method=f"{metric.value}_decay", based_on=label,
                    confidence=0.8, confidence_label="высокая",
                    explanation=f"{label}: {current:.0f} {unit} — уже ниже порога {threshold:.0f} {unit}. "
                                f"Проверьте субстрат сейчас.{caution}")
            if slope >= 0:
                return None
            hours = (math.log(threshold - floor) - icpt) / slope
            hours = max(0.0, hours)
            conf = round(max(0.3, min(0.9, r2)) * (0.95 if hours < 72 else 0.8), 2)
            demo_note = (" На DEMO-данных подгонка почти идеальна, потому что сами данные смоделированы; "
                         "на реальном датчике уверенность будет ниже." if plant.data_source == "demo" and r2 > 0.98 else "")
            return WateringForecast(
                next_check_at=now + timedelta(hours=hours), method=f"{metric.value}_exponential_decay",
                based_on=label, confidence=conf, confidence_label=conf_label(conf),
                explanation=(f"{label} снижается после полива {lw.timestamp:%d.%m}: сейчас {current:.0f} {unit}. "
                             f"Экспоненциальная модель высыхания (R²={r2:.2f}) даёт достижение порога "
                             f"{threshold:.0f} {unit} примерно через {hours / 24:.1f} сут.{demo_note}{caution}"))

        if Metric.substrate_moisture in available:
            r = decay_fit(Metric.substrate_moisture, plant.substrate_min, 5.0, "Влажность субстрата", "%")
            if r:
                return r
        if Metric.pot_weight in available and plant.pot_weight_dry and plant.pot_weight_wet:
            thr = plant.pot_weight_dry + 0.25 * (plant.pot_weight_wet - plant.pot_weight_dry)
            r = decay_fit(Metric.pot_weight, thr, plant.pot_weight_dry, "Масса горшка", "г")
            if r:
                return r

        # Нет датчика влажности: оценка по журналу поливов и климату
        ws = events_of(self.db, plant.id, "watering", since=now - timedelta(days=60))
        intervals = [(b.timestamp - a.timestamp).total_seconds() / 86400 for a, b in zip(ws, ws[1:])]
        base = median(intervals) if len(intervals) >= 2 else plant.watering_interval_days
        t_fc, h_fc = metric_fc.get("temperature"), metric_fc.get("air_humidity")
        factor = 1.0
        notes = []
        if t_fc and t_fc.expected_mean is not None:
            factor -= 0.03 * (t_fc.expected_mean - 22)
            notes.append(f"ожидаемая температура {t_fc.expected_mean:.1f} °C")
        if h_fc and h_fc.expected_mean is not None:
            factor -= 0.005 * (55 - h_fc.expected_mean)
            notes.append(f"влажность воздуха {h_fc.expected_mean:.0f} %")
        factor = max(0.7, min(1.2, factor))
        interval = base * factor
        if lw is None:
            return WateringForecast(next_check_at=now, method="no_history", based_on="нет записей о поливе",
                                    confidence=None, confidence_label=conf_label(None),
                                    explanation="В журнале нет поливов. Проверьте субстрат и внесите полив в журнал."
                                                + caution)
        nxt = max(now, lw.timestamp + timedelta(days=interval))
        overdue = lw.timestamp + timedelta(days=interval) < now
        return WateringForecast(
            next_check_at=nxt, method="care_history_interval", based_on="журнал поливов + прогноз климата",
            confidence=0.35, confidence_label="низкая",
            explanation=(f"Датчика влажности субстрата нет. Медианный интервал поливов {base:.1f} сут, "
                         f"скорректирован на {', '.join(notes) or 'климат'} → {interval:.1f} сут. "
                         + ("Срок уже наступил — проверьте субстрат пальцем или по весу горшка. " if overdue else
                            "Это время проверки, а не обязательного полива. ")
                         + caution).strip())

    # ---------- риски ----------
    def risks(self, plant: Plant, fc: dict[str, MetricForecast], derived: dict, horizon: int) -> list[Risk]:
        risks: list[Risk] = []
        t = fc.get("temperature")
        if t and t.points:
            mx = max(p.value for p in t.points)
            mn = min(p.value for p in t.points)
            if mx > plant.temp_max:
                lvl = "high" if mx > plant.temp_max + 3 else "medium"
                risks.append(Risk(code="overheat", title="Перегрев", level=lvl, kind="forecast",
                                  explanation=f"В прогнозе дневной максимум до {mx:.1f} °C при верхней границе {plant.temp_max:.0f} °C.",
                                  based_on=["прогноз температуры"],
                                  suggestion="Отодвиньте растение от радиатора или стекла в солнечные часы, проветривайте без сквозняков."))
            if mn < plant.temp_min:
                risks.append(Risk(code="cold", title="Переохлаждение", level="medium", kind="forecast",
                                  explanation=f"Ночной минимум в прогнозе {mn:.1f} °C при нижней границе {plant.temp_min:.0f} °C.",
                                  based_on=["прогноз температуры"],
                                  suggestion="Не ставьте горшок на холодный подоконник ночью; избегайте полива перед холодной ночью."))
        h = fc.get("air_humidity")
        if h and h.expected_mean is not None and h.expected_mean < plant.humidity_min:
            gap = plant.humidity_min - h.expected_mean
            hot = t and t.expected_mean is not None and t.expected_mean > 24
            risks.append(Risk(
                code="dry_air", title="Сухой воздух", level="high" if gap > 10 else "medium", kind="forecast",
                explanation=(f"Ожидаемая средняя влажность {h.expected_mean:.0f} % при минимуме {plant.humidity_min:.0f} %"
                             + (", в сочетании с теплом это ускоряет потерю воды листьями" if hot else "") + ". "
                             "Сухой тёплый воздух повышает риск обезвоживания, засыхания бутонов и паутинного клеща."),
                based_on=["прогноз влажности"] + (["прогноз температуры"] if hot else []),
                suggestion="Поддон с влажным керамзитом (горшок не в воде), увлажнитель рядом, отодвинуть от батареи."))
        if h and t and h.expected_mean is not None and t.expected_mean is not None \
                and h.expected_mean > 75 and t.expected_mean < 18:
            risks.append(Risk(code="fungal", title="Грибковые инфекции", level="medium", kind="hypothesis",
                              explanation="Прохладно и очень влажно — условия, в которых развиваются грибковые и бактериальные гнили.",
                              based_on=["прогноз влажности", "прогноз температуры"],
                              suggestion="Улучшите циркуляцию воздуха, не оставляйте воду в пазухах листьев."))
        light = derived.get("day_light_mean")
        if light is not None and light < plant.light_min:
            risks.append(Risk(
                code="low_light", title="Недостаток света", level="high" if light < plant.light_min * 0.5 else "medium",
                kind="derived",
                explanation=(f"Средняя освещённость в светлое время {light:.0f} lx при нужных ≥ {plant.light_min:.0f} lx. "
                             "Нехватка света — частая причина отсутствия цветения."),
                based_on=["измерения освещённости (расчёт)"],
                suggestion="Переставьте ближе к светлому окну или добавьте фитолампу по таймеру."))
        ph, ph_end = derived.get("photoperiod_now"), derived.get("photoperiod_astro_end")
        if ph is not None and ph < plant.photoperiod_min:
            risks.append(Risk(
                code="short_day", title="Короткий световой день", level="medium", kind="derived",
                explanation=(f"Световой день {ph:.1f} ч при нужных ≥ {plant.photoperiod_min:.0f} ч. "
                             f"Астрономически к концу горизонта день станет {ph_end:.1f} ч."),
                based_on=["измерения освещённости", "астрономический расчёт"],
                suggestion="Досветка до 11–12 часов в сутки."))
        if plant.root_status in ("damaged", "rotting"):
            risks.append(Risk(
                code="root_rot", title="Повторное загнивание корней", level="high", kind="observation",
                explanation="По последнему осмотру корни повреждены. Избыточный полив и холодный субстрат повышают риск гнили.",
                based_on=["наблюдение: состояние корней"],
                suggestion="Поливайте только после просыхания субстрата, держите горшок в тепле, контролируйте новые корни."))
        if plant.leaf_status == "wrinkled":
            risks.append(Risk(
                code="dehydration", title="Обезвоживание", level="high" if plant.root_status in ("damaged", "rotting") else "medium",
                kind="hypothesis",
                explanation="Морщинистые листья означают, что растение получает меньше воды, чем теряет. "
                            "При повреждённых корнях это ожидаемо и само по себе не говорит о нехватке полива.",
                based_on=["наблюдение: состояние листьев", "наблюдение: состояние корней"],
                suggestion="Повышайте влажность воздуха, а не частоту полива; оцените корни перед изменением режима."))
        if not fc:
            risks.append(Risk(code="no_data", title="Нет данных", level="medium", kind="derived",
                              explanation="Без измерений прогноз и оценка рисков невозможны.",
                              based_on=[], suggestion="Подключите датчики или внесите измерения вручную."))
        order = {"high": 0, "medium": 1, "low": 2}
        return sorted(risks, key=lambda r: order[r.level])

    def dynamics(self, plant: Plant, risks: list[Risk]) -> Dynamics:
        high = [r for r in risks if r.level == "high"]
        med = [r for r in risks if r.level == "medium"]
        factors = [r.title for r in risks]
        if plant.stage == "recovery" and high:
            return Dynamics(trajectory="declining" if len(high) >= 2 else "uncertain",
                            title="Восстановление под угрозой" if len(high) >= 2 else "Неопределённое восстановление",
                            explanation=("Растение восстанавливается после повреждения корней, а условия "
                                         "(" + ", ".join(r.title.lower() for r in high) + ") мешают этому. "
                                         "Если их не исправить, вероятно дальнейшее ослабление листьев."),
                            factors=factors)
        if len(high) >= 2:
            return Dynamics(trajectory="declining", title="Вероятно ухудшение",
                            explanation="Несколько факторов риска высокого уровня одновременно.", factors=factors)
        if high or len(med) >= 2:
            return Dynamics(trajectory="uncertain", title="Состояние может измениться",
                            explanation="Есть заметные отклонения условий; растение может отреагировать в ближайшие недели "
                                        "(рост замедлится, не будет цветоноса).", factors=factors)
        if plant.stage == "blooming":
            return Dynamics(trajectory="stable", title="Стабильно, цветение продолжится",
                            explanation="Условия в целевых диапазонах; при сохранении режима цветение, вероятно, продолжится.",
                            factors=factors)
        return Dynamics(trajectory="stable", title="Стабильное состояние",
                        explanation="Существенных рисков в горизонте прогноза не видно.", factors=factors)

    # ---------- сборка ----------
    def build(self, plant: Plant, horizon: int, now: datetime | None = None, save: bool = True) -> ForecastOut:
        now = now or datetime.now(timezone.utc)
        sync(self.db, plant, now)
        fc: dict[str, MetricForecast] = {}
        for m in (Metric.temperature, Metric.air_humidity, Metric.light):
            r = self.metric_forecast(plant, m, horizon, now)
            if r:
                fc[m.value] = r

        provider = provider_for(plant)
        derived_rows = []
        derived: dict = {}
        today_len = day_length_hours(LATITUDE, (now + LOCAL_OFFSET).timetuple().tm_yday)
        end_len = day_length_hours(LATITUDE, (now + timedelta(days=horizon) + LOCAL_OFFSET).timetuple().tm_yday)
        derived["photoperiod_astro_end"] = end_len
        derived_rows.append(dict(key="astro_day", label="Астрономическая длина дня", kind="derived",
                                 value=round(today_len, 1), value_end=round(end_len, 1), unit="h",
                                 explanation=f"Расчёт по широте {LATITUDE}° и дате; не зависит от датчиков."))
        if Metric.light in provider.available_metrics(self.db, plant):
            rows = provider.series(self.db, plant, Metric.light, now - timedelta(hours=24), now)
            hours, day_mean = daylight_stats(rows, estimate_step_hours(rows))
            derived["photoperiod_now"], derived["day_light_mean"] = hours, day_mean
            derived_rows.append(dict(key="photoperiod", label="Световой день по датчику", kind="derived",
                                     value=hours, unit="h",
                                     explanation="Часы с освещённостью > 300 lx за последние 24 ч."))
            derived_rows.append(dict(key="day_light_mean", label="Средняя освещённость днём", kind="derived",
                                     value=day_mean, unit="lx",
                                     explanation="Среднее по измерениям в светлое время за последние 24 ч."))

        watering = self.watering(plant, now, fc)
        risks = self.risks(plant, fc, derived, horizon)
        dyn = self.dynamics(plant, risks)
        out = ForecastOut(
            plant_id=plant.id, horizon_days=horizon, generated_at=now, data_source=plant.data_source,
            is_demo=plant.data_source == "demo",
            method_summary=("Затухающий линейный тренд по дневным средним (≤14 сут) + суточный профиль за 7 дней; "
                            "свет — с поправкой на астрономическую длину дня; полив — модель высыхания субстрата "
                            "или интервал по журналу."),
            metrics=list(fc.values()), derived=derived_rows, watering=watering, risks=risks, dynamics=dyn,
            disclaimer=("Прогноз построен на DEMO-данных: методика реальная, но исходные измерения смоделированы."
                        if plant.data_source == "demo" else
                        "Прогноз построен на измерениях датчиков. Погода и действия пользователя не прогнозируются."),
        )
        if save:
            rec = Forecast(plant_id=plant.id, horizon_days=horizon, method="damped_trend_v1",
                           data_source=plant.data_source,
                           payload=out.model_dump(mode="json", exclude={"metrics": {"__all__": {"points", "history"}}}))
            self.db.add(rec)
            self.db.commit()
            out.forecast_id = rec.id
        return out
