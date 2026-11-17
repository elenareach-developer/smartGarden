"""Demo AI Mode: экспертные правила без языковой модели. Работает без API-ключа.

Ответ строится только из контекста растения: каждый вывод ссылается на измерение
или наблюдение, а отсутствующие данные перечисляются явно.
"""
from datetime import datetime

from ...schemas import Assessment

TOPIC_TITLES = {
    "feeding": "Чем подкормить?", "watering": "Когда поливать?", "yellow_leaves": "Почему желтеют листья?",
    "no_bloom": "Почему не цветёт?", "roots": "Как стимулировать рост корней?",
    "disease": "Есть ли признаки заболевания?", "conditions": "Как изменить условия ухода?",
    "fertilizer": "Оценка удобрения", "general": "Вопрос о растении",
}

KEYWORDS = [
    ("yellow_leaves", ["желте", "жёлт", "желт"]),
    ("no_bloom", ["цвет", "цветонос", "бутон"]),
    ("roots", ["корн", "корен"]),
    ("disease", ["болез", "пятн", "гнил", "вредит", "клещ", "грибок", "инфекц"]),
    ("feeding", ["подкорм", "удобр", "питан"]),
    ("watering", ["полив", "поливать", "вода", "влажн"]),
    ("conditions", ["услови", "переставить", "свет", "температур", "лампа"]),
]


def detect_topic(question: str) -> str:
    q = question.lower()
    for topic, words in KEYWORDS:
        if any(w in q for w in words):
            return topic
    return "general"


def _m(ctx: dict, metric: str):
    for m in ctx["measured"]:
        if m["metric"] == metric and m.get("source") != "manual":
            return m
    return None


UNITS = {"h": "ч", "g": "г"}


def _fmt(m: dict) -> str:
    t = datetime.fromisoformat(m["timestamp"])
    v = m["value"]
    val = f"{v:.0f}" if abs(v) >= 100 else f"{v:.1f}"
    lo, hi = (m.get("target") or [None, None])
    unit = UNITS.get(m["unit"], m["unit"])
    label = m["label"]
    rng = f" (цель {lo:g}–{hi:g})" if lo is not None and hi is not None else ""
    if m["metric"] == "light":
        label, rng = "Освещённость в момент измерения", ""   # цель задана для средней дневной
    return f"{label}: **{val} {unit}**{rng}, {t:%d.%m %H:%M} UTC, источник `{m['source']}`"


def _days_since(iso: str | None, now: datetime) -> float | None:
    if not iso:
        return None
    return (now - datetime.fromisoformat(iso)).total_seconds() / 86400


