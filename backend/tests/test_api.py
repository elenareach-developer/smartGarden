from datetime import datetime, timedelta, timezone

from tests.conftest import by_name


def test_three_demo_plants(plants):
    assert len(plants) == 3
    names = {p["plant"]["name"] for p in plants}
    assert names == {"Луна", "Карамель", "Изумруд"}
    for p in plants:
        assert p["plant"]["photo_url"]
        assert p["plant"]["species"] and p["plant"]["stage_label"]
        assert p["last_watering"] and p["last_fertilizing"]
    # разные исходные состояния
    att = {p["plant"]["name"]: p["attention"] for p in plants}
    assert att["Луна"] == "ok"
    assert att["Карамель"] == "attention"
    assert att["Изумруд"] == "critical"


def test_select_plant_and_404(client, plants):
    pid = by_name(plants, "Луна")["plant"]["id"]
    r = client.get(f"/api/plants/{pid}")
    assert r.status_code == 200 and r.json()["plant"]["name"] == "Луна"
    r = client.get("/api/plants/9999")
    assert r.status_code == 404 and r.json()["code"] == "not_found"


def test_update_plant_and_validation(client, plants):
    pid = by_name(plants, "Карамель")["plant"]["id"]
    r = client.put(f"/api/plants/{pid}", json={"notes": "Переставлена ближе к окну", "stage": "vegetative"})
    assert r.status_code == 200 and r.json()["notes"] == "Переставлена ближе к окну"
    bad = client.put(f"/api/plants/{pid}", json={"name": ""})
    assert bad.status_code == 422 and bad.json()["code"] == "validation_error"
    t = r.json()["targets"] | {"temp_min": 30, "temp_max": 20}
    assert client.put(f"/api/plants/{pid}", json={"targets": t}).status_code == 422
    assert client.put(f"/api/plants/{pid}", json={"unknown": 1}).status_code == 422


def test_individual_monitoring(client, plants):
    luna = client.get(f"/api/plants/{by_name(plants, 'Луна')['plant']['id']}/monitoring").json()
    emerald = client.get(f"/api/plants/{by_name(plants, 'Изумруд')['plant']['id']}/monitoring").json()
    assert luna["is_demo"] is True
    lm = {m["metric"]: m for m in luna["metrics"]}
    em = {m["metric"]: m for m in emerald["metrics"]}
    assert lm["substrate_moisture"]["available"] and lm["substrate_moisture"]["current"]
    assert lm["photoperiod"]["kind"] == "derived"
    assert lm["temperature"]["current"]["source"] == "demo"
    assert lm["temperature"]["current"]["timestamp"]
    # у Изумруда нет датчиков света и субстрата — данные не придумываются
    assert em["light"]["status"] == "no_data" and em["light"]["current"] is None
    assert em["substrate_moisture"]["current"] is None
    assert em["air_humidity"]["status"] == "low"
    assert {o["key"] for o in emerald["observations"]} == {"root_status", "leaf_status"}


def test_history_periods(client, plants):
    pid = by_name(plants, "Карамель")["plant"]["id"]
    for period, min_points in [("24h", 40), ("7d", 70), ("30d", 100)]:
        r = client.get(f"/api/plants/{pid}/history", params={"period": period})
        assert r.status_code == 200
        series = {s["metric"]: s for s in r.json()["series"]}
        assert "pot_weight" in series and "substrate_moisture" not in series
        assert len(series["temperature"]["points"]) >= min_points
        assert all(s["source"] == "demo" for s in series.values())
    assert client.get(f"/api/plants/{pid}/history", params={"period": "1y"}).status_code == 422


def test_manual_reading_is_separate(client, plants):
    pid = by_name(plants, "Изумруд")["plant"]["id"]
    r = client.post("/api/sensors/readings", json={"plant_id": pid, "metric": "light", "value": 6500})
    assert r.status_code == 201 and r.json()["readings"][0]["source"] == "manual"
    mon = client.get(f"/api/plants/{pid}/monitoring").json()
    light = next(m for m in mon["metrics"] if m["metric"] == "light")
    assert light["current"] is None                      # DEMO-ряд не смешан с ручным
    assert light["manual_latest"]["value"] == 6500
    hist = client.get(f"/api/plants/{pid}/history", params={"period": "24h"}).json()
    assert any(s["metric"] == "light" and s["source"] == "manual" for s in hist["manual"])
    assert not any(s["metric"] == "light" for s in hist["series"])


