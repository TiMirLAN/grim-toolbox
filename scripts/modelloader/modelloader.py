# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "requests",
# ]
# ///

import json
import os
import pprint
import requests
from typing import Dict, List, Optional

# Настройка сессий для каждого провайдера
session = requests.Session()
session.headers.update({"User-Agent": "LLM Price Monitor Script/1.0"})


def get_api_key(provider_name: str) -> Optional[str]:
    """Получает API‑ключ из ~/.local/share/opencode/auth.json."""
    auth_path = os.path.expanduser("~/.local/share/opencode/auth.json")
    try:
        with open(auth_path, "r") as f:
            auth_data = json.load(f)
        if provider_name in auth_data:
            return auth_data[provider_name].get("key")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Ошибка при чтении auth.json: {e}")
    return None


def fetch_routerai_models() -> Optional[List[Dict]]:
    """Получает список моделей от RouterAI через OpenAI-compatible API."""
    provider_name = "RouterAI"
    api_key = get_api_key("routerai")
    if not api_key:
        return None

    url = "https://routerai.ru/api/v1/models"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

    try:
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "data" in data:
            return data["data"]
        return data

    except requests.exceptions.Timeout as e:
        print(f"Таймаут при запросе к {provider_name}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к {provider_name}: {e}")
        return None
    except ValueError as e:
        print(f"Неверный JSON от {provider_name}: {e}")
        return None


def fetch_neuroapi_models() -> Optional[List[Dict]]:
    """Получает список моделей от NeuroAPI через OpenAI-compatible API."""
    provider_name = "NeuroAPI"
    api_key = get_api_key("neuroapi")
    if not api_key:
        return None

    url = "https://neuroapi.host/v1/models"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

    try:
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "data" in data:
            return data["data"]
        return data
    except requests.exceptions.Timeout as e:
        print(f"Таймаут при запросе к {provider_name}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к {provider_name}: {e}")
        return None
    except ValueError as e:
        print(f"Неверный JSON от {provider_name}: {e}")
        return None


def fetch_caila_models() -> Optional[List[Dict]]:
    """Получает список моделей от Caila.io через OpenAI-compatible API."""
    provider_name = "Caila.io"
    api_key = get_api_key("caila-oai")
    if not api_key:
        return None

    url = "https://caila.io/api/adapters/openai-direct/models"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

    try:
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "data" in data:
            return data["data"]
        return data
    except requests.exceptions.Timeout as e:
        print(f"Таймаут при запросе к {provider_name}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к {provider_name}: {e}")
        return None
    except ValueError as e:
        print(f"Неверный JSON от {provider_name}: {e}")
        return None


def fetch_agentplatform_models() -> Optional[List[Dict]]:
    """Получает список моделей от AgentPlatform через OpenAI-compatible API."""
    provider_name = "AgentPlatform"
    api_key = get_api_key("agentplatform")
    if not api_key:
        return None

    url = "https://litellm.tokengate.ru/v1/models"
    headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

    try:
        response = session.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        if "data" in data:
            return data["data"]
        return data
    except requests.exceptions.Timeout as e:
        print(f"Таймаут при запросе к {provider_name}: {e}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Ошибка при запросе к {provider_name}: {e}")
        return None
    except ValueError as e:
        print(f"Неверный JSON от {provider_name}: {e}")
        return None


def main():
    """Основная функция — запускает запросы ко всем провайдерам."""
    providers = {
        "RouterAI": fetch_routerai_models,
        "NeuroAPI": fetch_neuroapi_models,
        "Caila.io": fetch_caila_models,
        "AgentPlatform": fetch_agentplatform_models,
    }

    results = {}

    for provider_name, fetch_func in providers.items():
        print(f"\n--- Получаем модели от {provider_name} ---")
        models = fetch_func()

        if models is None:
            results[provider_name] = "Ошибка/Нет данных"
        elif len(models) == 0:
            results[provider_name] = "Список пуст"
        else:
            results[provider_name] = f"Найдено моделей: {len(models)}"
            # Сохраняем модели в файл
            filename = f"{provider_name.replace('.', '')}.models.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(models, f, ensure_ascii=False, indent=2)
            print(f"Модели сохранены в {filename}")
            # Выводим первые 3 модели для примера
            print(f"Первые 3 модели ({provider_name}):")
            pprint.pprint(models[:3])

    # Финальный отчёт
    print("\n" + "=" * 50)
    print("ФИНАЛЬНЫЙ ОТЧЁТ")
    print("=" * 50)
    for provider, status in results.items():
        print(f"{provider}: {status}")


if __name__ == "__main__":
    main()