class DemoEngine:
    def answer(self, ctx: dict, topic: str, question: str, assessment: Assessment | None = None) -> dict:
        if topic == "general":
            topic = detect_topic(question)
        now = datetime.fromisoformat(ctx["now"])
        p = ctx["plant"]
        facts, analysis, recs, questions, warnings = [], [], [], [], []

        t, h, light = _m(ctx, "temperature"), _m(ctx, "air_humidity"), _m(ctx, "light")
        photo, sub, w = _m(ctx, "photoperiod"), _m(ctx, "substrate_moisture"), _m(ctx, "pot_weight")
        for m in (t, h, light, photo, sub, w):
            if m:
                facts.append(_fmt(m) + (f" — {m['status_text']}" if m.get("status_text") and m["metric"] in ("light", "photoperiod") else ""))
        facts.append(f"Корни: {p['root_label']}; листья: {p['leaf_label']}"
                     + (f" (осмотр {datetime.fromisoformat(p['observed_at']):%d.%m})" if p["observed_at"] else ""))
        waterings = ctx["care"]["waterings"]
        last_w = waterings[-1]["t"] if waterings else None
        dw = _days_since(last_w, now)
        if dw is not None:
            facts.append(f"Последний полив {dw:.0f} дн. назад; поливов за 45 дней: {len(waterings)}")
        lf = ctx["care"]["last_fertilizer"]
        df = _days_since(lf["applied_at"], now) if lf else None
        if lf:
            facts.append(f"Последняя подкормка {df:.0f} дн. назад: {lf['name']}")

        roots_bad = p["root_status"] in ("damaged", "rotting")
        dehydrated = p["leaf_status"] == "wrinkled" or p["root_status"] == "dry"
        hum_low = h and h["status"] == "low"
        light_low = light and light["status"] == "low"
        photo_low = photo and photo["status"] == "low"
        hot = t and t["status"] == "high"

        if topic == "watering":
            wc = ctx["forecast_7d"]["watering_check"]
            if wc["at"]:
                at = datetime.fromisoformat(wc["at"])
                analysis.append(f"Расчётное время следующей проверки: **{at:%d.%m %H:%M} UTC** "
                                f"(уверенность: {wc['confidence']}). {wc['explanation']}")
            if sub:
                analysis.append("Ориентируйтесь на датчик влажности субстрата: полив нужен, когда значение "
                                "подходит к нижней границе диапазона.")
            elif w:
                analysis.append("Масса горшка — надёжный косвенный показатель: чем ближе к массе сухого горшка, тем суше субстрат.")
            else:
                analysis.append("Датчика влажности субстрата и весов нет, поэтому срок рассчитан по журналу поливов — "
                                "это ориентир для проверки, а не команда полить.")
                questions.append("Какого цвета корни в прозрачном горшке: серебристые (сухо) или зелёные (влажно)?")
                questions.append("Горшок заметно легче, чем сразу после полива?")
            recs += ["Поливайте после просыхания субстрата: у орхидей вредно и пересушивание, и постоянная сырость.",
                     "Тёплая отстоянная или фильтрованная вода; после полива слейте излишки из поддона.",
                     "Не оставляйте воду в розетке и пазухах листьев."]
            if roots_bad:
                warnings.append("Корни повреждены: при малом количестве корней субстрат сохнет медленнее, "
                                "и полив «по расписанию» повышает риск гнили.")
                recs.insert(0, "Поливайте реже и меньшим объёмом, а потерю влаги листьями компенсируйте влажностью воздуха.")
            if hum_low:
                recs.append("Повышайте влажность воздуха (поддон с влажным керамзитом, увлажнитель) — это снижает потерю воды.")

        elif topic in ("feeding", "fertilizer"):
            if assessment:
                analysis.append(f"Оценка удобрения: **{assessment.verdict_label}**"
                                + (f", тип состава — {assessment.composition_type}" if assessment.composition_type else ""))
                analysis += assessment.reasons
                if assessment.blockers:
                    warnings += assessment.blockers
                analysis.append(f"Когда использовать: {assessment.when_to_use}")
                recs += assessment.precautions
                questions += assessment.questions
            else:
                analysis.append(f"Стадия: {p['stage_label']}.")
                if p["stage"] in ("vegetative", "recovery"):
                    analysis.append("В период роста листьев и корней обычно выбирают сбалансированный состав NPK.")
                elif p["stage"] == "spike":
                    analysis.append("Во время роста цветоноса уместны сбалансированные или фосфорно-калийные составы.")
                elif p["stage"] == "blooming":
                    analysis.append("Во время цветения подкормки обычно сокращают; следуйте инструкции производителя.")
                else:
                    analysis.append("В период покоя подкормки обычно прекращают.")
                if df is not None:
                    interval = p["targets"]["fertilizing_interval_days"]
                    analysis.append(f"С последней подкормки прошло {df:.0f} дн. при интервале {interval:g} дн."
                                    + (" — рано." if df < interval * 0.75 else ""))
                recs.append("Откройте Fertilizer Advisor и внесите удобрение, которое у вас есть: название, NPK, "
                            "микроэлементы и инструкцию производителя — я оценю его применимость.")
                recs.append("Я не назначаю конкретный препарат и не рассчитываю дозировку: дозу определяет только инструкция производителя.")
                questions.append("Какое удобрение есть у вас дома и какой состав NPK указан на этикетке?")
            if roots_bad or dehydrated:
                warnings.append("Подкормка сейчас не рекомендуется без дополнительной оценки: "
                                + ("корни повреждены" if roots_bad else "есть признаки обезвоживания")
                                + ". Сначала нужны новые здоровые корни и восстановление тургора.")

        elif topic == "yellow_leaves":
            causes = []
            if p["leaf_status"] == "yellowing" or "желтеет" in (ctx["care"]["other"][-1]["notes"] if ctx["care"]["other"] else ""):
                analysis.append("Пожелтение листьев отмечено в наблюдениях.")
            if roots_bad:
                causes.append("**Повреждённые корни** — самая вероятная причина: растение не может обеспечить все листья "
                              "водой и питанием и «жертвует» нижними.")
            if hum_low and hot:
                causes.append("**Сухой тёплый воздух** (по измерениям) усиливает потерю воды.")
            elif hum_low:
                causes.append("**Сухой воздух** по измерениям ниже целевого диапазона.")
            if light_low:
                causes.append("**Недостаток света** может давать бледность листьев.")
            causes.append("**Естественное старение**: если желтеет один нижний лист раз в год-два, а остальные упругие — это норма.")
            analysis += causes
            questions += ["Желтеет нижний лист или верхние/молодые?",
                          "Лист жёлтый равномерно и мягкий, или есть пятна, мокрые участки, запах?",
                          "Когда последний раз смотрели корни?"]
            recs += ["Не обрывайте желтеющий лист, пока он не высохнет полностью — растение забирает из него питательные вещества.",
                     "Если жёлтые участки мокрые или тёмные — изолируйте растение и осмотрите корни."]
            if hum_low:
                recs.append("Поднимите влажность воздуха до целевого диапазона.")

        elif topic == "no_bloom":
            if p["stage"] == "blooming":
                analysis.append("Растение сейчас цветёт — вопрос о стимуляции цветения пока неактуален.")
            if light_low:
                analysis.append(f"Главный фактор по данным — **освещённость ниже нормы**: {light['status_text']}.")
            if photo_low:
                analysis.append(f"**Короткий световой день**: {photo['value']:.1f} ч при нужных "
                                f"≥ {p['targets']['photoperiod'][0]:g} ч.")
            if not light:
                analysis.append("Датчика освещённости нет, поэтому оценить свет по данным нельзя.")
                questions.append("Где стоит растение и сколько часов в день на него попадает яркий рассеянный свет?")
            analysis.append("Для закладки цветоноса многим орхидеям нужна разница дневной и ночной температур "
                            "около 4–6 °C в течение нескольких недель.")
            if t:
                analysis.append("Суточную амплитуду температуры можно оценить на графике Monitoring за 7 дней.")
            if roots_bad or dehydrated:
                analysis.append("Ослабленное растение сначала восстанавливает корни и листья — цветения в этот период ждать не стоит.")
            recs += ["Обеспечьте 11–12 часов яркого рассеянного света (при необходимости — фитолампа по таймеру).",
                     "Осенью несколько недель держите ночью на 4–6 °C прохладнее, чем днём, без сквозняков.",
                     "Не перекармливайте азотом: он стимулирует листья, а не цветоносы."]
            questions.append("Сколько времени прошло с последнего цветения?")

        elif topic == "roots":
            analysis.append(f"Состояние корней по последнему осмотру: {p['root_label']}.")
            if roots_bad:
                analysis.append("Сейчас приоритет — условия для появления новых корней, а не питание.")
            if t:
                analysis.append(f"Температура {t['value']:.1f} °C — " + (
                    "тепло помогает росту корней, но перегрев выше нормы ослабляет растение." if hot else
                    "в допустимом диапазоне для роста корней."))
            if hum_low:
                analysis.append("Влажность воздуха ниже нормы: новым корням и листьям сложнее, растение теряет воду.")
            recs += ["Свободный, хорошо аэрируемый субстрат; горшок по размеру корней, а не «на вырост».",
                     "Стабильное тепло без перегрева, яркий рассеянный свет.",
                     "Полив только после просыхания субстрата; между поливами корни должны «дышать».",
                     "Повышенная влажность воздуха (50–70 %) снижает нагрузку на оставшиеся корни.",
                     "Не применяйте удобрения и стимуляторы, пока корни повреждены, без консультации и инструкции производителя."]
            questions.append("Есть ли новые зелёные кончики корней? Сколько их и какой длины?")

        elif topic == "disease":
            analysis.append("По датчикам нельзя диагностировать болезнь — нужны визуальные признаки.")
            if p["root_status"] == "rotting":
                warnings.append("В наблюдениях отмечены признаки гнили корней.")
            if p["leaf_status"] == "spots":
                warnings.append("В наблюдениях отмечены пятна на листьях.")
            if hum_low and t and t["value"] > 24:
                analysis.append("Тёплый сухой воздух — условия, в которых чаще появляется паутинный клещ.")
            analysis.append("Высокая влажность при низкой температуре и плохой циркуляции воздуха способствует грибковым гнилям.")
            questions += ["Есть ли пятна? Какие: сухие, мокрые, с жёлтым ободком, растут ли?",
                          "Есть ли липкий налёт, паутинка, белые «ватки» в пазухах?",
                          "Есть ли неприятный запах от субстрата?",
                          "Можете приложить фото листьев и корней? (функция загрузки фото — в профиле растения)"]
            recs += ["При подозрении на инфекцию изолируйте растение от других орхидей.",
                     "Для выбора препарата обратитесь к специалисту или в садовый центр с фото; "
                     "применяйте препараты строго по инструкции производителя."]

        else:  # conditions / прочее
            for m, name, adv in [
                (t, "Температура", "держите в целевом диапазоне; ночью на несколько градусов прохладнее"),
                (h, "Влажность воздуха", "увлажнитель или поддон с влажным керамзитом; подальше от радиатора"),
                (light, "Освещённость", "ближе к светлому окну или фитолампа по таймеру; без прямого полуденного солнца"),
                (photo, "Световой день", "досветка до 11–12 часов"),
            ]:
                if m and m["status"] in ("low", "high"):
                    recs.append(f"{name} {'ниже' if m['status'] == 'low' else 'выше'} нормы — {adv}.")
            if not recs:
                analysis.append("Измеряемые условия в целевых диапазонах — менять режим не требуется.")
            for r in ctx["forecast_7d"]["risks"][:4]:
                analysis.append(f"Риск «{r['title']}» ({r['level']}, {r['kind']}): {r['explanation']}")

        analysis.append(f"Сезонность: {ctx['season_note']}")
        missing = list(ctx["missing_measurements"])
        if not questions:
            questions.append("Замечали ли изменения во внешнем виде растения за последнюю неделю?")

        title = TOPIC_TITLES.get(topic, "Вопрос о растении")
        md = [f"## {title} — {p['name']}", ""]
        if ctx["is_demo"]:
            md += ["> Данные мониторинга — **DEMO** (смоделированы). Ответ сформирован в **Demo AI Mode** "
                   "по экспертным правилам, без языковой модели.", ""]
        md += ["### Что я вижу в данных"] + [f"- {f}" for f in facts] + [""]
        if warnings:
            md += ["### ⚠️ Важно"] + [f"- {x}" for x in warnings] + [""]
        md += ["### Анализ"] + [f"- {x}" for x in analysis] + [""]
        if recs:
            md += ["### Рекомендации"] + [f"{i}. {x}" for i, x in enumerate(recs, 1)] + [""]
        md += ["### Уточняющие вопросы"] + [f"- {x}" for x in questions] + [""]
        if missing:
            md += ["### Каких данных нет", "Я не делаю выводов по этим показателям: " + ", ".join(missing) + "."]
        return dict(answer="\n".join(md), topic=topic, clarifying_questions=questions, data_used=facts,
                    missing_data=missing, warnings=warnings)