def test_reading_validation_errors(client, plants):
    pid = by_name(plants, "Луна")["plant"]["id"]
    assert client.post("/api/sensors/readings", json={"plant_id": pid, "metric": "air_humidity", "value": 140}).status_code == 422
    assert client.post("/api/sensors/readings", json={"plant_id": pid, "metric": "temperature", "value": 20, "unit": "F"}).status_code == 422
    assert client.post("/api/sensors/readings", json={"plant_id": pid, "metric": "co2", "value": 400}).status_code == 422
    assert client.post("/api/sensors/readings", json={"plant_id": 999, "metric": "temperature", "value": 20}).status_code == 404
    # IoT без зарегистрированного датчика
    r = client.post("/api/sensors/readings", json={"plant_id": pid, "metric": "temperature", "value": 20,
                                                   "source": "iot", "hardware_id": "esp32-unknown"})
    assert r.status_code == 404


def test_iot_sensor_flow(client, plants):
    pid = by_name(plants, "Луна")["plant"]["id"]
    s = client.post("/api/sensors", json={"plant_id": pid, "name": "ESP32 DHT22", "sensor_type": "DHT22",
                                          "hardware_id": "esp32-aa:bb:cc-dht"})
    assert s.status_code == 201 and s.json()["metrics"] == ["temperature", "air_humidity"]
    batch = {"readings": [
        {"plant_id": pid, "metric": "temperature", "value": 22.4, "source": "iot", "hardware_id": "esp32-aa:bb:cc-dht"},
        {"plant_id": pid, "metric": "air_humidity", "value": 61, "source": "iot", "sensor_id": s.json()["id"]},
    ]}
    r = client.post("/api/sensors/readings", json=batch)
    assert r.status_code == 201 and r.json()["accepted"] == 2
    bad = client.post("/api/sensors/readings", json={"plant_id": pid, "metric": "light", "value": 100,
                                                     "source": "iot", "sensor_id": s.json()["id"]})
    assert bad.status_code == 422   # DHT22 не измеряет свет
    dup = client.post("/api/sensors", json={"plant_id": pid, "name": "dup", "sensor_type": "DHT22",
                                            "hardware_id": "esp32-aa:bb:cc-dht"})
    assert dup.status_code == 409


def test_watering_event(client, plants):
    pid = by_name(plants, "Изумруд")["plant"]["id"]
    before = client.get(f"/api/plants/{pid}").json()["last_watering"]
    r = client.post(f"/api/plants/{pid}/care", json={"event_type": "watering", "amount_ml": 100,
                                                      "method": "по краю горшка"})
    assert r.status_code == 201 and r.json()["event_label"] == "Полив"
    after = client.get(f"/api/plants/{pid}").json()["last_watering"]
    assert after > before
    care = client.get(f"/api/plants/{pid}/care").json()
    assert care["events"][0]["id"] == r.json()["id"]
    assert {t["task"] for t in care["planned"]} >= {"watering_check", "fertilizing", "inspection"}
    future = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    assert client.post(f"/api/plants/{pid}/care", json={"event_type": "watering", "timestamp": future}).status_code == 422
    assert client.post(f"/api/plants/{pid}/care", json={"event_type": "fertilizing"}).status_code == 422


def test_inspection_updates_observations(client, plants):
    pid = by_name(plants, "Луна")["plant"]["id"]
    r = client.post(f"/api/plants/{pid}/care", json={"event_type": "inspection", "root_status": "healthy",
                                                      "leaf_status": "healthy", "notes": "ок"})
    assert r.status_code == 201
    assert client.get(f"/api/plants/{pid}").json()["plant"]["root_status"] == "healthy"


def test_fertilizer_advisor(client, plants):
    luna = by_name(plants, "Луна")["plant"]["id"]
    emerald = by_name(plants, "Изумруд")["plant"]["id"]
    lib = client.get(f"/api/plants/{luna}/fertilizers").json()
    assert len(lib["library"]) >= 2 and lib["applications"]
    # повреждённые корни — подкормка не рекомендуется
    r = client.post(f"/api/plants/{emerald}/fertilizers", json={"fertilizer_id": lib["library"][0]["id"]})
    assert r.status_code == 201
    a = r.json()["assessment"]
    assert a["verdict"] == "not_now" and a["blockers"]
    assert r.json()["application"] is None    # ничего не назначено автоматически
    # нет состава — оценка невозможна, но система не придумывает NPK
    r = client.post(f"/api/plants/{luna}/fertilizers", json={"fertilizer": {"name": "Неизвестное"}})
    a = r.json()["assessment"]
    assert a["verdict"] in ("insufficient_data", "not_now") and any("NPK" in q for q in a["questions"])
    assert r.json()["fertilizer"]["npk_n"] is None


