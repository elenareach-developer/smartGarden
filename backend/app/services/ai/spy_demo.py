"""Demo-движок Botanical Spy. Работает без API-ключа и без языковой модели.

Он не «видит» объекты на фото. Факты берутся из пиксельных измерений, профиля растения, датчиков и
журнала ухода; всё, что требует настоящего зрения (насекомые, паутина, другие растения), явно
помечается как неизвестное."""
from datetime import datetime

# Справочник родов: естественный ареал и условия. Источник — общие ботанические сведения (source=knowledge).
GENERA = {
    "phalaenopsis": dict(name="Фаленопсис (Phalaenopsis)", range="Юго-Восточная Азия: Филиппины, Индонезия, Индокитай, север Австралии",
                         zone="влажные тропики (Af/Am по Кёппену), равнинные и предгорные леса", habit="эпифит в тени полога",
                         temp="18–30 °C, ночью на 4–6 °C прохладнее", humidity="60–80 %", light="рассеянный свет, без прямого солнца"),
    "cattleya": dict(name="Каттлея (Cattleya)", range="Центральная и Южная Америка, особенно Атлантический лес Бразилии",
                     zone="тропики и субтропики с сухим сезоном (Aw/Cfa)", habit="эпифит на открытых, светлых ветвях",
                     temp="18–30 °C, заметная ночная разница", humidity="50–70 %", light="яркий свет, утреннее солнце"),
    "oncidium": dict(name="Онцидиум (Oncidium)", range="Неотропики: от Мексики до Бразилии и Анд",
                     zone="от тёплых низин до прохладных туманных горных лесов (Af/Cwb)", habit="эпифит, часто в туманных лесах",
                     temp="16–26 °C", humidity="55–75 %", light="яркий рассеянный свет"),
    "dendrobium": dict(name="Дендробиум (Dendrobium)", range="Азия, Австралия, Океания", zone="от муссонных тропиков до гор (Am/Cwa)",
                       habit="эпифит; у многих видов выраженный сухой прохладный сезон", temp="15–28 °C", humidity="50–70 %",
                       light="яркий свет"),
    "paphiopedilum": dict(name="Пафиопедилум (Paphiopedilum)", range="Юго-Восточная Азия, Гималаи", zone="влажные тропики и горы",
                          habit="наземный/литофит в лесной подстилке", temp="16–26 °C", humidity="60–75 %", light="тень, рассеянный свет"),
    "cymbidium": dict(name="Цимбидиум (Cymbidium)", range="Гималаи, Китай, Юго-Восточная Азия, Австралия", zone="субтропические горы (Cwb)",
                      habit="наземный и эпифит", temp="10–25 °C, прохладные ночи для цветения", humidity="50–65 %", light="очень яркий свет"),
    "vanda": dict(name="Ванда (Vanda)", range="Тропическая Азия", zone="жаркие влажные тропики (Af)", habit="эпифит на солнечных ветвях",
                  temp="20–32 °C", humidity="70–85 %", light="много яркого света"),
}

SENSOR_TIPS = {
    "climate": [("SHT31 / DHT22", "проверить температуру и влажность воздуха у растения"),
                ("BH1750", "измерить освещённость и световой день")],
    "scene": [("BH1750", "отличить дневной свет от лампы по суточному ходу освещённости"),
              ("ESP32-CAM", "серия снимков в разное время суток — тени покажут ориентацию окна")],
    "biology": [("Клеевые ловушки + макросъёмка", "выявить летающих вредителей и трипсов"),
                ("SHT31", "сухой тёплый воздух — фактор риска паутинного клеща")],
    "owner": [("Журнал ухода в приложении", "регулярные записи покажут реальный ритм ухода"),
              ("HX711", "весы под горшком объективно покажут, как часто субстрат пересыхает")],
}


def genus_of(species: str | None) -> dict | None:
    s = (species or "").lower()
    return next((v for k, v in GENERA.items() if k in s), None)


def _h(text, conf, evidence, verify):
    return dict(text=text, confidence=conf, evidence=evidence, how_to_verify=verify)


def _pad(hyps: list[dict], extra: list[dict]) -> list[dict]:
    for e in extra:
        if len(hyps) >= 3:
            break
        hyps.append(e)
    return hyps[:3]


def _metric(ctx: dict | None, key: str):
    if not ctx:
        return None
    return next((m for m in ctx["measured"] if m["metric"] == key and m.get("source") != "manual"), None)


