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
- Конфигурация через `~/.config/hastuioctl/events.yaml` (без хардкода в коде)

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
| 4 | Написать и загнать тесты (`pytest`) | ✅ Готово |
| 5 | Создать Portainer stack для Mosquitto | ✅ Готово |
| 6 | Настроить HA (`configuration.yaml`, shell_command) | ✅ Готово |
| 7 | Сделать конфиг в `~/.config/hastuioctl/events.yaml` | ✅ Готово |
| 8 | Развернуть systemd на хосте | ✅ Готово (нужно установить playerctl) |

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

### Расположение конфига
Конфигурация `events.yaml` должна находиться в:
```
~/.config/hastuioctl/events.yaml
```

Это позволяет:
- Не захардкоживать путь в коде
- Использовать один конфиг для нескольких демонов
- Легко редактировать без прав суперпользователя
- Создать симлинк в репозитории для удобства разработки

При запуске демон ищет конфиг по следующему приоритету:
1. `~/.config/hastuioctl/events.yaml`
2. (опционально) `./events.yaml` в директории со скриптом

### Тестирование
- Мок MQTT для проверки парсинга JSON
- Проверка `match_trigger` на Edge-кейсы
- Проверка `render` и `build_context` шаблонов
- Проверка `run_action` через `subprocess.run(mock=True)`