def test_record_fertilizer_application(client, plants):
    pid = by_name(plants, "Карамель")["plant"]["id"]
    new = {"name": "Тестовое 4-4-4", "npk_n": 4, "npk_p": 4, "npk_k": 4, "labeled_for_orchids": True,
           "manufacturer_instructions": "Развести по инструкции на упаковке"}
    r = client.post(f"/api/plants/{pid}/fertilizers", json={"fertilizer": new, "record_application": True,
                                                            "dilution": "по инструкции"})
    assert r.status_code == 201
    body = r.json()
    assert body["assessment"]["verdict"] in ("suitable", "conditional")
    assert body["application"]["fertilizer"]["name"] == "Тестовое 4-4-4"
    lf = client.get(f"/api/plants/{pid}").json()["last_fertilizing"]
    assert lf[:10] == datetime.now(timezone.utc).date().isoformat()
    bad = client.post(f"/api/plants/{pid}/fertilizers", json={"fertilizer_id": 1, "fertilizer": new})
    assert bad.status_code == 422
    assert client.post(f"/api/plants/{pid}/fertilizers", json={"fertilizer_id": 9999}).status_code == 404


def test_forecast(client, plants):
    for p in plants:
        pid = p["plant"]["id"]
        for h in (3, 7, 14):
            r = client.get(f"/api/plants/{pid}/forecast", params={"horizon": h})
            assert r.status_code == 200
            f = r.json()
            assert f["horizon_days"] == h and f["is_demo"]
            assert f["watering"]["explanation"]
            for m in f["metrics"]:
                assert m["kind"] == "forecast" and m["explanation"]
                if m["points"]:
                    last = datetime.fromisoformat(m["points"][-1]["t"])
                    assert last <= datetime.now(timezone.utc) + timedelta(days=h, hours=1)
                    assert all(pt["low"] <= pt["value"] <= pt["high"] for pt in m["points"])
            assert f["dynamics"]["kind"] == "hypothesis"
    caramel = client.get(f"/api/plants/{by_name(plants, 'Карамель')['plant']['id']}/forecast").json()
    assert any(r["code"] == "low_light" for r in caramel["risks"])
    emerald = client.get(f"/api/plants/{by_name(plants, 'Изумруд')['plant']['id']}/forecast").json()
    assert {"light"} & {m["metric"] for m in emerald["metrics"]} == set()   # нет датчика — нет прогноза
    assert emerald["watering"]["confidence_label"] == "низкая"
    assert client.get(f"/api/plants/1/forecast", params={"horizon": 5}).status_code == 422


def test_ai_demo_mode(client, plants):
    pid = by_name(plants, "Изумруд")["plant"]["id"]
    for topic in ("feeding", "watering", "yellow_leaves", "no_bloom", "roots", "disease", "conditions"):
        r = client.post("/api/ai/consult", json={"plant_id": pid, "topic": topic, "question": "Помоги"})
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["mode"] == "demo" and body["answer"].startswith("##")
        assert body["clarifying_questions"]
        assert "Освещённость" in body["missing_data"]     # не придумывает отсутствующие измерения
    feed = client.post("/api/ai/consult", json={"plant_id": pid, "topic": "feeding", "question": "Чем подкормить?"}).json()
    assert any("не рекомендуется" in w for w in feed["warnings"])
    auto = client.post("/api/ai/consult", json={"plant_id": pid, "question": "Почему желтеет нижний лист?"}).json()
    assert auto["topic"] == "yellow_leaves"
    hist = client.get(f"/api/plants/{pid}/consultations").json()
    assert len(hist) >= 9
    assert client.get("/api/ai/status").json()["mode"] == "demo"


def test_ai_errors(client):
    assert client.post("/api/ai/consult", json={"plant_id": 999, "question": "?"}).status_code == 404
    assert client.post("/api/ai/consult", json={"plant_id": 1, "question": ""}).status_code == 422
    assert client.post("/api/ai/consult", json={"plant_id": 1, "question": "x", "topic": "magic"}).status_code == 422
    assert client.post("/api/ai/consult", json={"plant_id": 1, "question": "x", "fertilizer_id": 999}).status_code == 404


def test_dashboard_and_system(client):
    d = client.get("/api/dashboard/summary").json()
    assert d["plants_total"] == 3 and d["needs_attention"] >= 2 and d["critical"] >= 1
    assert d["upcoming"] and d["recent_events"]
    s = client.get("/api/system/status").json()
    assert s["readings_by_source"]["demo"] > 1000
    assert client.get("/docs").status_code == 200
    assert "/api/plants/{plant_id}/forecast" in client.get("/openapi.json").json()["paths"]


def test_photo_upload(client):
    png = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
           b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05\x18\xd8N\x00\x00\x00\x00IEND\xaeB`\x82")
    r = client.post("/api/plants/1/photo", files={"file": ("a.png", png, "image/png")})
    assert r.status_code == 200 and r.json()["photo_url"].startswith("/uploads/")
    assert client.get(r.json()["photo_url"]).status_code == 200
    bad = client.post("/api/plants/1/photo", files={"file": ("a.txt", b"hi", "text/plain")})
    assert bad.status_code == 415
