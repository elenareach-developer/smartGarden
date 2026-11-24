"""USB-мост: ESP32 (монитор порта) → Smart Orchid API.

Работает с исходным скетчем temp_humidity_working_copy без перепрошивки: читает строки
  Humidity = 45.00%
  Temperature = 23.50 C
и раз в --interval секунд отправляет средние значения в POST /api/sensors/readings.

Установка:  pip install pyserial
Запуск:     python serial_bridge.py --port /dev/cu.usbserial-0001 --plant-id 1
Порт:       macOS — ls /dev/cu.*; Windows — COM3 (Диспетчер устройств); Linux — /dev/ttyUSB0
Важно:      закройте монитор порта Arduino IDE — порт может занимать только одна программа.
"""
import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request

HUM = re.compile(r"Humidity\s*=\s*(-?\d+(?:\.\d+)?)")
TEMP = re.compile(r"Temperature\s*=\s*(-?\d+(?:\.\d+)?)")


def parse_line(line: str):
    """Возвращает ('air_humidity'|'temperature', значение) или None."""
    if m := HUM.search(line):
        return "air_humidity", float(m.group(1))
    if m := TEMP.search(line):
        return "temperature", float(m.group(1))
    return None


def post(server: str, plant_id: int, hardware_id: str, values: dict[str, float]) -> None:
    body = {"readings": [{"plant_id": plant_id, "metric": k, "value": round(v, 1), "source": "iot",
                          "hardware_id": hardware_id} for k, v in values.items()]}
    req = urllib.request.Request(server.rstrip("/") + "/api/sensors/readings", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            print(f"✓ отправлено ({r.status}): " + ", ".join(f"{k}={v:.1f}" for k, v in values.items()))
    except urllib.error.HTTPError as e:
        detail = e.read().decode(errors="replace")
        print(f"✗ сервер ответил {e.code}: {detail}")
        if e.code == 404:
            print("  → Зарегистрируйте датчик в Settings (тип DHT11, hardware_id как в --hardware-id)")
    except urllib.error.URLError as e:
        print(f"✗ сервер недоступен: {e.reason}. Запущен ли backend на {server}?")


def lines_from(args):
    if args.stdin:
        yield from sys.stdin
        return
    try:
        import serial  # pyserial
    except ImportError:
        sys.exit("Установите pyserial: pip install pyserial")
    with serial.Serial(args.port, args.baud, timeout=2) as port:
        print(f"Слушаю {args.port} ({args.baud} бод). Ctrl+C — выход.")
        while True:
            raw = port.readline()
            if raw:
                yield raw.decode(errors="replace")


def main():
    ap = argparse.ArgumentParser(description="ESP32 serial → Smart Orchid")
    ap.add_argument("--port", help="последовательный порт ESP32")
    ap.add_argument("--baud", type=int, default=9600, help="скорость, как в Serial.begin (по умолчанию 9600)")
    ap.add_argument("--server", default="http://localhost:8000")
    ap.add_argument("--plant-id", type=int, required=True)
    ap.add_argument("--hardware-id", default="esp32-orchid-dht11")
    ap.add_argument("--interval", type=float, default=60, help="как часто отправлять средние, сек")
    ap.add_argument("--stdin", action="store_true", help="читать строки из stdin (для проверки без ESP32)")
    args = ap.parse_args()
    if not args.stdin and not args.port:
        ap.error("укажите --port (или --stdin для проверки)")

    acc: dict[str, list[float]] = {}
    last = time.monotonic()
    try:
        for line in lines_from(args):
            parsed = parse_line(line)
            if parsed:
                acc.setdefault(parsed[0], []).append(parsed[1])
            if acc and (time.monotonic() - last >= args.interval):
                post(args.server, args.plant_id, args.hardware_id, {k: sum(v) / len(v) for k, v in acc.items()})
                acc, last = {}, time.monotonic()
    except KeyboardInterrupt:
        pass
    if acc and args.stdin:
        post(args.server, args.plant_id, args.hardware_id, {k: sum(v) / len(v) for k, v in acc.items()})


if __name__ == "__main__":
    main()
