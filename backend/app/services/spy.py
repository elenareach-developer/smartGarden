"""Botanical Spy: расследование по фотографии.

Переиспользует существующие части: контекст растения (build_context — профиль, датчики, наблюдения,
журнал ухода), MonitoringService (сверка с реальными показаниями), настройки AI и папку uploads."""
from datetime import datetime, timedelta, timezone
from statistics import median, pstdev

from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import CareEvent, Plant, Sensor, SensorReading, SpyInvestigation
from ..schemas import SpyCrosscheck, SpyInvestigationBrief, SpyInvestigationOut, SpyResult
from .ai.claude_engine import ClaudeUnavailable
from .ai.context import build_context
from .ai.spy_claude import ClaudeSpyEngine
from .ai.spy_demo import DemoSpyEngine, genus_of
from .common import events_of
from .monitoring import MonitoringService
from .spy_images import ImageError, normalized, open_image, pixel_stats, safe_exif, save_clean, to_base64_jpeg

DIRECTIONS = ["climate", "scene", "biology", "owner"]
LEVEL_RU = {"low": "низкий", "medium": "средний", "high": "высокий", "unknown": "не оценён"}


class SpyError(ValueError):
    def __init__(self, message: str, status_code: int = 422):
        super().__init__(message)
        self.status_code = status_code


def owner_stats(db: Session, now: datetime) -> dict:
    plants = list(db.scalars(select(Plant)))
    genera = {(genus_of(p.species) or {}).get("name", p.species.split()[0].lower()) for p in plants}
    care = db.scalar(select(func.count(CareEvent.id)).where(CareEvent.timestamp >= now - timedelta(days=45))) or 0
    manual = db.scalar(select(func.count(SensorReading.id)).where(SensorReading.source == "manual")) or 0
    sensors = db.scalar(select(func.count(Sensor.id)).where(Sensor.source.in_(["demo", "iot"]))) or 0
    spreads = []
    for p in plants:
        ws = events_of(db, p.id, "watering", since=now - timedelta(days=60))
        iv = [(b.timestamp - a.timestamp).total_seconds() / 86400 for a, b in zip(ws, ws[1:])]
        if len(iv) >= 3:
            spreads.append(pstdev(iv))
    spread = median(spreads) if spreads else None
    return dict(plants=len(plants), genera=len(genera), care_events=care, manual_readings=manual, sensors=sensors,
                watering_spread=spread or 0.0, watering_regular=(spread < 1.0) if spread is not None else None)


def crosscheck(db: Session, plant: Plant | None, estimates: dict) -> list[SpyCrosscheck]:
    """Детерминированная сверка визуальных оценок AI с реальными показаниями. Измерения не придумываются."""
    rows: list[SpyCrosscheck] = []
    vis_light = estimates.get("light_level", "unknown")
    vis_hum = estimates.get("humidity_level", "unknown")
    if plant is None:
        for metric, label, vis in (("light", "Освещённость", vis_light), ("air_humidity", "Влажность воздуха", vis_hum)):
            rows.append(SpyCrosscheck(metric=metric, label=label, visual=LEVEL_RU[vis], measured=None, measured_at=None,
                                      source=None, verdict="no_data",
                                      note="Фото не привязано к растению — сверять не с чем."))
        return rows
    mon = {m.metric: m for m in MonitoringService(db).snapshot(plant).metrics}

    light = mon.get("light")
    if light and light.current:
        measured_level = {"low": "low", "ok": "medium", "high": "high"}.get(light.status, "unknown")
        text = light.status_text.split("—")[0].strip()
        rows.append(_verdict("light", "Освещённость", vis_light, measured_level, text, light.current.timestamp,
                             light.current.source, "уровень относительно целевого диапазона растения"))
    else:
        rows.append(SpyCrosscheck(metric="light", label="Освещённость", visual=LEVEL_RU[vis_light], measured=None,
                                  measured_at=None, source=None, verdict="no_data",
                                  note="Датчика освещённости нет — проверить визуальную оценку нечем."))

    hum = mon.get("air_humidity")
    if hum and hum.current:
        v = hum.current.value
        level = "low" if v < 45 else "high" if v > 65 else "medium"
        rows.append(_verdict("air_humidity", "Влажность воздуха", vis_hum, level, f"{v:.0f} %", hum.current.timestamp,
                             hum.current.source, "низкая <45 %, высокая >65 %"))
    else:
        rows.append(SpyCrosscheck(metric="air_humidity", label="Влажность воздуха", visual=LEVEL_RU[vis_hum], measured=None,
                                  measured_at=None, source=None, verdict="no_data",
                                  note="Датчика влажности нет — проверить визуальную оценку нечем."))
    return rows


def _verdict(metric, label, visual, measured_level, measured_text, ts, source, rule) -> SpyCrosscheck:
    if visual == "unknown":
        verdict, note = "no_data", f"По фото уровень не оценить; датчик: {LEVEL_RU[measured_level]} ({rule})."
    elif visual == measured_level:
        verdict, note = "consistent", f"Визуальная оценка совпадает с датчиком ({rule})."
    else:
        verdict, note = "contradicts", (f"Фото намекает на «{LEVEL_RU[visual]}», а датчик показывает «{LEVEL_RU[measured_level]}». "
                                        "Фото — мгновенный снимок, датчик — среднее за сутки: доверяйте датчику.")
    src = str(getattr(source, "value", source))
    return SpyCrosscheck(metric=metric, label=label, visual=LEVEL_RU[visual], measured=measured_text, measured_at=ts,
                         source=src, verdict=verdict, note=note)


