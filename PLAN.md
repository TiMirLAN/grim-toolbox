# План: hastuioctl — интеграция Home Assistant с аудио хоста

## 🎯 Цель
Возможность дистанционного управления звуком и плеерами на Arch Linux (Niri, PipeWire) через Home Assistant.

## 🏗 Архитектура (3 уровня)

### 1. MQTT-брокер (Docker / Portainer)
- `eclipse-mosquitto:2` в контейнере
- Порты: `1883` (TCP), `9001` (WebSocket)
- Данные и конфиг через volumes

### 2. Системный демон `hastuioctl` (Хост Arch)
- Python 3.10+ демон
- Подписывается на MQTT-топики
- Исполняет команды через `playerctl`, `pactl`, `mpv`, `espeak`
- Конфигурация через `events.yaml` (без хардкода в коде)

### 3. Home Assistant (Docker Container)
- Использует встроенный `mqtt` интеграцию
- `shell_command` отправляет JSON-сообщения в брокер
- Дашборд / автоматизации для управления

---

## 📁 Структура файлов

```
grim-toolbox/
├── PLAN.md
└── apps/hastuioctl/
    ├── hastuioctl.py          # Основной демон
    ├── events.yaml            # Декларативное описание правил (топик -> команда)
    ├── docker-compose.yml     # Стек для Portainer (Mosquitto)
    ├── hastuioctl.service     # systemd юнит для хоста
    └── test_hastuioctl.py     # Юнит-тесты
```

---

## ✅ Прогресс

| # | Задача | Статус |
|---|--------|--------|
| 1 | Составить план и структуру | ✅ Готово |
| 2 | Реализовать `events.yaml` (декларативный триггеры → shell) | ✅ Готово |
| 3 | Написать `hastuioctl.py` с `loguru` и `uv` shebang | ✅ Готово |
| 4 | Написать и загнать тесты (`pytest`) | 🔄 В процессе |
| 5 | Создать Portainer stack для Mosquitto | ⬜ Следующий шаг |
| 6 | Настроить HA (`configuration.yaml`, shell_command) | ⬜ Следующий шаг |
| 7 | Развернуть systemd на хосте | ⬜ Следующий шаг |

---

## 🛠 Детали реализации

### `events.yaml` формат
```yaml
events:
  - topic: "ha/audio/command"
    trigger:
      command: "play"
    action:
      description: "Play audio"
      command: "playerctl"
      args: ["play"]
```
- Поддержка `{{ params }}` шаблонов
- Автоответы (reply) через `publish_reply_to`
- Порядок имеет значение — первый match побеждает

### uv-запуск
Файл начинается с:
```python
#!/usr/bin/env -S uv --with pyyaml --with paho-mqtt --with loguru run
```
Результат: `uv run ./hastuioctl.py` работает сразу, без `pip install`.

### Тестирование
- Мок MQTT для проверки парсинга JSON
- Проверка `match_trigger` на Edge-кейсы
- Проверка `render` и `build_context` шаблонов
- Проверка `run_action` через `subprocess.run(mock=True)`
