import io

from PIL import Image

from app.config import get_settings
from app.services.ai import spy_claude
from tests.conftest import by_name


def _photo(color=(60, 140, 70), size=(640, 480), gps=True, fmt="JPEG") -> bytes:
    img = Image.new("RGB", size, color)
    for x in range(0, size[0], 40):          # немного текстуры
        for y in range(size[1] // 2, size[1]):
            img.putpixel((x, y), (200, 60, 200))
    buf = io.BytesIO()
    exif = Image.Exif()
    exif[0x0132] = "2026:11:18 21:30:00"                     # DateTime
    if gps:
        exif[0x8825] = {1: "N", 2: (55.0, 45.0, 0.0)}        # GPSInfo — должно быть удалено
    img.save(buf, fmt, exif=exif.tobytes()) if fmt == "JPEG" else img.save(buf, fmt)
    return buf.getvalue()


def _post(client, data=None, **form):
    files = {"file": ("leaf.jpg", data, "image/jpeg")} if data is not None else None
    return client.post("/api/spy/investigations", files=files, data={k: str(v) for k, v in form.items()})


def test_upload_unlinked_demo_dossier(client):
    r = _post(client, _photo())
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["mode"] == "demo" and d["photo_source"] == "upload" and d["plant_id"] is None
    res = d["result"]
    assert [s["direction"] for s in res["sections"]] == ["climate", "scene", "biology", "owner"]
    for s in res["sections"]:
        assert len(s["hypotheses"]) == 3
        assert all(h["confidence"] in ("высокая", "средняя", "низкая") and h["how_to_verify"] for h in s["hypotheses"])
        assert s["unknowns"] and s["sensors"]
    scene = res["sections"][1]
    assert any(f["source"] == "pixel_stats" for f in scene["facts"])
    assert res["identification"]["confidence"] == "низкая"            # без профиля и vision вид не определяем
    assert all(c["verdict"] == "no_data" for c in d["crosscheck"])   # не привязано — не придумываем
    assert d["image_stats"]["width"] == 640 and "magenta_share" in d["image_stats"]


def test_uploaded_photo_is_stripped_of_metadata(client):
    d = _post(client, _photo(gps=True)).json()
    saved = client.get(d["photo_url"])
    assert saved.status_code == 200
    img = Image.open(io.BytesIO(saved.content))
    assert 0x8825 not in img.getexif() and len(img.getexif()) == 0     # GPS и прочий EXIF удалены
    assert "gps" not in str(d["image_stats"]).lower()


def test_linked_plant_uses_profile_and_sensors(client, plants):
    luna = by_name(plants, "Луна")["plant"]["id"]
    d = _post(client, _photo(color=(240, 240, 235)), plant_id=luna).json()
    assert d["plant_name"] == "Луна"
    climate = d["result"]["sections"][0]
    assert any(f["source"] == "knowledge" and "Азия" in f["text"] for f in climate["facts"])
    assert any(f["source"] == "sensor" for f in climate["facts"])
    light = next(c for c in d["crosscheck"] if c["metric"] == "light")
    assert light["measured"] and light["source"] == "demo" and light["verdict"] in ("consistent", "contradicts", "no_data")


def test_no_invented_measurements_without_sensors(client, plants):
    emerald = by_name(plants, "Изумруд")["plant"]["id"]       # нет датчика света
    d = _post(client, _photo(), plant_id=emerald).json()
    light = next(c for c in d["crosscheck"] if c["metric"] == "light")
    assert light["verdict"] == "no_data" and light["measured"] is None
    hum = next(c for c in d["crosscheck"] if c["metric"] == "air_humidity")
    assert hum["measured"] is not None                        # DHT22 есть — сверка выполняется


def test_collection_illustration(client, plants):
    pid = by_name(plants, "Карамель")["plant"]["id"]
    r = _post(client, plant_id=pid, use_plant_photo=True)
    assert r.status_code == 201
    d = r.json()
    assert d["photo_source"] == "illustration" and d["image_stats"] is None
    assert any("иллюстрация" in w for w in d["warnings"])


def test_owner_profile_is_about_care_only(client):
    d = _post(client, _photo()).json()
    owner = next(s for s in d["result"]["sections"] if s["direction"] == "owner")
    text = str(owner).lower()
    for banned in ("возраст", "семейн", "характер владельц", "пол владельц"):
        assert banned not in text.replace("определять нельзя", "")
    assert any("личные характеристики" in u for u in owner["unknowns"])


def test_history_and_get(client):
    hist = client.get("/api/spy/investigations").json()
    assert len(hist) >= 5 and hist[0]["created_at"] >= hist[-1]["created_at"]
    one = client.get(f"/api/spy/investigations/{hist[0]['id']}")
    assert one.status_code == 200 and one.json()["codename"]
    luna_hist = client.get("/api/spy/investigations", params={"plant_id": 1}).json()
    assert all(h["plant_id"] == 1 for h in luna_hist)


def test_spy_errors(client):
    assert _post(client).status_code == 422                                   # ни фото, ни растения
    assert _post(client, plant_id=1).status_code == 422                       # растение без use_plant_photo
    assert _post(client, plant_id=999, use_plant_photo=True).status_code == 404
    bad_type = client.post("/api/spy/investigations", files={"file": ("a.txt", b"hi", "text/plain")})
    assert bad_type.status_code == 415
    assert _post(client, b"not really a jpeg").status_code == 415
    assert client.get("/api/spy/investigations/99999").status_code == 404


def test_claude_path_and_fallback(client, plants, monkeypatch):
    s = get_settings()
    monkeypatch.setattr(s, "anthropic_api_key", "test-key")
    monkeypatch.setattr(s, "ai_mode", "auto")
    seen = {}

    def fake_ok(self, image_b64, media_type, dossier_input):
        seen.update(image=image_b64, media=media_type, ctx=dossier_input)
        sec = lambda d: dict(direction=d, title=d, facts=[dict(text="видна кора", source="photo")],
                             hypotheses=[dict(text=f"h{i}", confidence="средняя", evidence=["e"], how_to_verify="v") for i in range(4)],
                             unknowns=["u"], data_needed=["n"], sensors=[dict(sensor="BH1750", purpose="свет")])
        return dict(codename="Операция «Тест»", summary="s", identification=dict(name="Phalaenopsis", confidence="высокая", basis="цветок"),
                    sections=[sec(d) for d in ("owner", "climate", "scene", "biology")], clues=["c"], to_check=["t"],
                    visual_estimates=dict(light_level="medium", humidity_level="unknown", setting="indoor"), photo_note="ok")

    monkeypatch.setattr(spy_claude.ClaudeSpyEngine, "investigate", fake_ok)
    luna = by_name(plants, "Луна")["plant"]["id"]
    d = _post(client, _photo(), plant_id=luna).json()
    assert d["mode"] == "claude" and d["codename"] == "Операция «Тест»"
    assert [x["direction"] for x in d["result"]["sections"]] == ["climate", "scene", "biology", "owner"]
    assert all(len(x["hypotheses"]) == 3 for x in d["result"]["sections"])
    assert seen["media"] == "image/jpeg" and seen["image"] and seen["ctx"]["plant_context"]["plant"]["name"] == "Луна"

    monkeypatch.setattr(spy_claude.ClaudeSpyEngine, "investigate", lambda *a, **k: {"codename": "broken"})
    d = _post(client, _photo()).json()
    assert d["mode"] == "demo" and any("формат" in w for w in d["warnings"])

    def boom(*a, **k):
        raise spy_claude.ClaudeUnavailable("нет сети")
    monkeypatch.setattr(spy_claude.ClaudeSpyEngine, "investigate", boom)
    d = _post(client, _photo()).json()
    assert d["mode"] == "demo" and any("Claude недоступен" in w for w in d["warnings"])
