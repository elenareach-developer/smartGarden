"""ESP32 + DHT11: регистрация датчика, приём данных в формате прошивки и USB-моста, отображение в мониторинге."""
import importlib.util
from pathlib import Path

from tests.conftest import by_name

BRIDGE = Path(__file__).resolve().parents[2] / "Device" / "serial_bridge" / "serial_bridge.py"


def _bridge():
    spec = importlib.util.spec_from_file_location("serial_bridge", BRIDGE)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_bridge_parses_original_sketch_output():
    b = _bridge()
    assert b.parse_line("Humidity = 45.00%\r\n") == ("air_humidity", 45.0)
    assert b.parse_line("Temperature = 23.50 C") == ("temperature", 23.5)
    assert b.parse_line("Sensor reading failed!") is None
    assert b.parse_line("----------------") is None


def test_esp32_dht11_flow(client, plants):
    pid = by_name(plants, "Карамель")["plant"]["id"]
    s = client.post("/api/sensors", json={"plant_id": pid, "name": "ESP32 DHT11", "sensor_type": "DHT11",
                                          "hardware_id": "esp32-test-dht11"})
    assert s.status_code == 201 and s.json()["metrics"] == ["temperature", "air_humidity"]
    assert client.put(f"/api/plants/{pid}", json={"data_source": "iot"}).status_code == 200
    body = {"readings": [  # ровно то, что отправляет smart_orchid_dht11_wifi.ino
        {"plant_id": pid, "metric": "temperature", "value": 23.4, "source": "iot", "hardware_id": "esp32-test-dht11"},
        {"plant_id": pid, "metric": "air_humidity", "value": 52.0, "source": "iot", "hardware_id": "esp32-test-dht11"},
    ]}
    assert client.post("/api/sensors/readings", json=body).status_code == 201
    mon = client.get(f"/api/plants/{pid}/monitoring").json()
    m = {x["metric"]: x for x in mon["metrics"]}
    assert mon["data_source"] == "iot" and not mon["is_demo"]
    assert m["temperature"]["current"]["value"] == 23.4 and m["temperature"]["current"]["source"] == "iot"
    assert m["air_humidity"]["current"]["value"] == 52.0
    assert m["light"]["current"] is None                   # у DHT11 нет света — не придумываем
    # возвращаем DEMO, чтобы не влиять на другие тесты
    assert client.put(f"/api/plants/{pid}", json={"data_source": "demo"}).status_code == 200