class DemoSpyEngine:
    def investigate(self, stats: dict | None, exif: dict, ctx: dict | None, photo_kind: str, extras: dict) -> dict:
        p = ctx["plant"] if ctx else None
        genus = genus_of(p["species"]) if p else None
        no_vision = "В Demo-режиме объекты на фото не распознаются: нужен Claude (ANTHROPIC_API_KEY)."

        # ---------- Climate ----------
        cf, ch = [], []
        if p:
            cf.append(dict(text=f"По профилю: {p['name']} — {p['species']}" + (f", {p['variety']}" if p['variety'] else ""), source="profile"))
        if genus:
            cf += [dict(text=f"Естественный ареал рода: {genus['range']}", source="knowledge"),
                   dict(text=f"Типичные условия: {genus['temp']}, влажность {genus['humidity']}, {genus['light']}", source="knowledge")]
            ch.append(_h(f"Климатическая зона «родины» — {genus['zone']}; образ жизни: {genus['habit']}", "высокая",
                         [f"род {genus['name']} в профиле"], "Сверить вид по атласу орхидей или через Claude-vision по фото цветка"))
        for key, label in (("temperature", "Температура"), ("air_humidity", "Влажность воздуха")):
            m = _metric(ctx, key)
            if m:
                cf.append(dict(text=f"{label} у растения: {m['value']:.1f} {m['unit']} ({m['timestamp'][:16].replace('T', ' ')} UTC, {m['source']})", source="sensor"))
        hum = _metric(ctx, "air_humidity")
        if genus and hum:
            lo = int(genus["humidity"].split("–")[0])
            if hum["value"] < lo:
                ch.append(_h(f"Растение живёт суше, чем на родине: {hum['value']:.0f} % против {genus['humidity']}", "высокая",
                             ["показания датчика", "справочные данные рода"], "Понаблюдать за тургором листьев и кончиками корней 2 недели"))
            else:
                ch.append(_h("Влажность воздуха близка к природной для рода", "средняя", ["показания датчика"],
                             "Проверить ночные минимумы на графике за 7 дней"))
        if stats:
            if stats["magenta_share"] > 0.04:
                ch.append(_h("Растение выращивается под фитолампой, т.е. в помещении", "средняя",
                             [f"доля пурпурных пикселей {stats['magenta_share']:.1%}"], "Сравнить снимки при выключенной лампе"))
            elif stats["warmth"] > 18:
                ch.append(_h("Снимок сделан при тёплом искусственном свете — вероятно, в помещении", "низкая",
                             [f"тёплый баланс белого (R−B = {stats['warmth']:.0f})"], "Сделать фото днём у окна"))
        ch = _pad(ch, [
            _h("Среда выращивания — комнатная культура в горшке", "средняя" if p else "низкая",
               ["профиль растения" if p else "типично для орхидей в коллекциях"], "Указать место в профиле растения"),
            _h("Без датчиков нельзя отличить постоянный климат от случайного дня", "низкая", ["единичный снимок"],
               "Поставить SHT31 и BH1750 хотя бы на неделю"),
            _h("Растение может быть гибридом, а у гибридов условия шире, чем у природного вида", "низкая",
               ["большинство орхидей в продаже — гибриды"], "Найти этикетку/сорт при покупке"),
        ])
        cu = ["Точный вид и сорт без фото цветка крупным планом", "Климат за пределами кадра (сквозняки, радиатор, окно)"]
        if not genus:
            cu.insert(0, "Вид растения: " + ("в Demo-режиме определяется только по профилю" if not p else "род не найден в справочнике"))

        # ---------- Scene ----------
        sf, sh = [], []
        if stats:
            sf += [dict(text=f"Размер снимка {stats['width']}×{stats['height']} px, средняя яркость {stats['brightness']:.0f}/255, контраст {stats['contrast']:.0f}", source="pixel_stats"),
                   dict(text=f"Баланс белого: R−B = {stats['warmth']:+.0f} ({'тёплый' if stats['warmth'] > 8 else 'холодный' if stats['warmth'] < -8 else 'нейтральный'}); насыщенность {stats['saturation']:.0f}/255", source="pixel_stats"),
                   dict(text=f"Зелёные пиксели: {stats['green_share']:.0%}; пересвеченные: {stats['overexposed_share']:.1%}; тёмные: {stats['dark_share']:.0%}", source="pixel_stats")]
            if stats["overexposed_share"] > 0.05 and stats["contrast"] > 60:
                sh.append(_h("Жёсткий свет: прямое солнце или вспышка", "средняя",
                             [f"пересвечено {stats['overexposed_share']:.0%} кадра", f"контраст {stats['contrast']:.0f}"],
                             "Посмотреть, есть ли резкие тени на фото"))
            if stats["brightness"] < 70 or stats["dark_share"] > 0.35:
                sh.append(_h("Съёмка при слабом освещении: вечер или глубина комнаты", "средняя",
                             [f"яркость {stats['brightness']:.0f}/255"], "Сопоставить со временем съёмки и датчиком света"))
            if stats["green_share"] > 0.45:
                sh.append(_h("В кадре много зелени — возможно, рядом другие растения или теплица", "низкая",
                             [f"зелёные пиксели {stats['green_share']:.0%}"], "Claude-vision или фото общего плана"))
        if exif.get("taken_at_local"):
            t = datetime.fromisoformat(exif["taken_at_local"])
            sf.append(dict(text=f"Время съёмки по метаданным: {t:%d.%m.%Y %H:%M}", source="photo"))
            if not 7 <= t.hour < 19:
                sh.append(_h("Свет на фото — искусственный (снято в тёмное время суток)", "средняя",
                             [f"время съёмки {t:%H:%M}"], "Сравнить с дневным снимком"))
        if exif.get("flash_fired"):
            sf.append(dict(text="Метаданные: при съёмке сработала вспышка", source="photo"))
        if p and p.get("location"):
            sf.append(dict(text=f"По профилю: {p['location']}", source="profile"))
            sh.append(_h("Растение в помещении на подоконнике/полке (по профилю)", "высокая", ["место в профиле"],
                         "Сверить с фото общего плана"))
        if p and p.get("pot"):
            sf.append(dict(text=f"Ёмкость по профилю: {p['pot']}; субстрат: {p.get('substrate') or 'не указан'}", source="profile"))
        sh = _pad(sh, [
            _h("Съёмка в помещении", "низкая", ["большинство фото комнатных орхидей"], "Фото с окном или интерьером в кадре"),
            _h("Признаков теплицы по пиксельной статистике не обнаружить", "низкая", ["ограничение Demo-режима"], "Claude-vision"),
            _h("Освещение смешанное: окно + лампы", "низкая", ["типично для квартир"], "Датчик BH1750: суточный профиль покажет источники"),
        ])

        # ---------- Biology ----------
        bf, bh = [], []
        if p:
            bf.append(dict(text=f"Наблюдение владельца: листья — {p['leaf_label'].lower()}; корни — {p['root_label'].lower()}"
                                + (f" (осмотр {p['observed_at'][:10]})" if p.get("observed_at") else ""), source="observation"))
            for e in (ctx["care"]["other"] if ctx else [])[-3:]:
                if e.get("notes"):
                    bf.append(dict(text=f"Журнал ({e['type']}, {e['t'][:10]}): {e['notes']}", source="care_history"))
            if p["leaf_status"] == "wrinkled":
                bh.append(_h("Морщинистые листья — скорее водный стресс, чем вредители", "средняя",
                             ["наблюдение: потеря тургора", "состояние корней: " + p["root_status"]],
                             "Осмотреть корни и нижнюю сторону листьев с лупой"))
            if p["leaf_status"] == "spots":
                bh.append(_h("Пятна могут быть грибковыми, бактериальными или следами солнечного ожога", "низкая",
                             ["наблюдение: пятна"], "Макрофото пятен; изоляция растения до выяснения"))
        if hum and hum["value"] < 45 and (_metric(ctx, "temperature") or {}).get("value", 0) > 24:
            bh.append(_h("Сухой тёплый воздух создаёт условия для паутинного клеща", "средняя",
                         ["показания датчиков: тепло и сухо"], "Протереть нижнюю сторону листа белой салфеткой"))
        bh = _pad(bh, [
            _h("Явных следов вредителей не выявлено — но Demo-режим не способен их увидеть", "низкая", [no_vision], "Claude-vision или осмотр с лупой"),
            _h("Повреждения листьев от механических причин (перестановка, транспорт) возможны у любого растения", "низкая",
               ["общая статистика"], "Сравнить с фото месячной давности"),
            _h("Присутствие животных (кот, грызущий листья) нельзя исключить", "низкая", ["нет визуальных данных"],
               "Посмотреть края листьев: ровные надкусы или погрызы"),
        ])

        # ---------- Owner (только об уходе, без выводов о личности) ----------
        of, oh = [], []
        own = extras.get("owner", {})
        if own:
            of.append(dict(text=f"В коллекции {own['plants']} растений, родов: {own['genera']}", source="profile"))
            of.append(dict(text=f"Записей ухода за 45 дней: {own['care_events']}; ручных измерений: {own['manual_readings']}; датчиков: {own['sensors']}", source="care_history"))
            if own["plants"] >= 3 and own["genera"] >= 2:
                oh.append(_h("Есть признаки коллекционирования: несколько родов орхидей", "средняя",
                             [f"{own['genera']} разных рода в коллекции"], "Посмотреть, растёт ли коллекция со временем"))
            if own["manual_readings"] > 0 or own["sensors"] > 3:
                oh.append(_h("Уход с элементами эксперимента: измерения и датчики", "средняя",
                             [f"датчиков: {own['sensors']}", f"ручных измерений: {own['manual_readings']}"],
                             "Через месяц сравнить, меняется ли режим ухода по данным"))
            if own.get("watering_regular") is not None:
                oh.append(_h("Полив по устойчивому графику" if own["watering_regular"] else "Полив по наблюдению, без жёсткого графика",
                             "средняя", [f"разброс интервалов полива ±{own['watering_spread']:.1f} дн."],
                             "Сопоставить с датчиком влажности субстрата"))
        oh = _pad(oh, [
            _h("Выращивание декоративное: орхидеи — растения для красоты, а не урожая", "средняя", ["состав коллекции"],
               "Есть ли в коллекции съедобные растения?"),
            _h("Уход организован с журналом — вероятно, вдумчивый подход", "низкая", ["пользуется приложением"], "Регулярность записей"),
            _h("Возможно, владелец только начинает собирать данные", "низкая", ["короткая история"], "Посмотреть историю через 3 месяца"),
        ])

        def sec(direction, title, facts, hyps, unknowns, needed):
            return dict(direction=direction, title=title, facts=facts, hypotheses=hyps, unknowns=unknowns,
                        data_needed=needed, sensors=[dict(sensor=a, purpose=b) for a, b in SENSOR_TIPS[direction]])

        name = genus["name"] if genus else (p["species"] if p else "Неустановленное растение")
        codename = f"Операция «{p['name']}»" if p else "Операция «Неизвестный стебель»"
        if photo_kind == "illustration":
            photo_note = "Это иллюстрация из коллекции, а не фотография: пиксельные улики не собирались. Загрузите настоящее фото."
        elif photo_kind == "none":
            photo_note = "Фотографии нет — досье составлено по материалам дела."
        else:
            photo_note = "Фото перекодировано без метаданных геолокации. " + no_vision
        return dict(
            codename=codename,
            summary=(f"Агент Demo изучил {'снимок и ' if stats else ''}материалы дела"
                     + (f" на «{p['name']}»" if p else "") + ". Объекты на фото он не распознаёт, зато честно меряет пиксели "
                     "и сверяет профиль с датчиками. Гипотезы ниже — не приговор, а план проверки."),
            identification=dict(name=name, confidence="высокая" if genus else "низкая",
                                basis="по профилю растения" if p else "без профиля и без vision вид не установить"),
            sections=[
                sec("climate", "Климатическая разведка", cf, ch, cu,
                    ["Фото цветка и листа крупным планом", "Неделя показаний температуры и влажности"]),
                sec("scene", "Расследование окружения", sf, sh,
                    ["Другие растения, ёмкости и грунт в кадре (нужно зрение)", "Признаки теплицы", "Ориентация окна"],
                    ["Фото общего плана", "Время съёмки"]),
                sec("biology", "Биологические улики", bf, bh,
                    ["Насекомые, паутина, следы вредителей и животных на фото", "Мелкие повреждения ниже разрешения снимка"],
                    ["Макрофото нижней стороны листьев", "Фото корней"]),
                sec("owner", "Профиль владельца (только уход)", of, oh,
                    ["Любые личные характеристики владельца — по фото их определять нельзя и не нужно"],
                    ["История ухода за несколько месяцев"]),
            ],
            clues=[f["text"] for f in (sf[:2] + bf[:1] + cf[:1])][:5] or ["Улик мало: нужна фотография или профиль растения"],
            to_check=["Сфотографировать растение днём у окна и общим планом",
                      "Осмотреть нижнюю сторону листьев с лупой",
                      "Подключить ANTHROPIC_API_KEY для настоящего визуального анализа"]
                     + (["Сравнить визуальные гипотезы со сверкой датчиков ниже"] if p else ["Привязать фото к растению из коллекции"]),
            visual_estimates=dict(
                light_level=("unknown" if not stats else "low" if stats["brightness"] < 70 else "high" if stats["brightness"] > 170 else "medium"),
                humidity_level="unknown",
                setting=("indoor" if (stats and (stats["magenta_share"] > 0.04 or stats["warmth"] > 18)) or (p and p.get("location")) else "unknown"),
            ),
            photo_note=photo_note,
        )
