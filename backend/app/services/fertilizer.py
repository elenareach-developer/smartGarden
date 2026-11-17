"""Fertilizer Advisor — оценка применимости удобрения, указанного пользователем.

Правила:
  * система не назначает удобрение и не придумывает состав или дозировку;
  * дозировку определяет инструкция производителя;
  * при повреждённых корнях или признаках обезвоживания подкормка не рекомендуется без доп. оценки.
"""
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..domain.metrics import LEAF_LABELS, ROOT_LABELS, STAGE_LABELS, LeafStatus, Metric, RootStatus, Stage
from ..models import CareEvent, Fertilizer, FertilizerApplication, Plant
from ..providers.registry import provider_for
from ..schemas import ApplicationOut, Assessment, FertilizerIn, FertilizerOut, PlannedTask

VERDICT_LABELS = {
    "suitable": "Подходит сейчас",
    "conditional": "Подходит с оговорками",
    "not_now": "Сейчас не рекомендуется",
    "insufficient_data": "Недостаточно данных для оценки",
}


def last_application(db: Session, plant_id: int) -> FertilizerApplication | None:
    return db.scalars(select(FertilizerApplication).where(FertilizerApplication.plant_id == plant_id)
                      .order_by(FertilizerApplication.applied_at.desc()).limit(1)).first()


def composition_type(f: Fertilizer) -> str | None:
    n, p, k = f.npk_n, f.npk_p, f.npk_k
    if None in (n, p, k):
        return None
    if n + p + k == 0:
        return "без NPK (стимулятор/микроэлементы)"
    hi, lo = max(n, p, k), min(n, p, k)
    if lo > 0 and hi / lo <= 1.5:
        return "сбалансированное"
    if n >= p and n >= k:
        return "с преобладанием азота"
    return "с преобладанием фосфора и калия"


def assess(db: Session, plant: Plant, fert: Fertilizer, stage: str | None = None,
           last_fertilized_at: datetime | None = None, now: datetime | None = None) -> Assessment:
    now = now or datetime.now(timezone.utc)
    stage = stage or plant.stage
    reasons, precautions, blockers, questions, used = [], [], [], [], []
    ctype = composition_type(fert)

    used.append(f"Стадия: {STAGE_LABELS[Stage(stage)]}")
    used.append(f"Корни: {ROOT_LABELS[RootStatus(plant.root_status)].split(':')[0].lower()}, "
                f"листья: {LEAF_LABELS[LeafStatus(plant.leaf_status)].split(',')[0].lower()}"
                + (f" (осмотр {plant.observed_at:%d.%m.%Y})" if plant.observed_at else " (осмотров не было)"))

    # 1. Состав
    if ctype is None:
        questions.append("Укажите состав NPK с этикетки (например, 4-6-6) — без него оценить удобрение нельзя.")
    else:
        used.append(f"NPK {fert.npk_n:g}-{fert.npk_p:g}-{fert.npk_k:g}: {ctype}")
    if fert.labeled_for_orchids is None:
        questions.append("Есть ли на упаковке указание, что удобрение предназначено для орхидей?")
    elif not fert.labeled_for_orchids:
        precautions.append("Удобрение не предназначено специально для орхидей: корни орхидей чувствительны к "
                           "концентрации солей. Используйте только если производитель приводит схему для орхидей "
                           "или эпифитов; без неё — проконсультируйтесь со специалистом.")
    if not fert.manufacturer_instructions:
        questions.append("Внесите инструкцию производителя (разведение и частоту) — дозировку определяет только она.")
    else:
        used.append("Инструкция производителя внесена пользователем")
    if fert.micronutrients:
        used.append(f"Микроэлементы: {fert.micronutrients}")

    # 2. Блокирующие условия
    if plant.root_status in ("damaged", "rotting"):
        blockers.append("Корни повреждены или есть признаки гнили: соли удобрения могут обжечь ослабленные корни. "
                        "Сначала нужна оценка состояния корней и появление новых здоровых кончиков.")
    if plant.root_status == "dry" or plant.leaf_status == "wrinkled":
        blockers.append("Есть признаки обезвоживания (пересушенные корни или потеря тургора). Подкормка по сухому "
                        "субстрату опасна; сначала выясните причину и восстановите водный баланс.")
    sm = provider_for(plant).latest(db, plant, Metric.substrate_moisture) \
        if Metric.substrate_moisture in provider_for(plant).available_metrics(db, plant) else None
    if sm and sm.value < plant.substrate_min:
        blockers.append(f"Субстрат сухой ({sm.value:.0f} % на {sm.timestamp:%d.%m %H:%M} UTC): удобрения вносят "
                        "только по влажному субстрату, после обычного полива.")
    if sm:
        used.append(f"Влажность субстрата {sm.value:.0f} % ({sm.source})")
    if stage == "resting":
        blockers.append("Период покоя: в это время подкормки обычно прекращают.")

    la = last_application(db, plant.id)
    last = last_fertilized_at or (la.applied_at if la else None)
    if last:
        days = (now - last).total_seconds() / 86400
        used.append(f"Последняя подкормка: {last:%d.%m.%Y} ({days:.0f} дн. назад)")
        if days < plant.fertilizing_interval_days * 0.75:
            blockers.append(f"С последней подкормки прошло {days:.0f} дн. при интервале "
                            f"{plant.fertilizing_interval_days:g} дн. — рано.")
    else:
        questions.append("Когда была последняя подкормка? В журнале нет записей.")

    # 3. Соответствие стадии
    when = ""
    if ctype:
        if stage in ("vegetative", "recovery"):
            if ctype == "с преобладанием фосфора и калия":
                reasons.append("На стадии роста листьев и корней обычно используют сбалансированные составы; "
                               "фосфорно-калийные чаще применяют перед закладкой цветоноса.")
                when = "Лучше отложить до окончания роста нового листа/псевдобульба, ближе к закладке цветоноса."
            else:
                reasons.append(f"Состав ({ctype}) соответствует стадии активного роста.")
                when = "В период активного роста — после полива, с интервалом из инструкции производителя."
        elif stage == "spike":
            if ctype == "с преобладанием азота":
                reasons.append("Во время роста цветоноса избыток азота стимулирует листья в ущерб цветению.")
                when = "Предпочтительнее сбалансированный или фосфорно-калийный состав."
            else:
                reasons.append(f"Состав ({ctype}) уместен в период роста цветоноса.")
                when = "Во время роста цветоноса, по влажному субстрату."
        elif stage == "blooming":
            reasons.append("Во время цветения многие производители рекомендуют снизить частоту подкормок или "
                           "сделать паузу — проверьте это в инструкции.")
            if ctype == "с преобладанием азота":
                reasons.append("Азотный состав во время цветения нежелателен.")
            when = "Если инструкция допускает подкормку во время цветения — только по её схеме, без превышения."
        elif stage == "resting":
            when = "После окончания периода покоя, когда начнётся новый рост."
        total = (fert.npk_n or 0) + (fert.npk_p or 0) + (fert.npk_k or 0)
        if total >= 30:
            precautions.append(f"Концентрат (сумма NPK {total:g} %): строго соблюдайте разведение из инструкции, "
                               "ошибка в дозировке легко приводит к ожогу корней.")

    precautions += [
        "Вносите удобрение только по предварительно увлажнённому субстрату.",
        "Не превышайте дозировку производителя; при сомнении выбирайте меньшую из указанных.",
        "Раз в месяц промывайте субстрат чистой водой, чтобы не накапливались соли.",
        "Следите за кончиками корней: потемнение после подкормки — повод прекратить её.",
    ]

    if blockers:
        verdict = "not_now"
        when = when or "После устранения причин, перечисленных выше, и повторной оценки."
    elif ctype is None:
        verdict = "insufficient_data"
        when = when or "Оценка будет возможна после ввода состава."
    elif questions or precautions[:-4] or any("нежелателен" in r or "отложить" in when for r in reasons) \
            or stage == "blooming":
        verdict = "conditional"
    else:
        verdict = "suitable"

    return Assessment(verdict=verdict, verdict_label=VERDICT_LABELS[verdict], composition_type=ctype,
                      reasons=reasons, when_to_use=when or "По инструкции производителя.",
                      precautions=precautions, blockers=blockers, questions=questions, data_used=used)