def _normalize(raw: dict) -> SpyResult:
    """Гарантирует четыре направления и ровно ≤3 гипотезы; отбрасывает лишнее."""
    by = {}
    for s in raw.get("sections", []):
        if s.get("direction") in DIRECTIONS and s["direction"] not in by:
            s["hypotheses"] = s.get("hypotheses", [])[:3]
            by[s["direction"]] = s
    titles = {"climate": "Климатическая разведка", "scene": "Расследование окружения",
              "biology": "Биологические улики", "owner": "Профиль владельца"}
    raw["sections"] = [by.get(d) or dict(direction=d, title=titles[d], facts=[], hypotheses=[],
                                         unknowns=["Агент не вернул данные по этому направлению"], data_needed=[], sensors=[])
                       for d in DIRECTIONS]
    return SpyResult.model_validate(raw)


def to_out(rec: SpyInvestigation, plant_name: str | None, warnings: list[str] | None = None) -> SpyInvestigationOut:
    return SpyInvestigationOut(
        id=rec.id, plant_id=rec.plant_id, plant_name=plant_name, photo_url=rec.photo_url, photo_source=rec.photo_source,
        codename=rec.codename, mode=rec.mode, model=rec.model, result=SpyResult.model_validate(rec.result),
        crosscheck=[SpyCrosscheck.model_validate(c) for c in rec.crosscheck], image_stats=rec.image_stats,
        warnings=warnings or [], created_at=rec.created_at)


class SpyService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def investigate(self, data: bytes | None, plant_id: int | None, use_plant_photo: bool,
                    force_demo: bool = False) -> SpyInvestigationOut:
        now = datetime.now(timezone.utc)
        plant = None
        if plant_id is not None:
            plant = self.db.get(Plant, plant_id)
            if plant is None:
                raise SpyError(f"Растение {plant_id} не найдено", 404)
        if data is None and not (use_plant_photo and plant):
            raise SpyError("Загрузите фотографию или выберите фото растения из коллекции")

        img, photo_url, kind, warnings = None, None, "none", []
        if data is not None:
            try:
                img = normalized(open_image(data))
                exif = safe_exif(open_image(data))
            except ImageError as e:
                raise SpyError(str(e), 415 if "прочитать" in str(e) else 413)
            photo_url, kind = save_clean(img, self.settings.upload_dir, "spy"), "upload"
        else:
            exif = {}
            url = plant.photo_url or ""
            if url.startswith("/uploads/"):
                path = self.settings.upload_dir / url.removeprefix("/uploads/")
                if path.is_file():
                    img = normalized(open_image(path.read_bytes()))
                    photo_url, kind = url, "collection"
                else:
                    warnings.append("Файл фото растения не найден на сервере — расследование только по данным.")
            else:
                photo_url, kind = url or None, "illustration"
                warnings.append("У растения нет загруженной фотографии (только иллюстрация). Пиксельные улики не собирались.")

        stats = pixel_stats(img) if img is not None else None
        ctx = build_context(self.db, plant, now) if plant else None
        extras = {"owner": owner_stats(self.db, now)}

        mode, model = "demo", None
        raw = DemoSpyEngine().investigate(stats, exif, ctx, kind, extras)
        if self.settings.effective_ai_mode == "claude" and not force_demo:
            try:
                dossier_input = dict(plant_context=ctx, pixel_stats=stats, photo_metadata=exif, owner_care_stats=extras["owner"],
                                     photo_kind=kind, note="Если plant_context = null, фото не привязано к растению.")
                raw = ClaudeSpyEngine(self.settings).investigate(
                    to_base64_jpeg(img) if img is not None else None, "image/jpeg", dossier_input)
                mode, model = "claude", self.settings.claude_model
            except ClaudeUnavailable as e:
                warnings.insert(0, f"Claude недоступен ({e}); досье составлено в Demo-режиме.")
        try:
            result = _normalize(raw)
        except ValidationError:
            warnings.insert(0, "Ответ AI не прошёл проверку формата; досье составлено в Demo-режиме.")
            result, mode, model = _normalize(DemoSpyEngine().investigate(stats, exif, ctx, kind, extras)), "demo", None

        checks = crosscheck(self.db, plant, result.visual_estimates.model_dump())
        rec = SpyInvestigation(
            plant_id=plant.id if plant else None, photo_url=photo_url, photo_source=kind, codename=result.codename[:160],
            mode=mode, model=model, result=result.model_dump(mode="json"),
            crosscheck=[c.model_dump(mode="json") for c in checks],
            image_stats=(stats | {"exif": exif}) if stats else ({"exif": exif} if exif else None),
            context_snapshot=ctx, created_at=now)
        self.db.add(rec)
        self.db.commit()
        return to_out(rec, plant.name if plant else None, warnings)

    def history(self, plant_id: int | None = None, limit: int = 50) -> list[SpyInvestigationBrief]:
        q = select(SpyInvestigation).order_by(SpyInvestigation.created_at.desc()).limit(limit)
        if plant_id is not None:
            q = q.where(SpyInvestigation.plant_id == plant_id)
        names = {p.id: p.name for p in self.db.scalars(select(Plant))}
        return [SpyInvestigationBrief(id=r.id, plant_id=r.plant_id, plant_name=names.get(r.plant_id), photo_url=r.photo_url,
                                      photo_source=r.photo_source, codename=r.codename, summary=r.result.get("summary", ""),
                                      mode=r.mode, created_at=r.created_at)
                for r in self.db.scalars(q)]

    def get(self, inv_id: int) -> SpyInvestigationOut:
        rec = self.db.get(SpyInvestigation, inv_id)
        if rec is None:
            raise SpyError("Расследование не найдено", 404)
        plant = self.db.get(Plant, rec.plant_id) if rec.plant_id else None
        return to_out(rec, plant.name if plant else None)
