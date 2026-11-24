// Скопируйте этот файл в secrets.h (в этой же папке) и заполните.
// secrets.h не попадает в git — пароль от Wi-Fi останется только у вас.
#pragma once

#define WIFI_SSID     "ИМЯ_ВАШЕЙ_WIFI_СЕТИ"     // ESP32 работает только с Wi-Fi 2.4 ГГц
#define WIFI_PASSWORD "ПАРОЛЬ_WIFI"

// Адрес компьютера, где запущен backend: http://<IP компьютера в локальной сети>:8000
// Узнать IP: macOS — ipconfig getifaddr en0; Windows — ipconfig; Linux — hostname -I
// Не используйте localhost: для ESP32 это он сам.
#define SERVER_URL    "http://192.168.1.50:8000"

// ID растения в приложении (Луна = 1, Карамель = 2, Изумруд = 3 в демо-данных)
#define PLANT_ID      1

// Должен совпадать с hardware_id датчика, зарегистрированного в Settings приложения
#define HARDWARE_ID   "esp32-orchid-dht11"