def get_or_create(db: Session, fertilizer_id: int | None, data: FertilizerIn | None) -> Fertilizer:
    if fertilizer_id is not None:
        f = db.get(Fertilizer, fertilizer_id)
        if f is None:
            raise LookupError("Удобрение не найдено")
        return f
    f = Fertilizer(**data.model_dump())
    db.add(f)
    db.flush()
    return f


def record(db: Session, plant: Plant, fert: Fertilizer, applied_at: datetime | None, dilution: str | None,
           notes: str | None, stage: str) -> FertilizerApplication:
    ts = applied_at or datetime.now(timezone.utc)
    ev = CareEvent(plant_id=plant.id, event_type="fertilizing", timestamp=ts, source="user",
                   notes=f"Подкормка: {fert.name}" + (f". {notes}" if notes else ""))
    db.add(ev)
    db.flush()
    app = FertilizerApplication(plant_id=plant.id, fertilizer_id=fert.id, care_event_id=ev.id, applied_at=ts,
                                dilution=dilution, stage_at_application=stage, notes=notes, source="user")
    db.add(app)
    db.flush()
    return app


def application_out(a: FertilizerApplication) -> ApplicationOut:
    return ApplicationOut(id=a.id, fertilizer=FertilizerOut.model_validate(a.fertilizer), applied_at=a.applied_at,
                          dilution=a.dilution, stage_at_application=a.stage_at_application, notes=a.notes,
                          source=a.source)


def next_window(db: Session, plant: Plant, now: datetime) -> PlannedTask:
    la = last_application(db, plant.id)
    blockers = []
    if plant.root_status in ("damaged", "rotting"):
        blockers.append("корни повреждены")
    if plant.leaf_status == "wrinkled" or plant.root_status == "dry":
        blockers.append("признаки обезвоживания")
    if plant.stage == "resting":
        blockers.append("период покоя")
    due = (la.applied_at + timedelta(days=plant.fertilizing_interval_days)) if la else now
    if blockers:
        return PlannedTask(task="fertilizing", title="Подкормка отложена", due_at=None, kind="derived",
                           explanation="Не планируется: " + ", ".join(blockers) + ". Нужна повторная оценка.")
    return PlannedTask(task="fertilizing", title="Окно для подкормки", due_at=max(due, now), kind="derived",
                       explanation=(f"Интервал {plant.fertilizing_interval_days:g} дн. от последней подкормки. "
                                    "Это напоминание, а не назначение: проверьте состояние растения и "
                                    "оцените удобрение в Fertilizer Advisor."))
