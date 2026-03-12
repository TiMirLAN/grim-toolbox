# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "requests",
# ]
# ///

import json
import os
import pprint
import requests  # pyright: ignore[reportMissingModuleSource]
from typing import Dict, List, Optional, Any


class BaseProvider:
    """Базовый класс для всех провайдеров моделей."""

    NAME: str = ""
    BASE_URL: str = ""

    def __init__(self):
        """
        Инициализация базового провайдера.
        """
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "LLM Price Monitor Script/1.0"})

    @property
    def name(self) -> str:
        """Имя провайдера (только для чтения)."""
        return self.NAME

    @property
    def base_url(self) -> str:
        """Базовый URL провайдера (только для чтения)."""
        return self.BASE_URL

    def get_api_key(self) -> Optional[str]:
        """
        Получает API‑ключ из ~/.local/share/opencode/auth.json.

        Returns:
            API ключ или None, если не найден
        """
        auth_path = os.path.expanduser("~/.local/share/opencode/auth.json")
        try:
            with open(auth_path, "r") as f:
                auth_data = json.load(f)
            if self.name in auth_data:
                return auth_data[self.name].get("key")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Ошибка при чтении auth.json: {e}")
        return None

    def fetch_models(self) -> Optional[List[Dict]]:
        """
        Получает список моделей от провайдера через OpenAI-compatible API.

        Returns:
            Список моделей или None в случае ошибки
        """
        api_key = self.get_api_key()
        if not api_key:
            return None

        url = f"{self.base_url}/models"
        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

        try:
            response = self.session.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            if "data" in data:
                return data["data"]
            return data

        except requests.exceptions.Timeout as e:
            print(f"Таймаут при запросе к {self.name}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к {self.name}: {e}")
            return None
        except ValueError as e:
            print(f"Неверный JSON от {self.name}: {e}")
            return None


class RouterAIProvider(BaseProvider):
    """Провайдер RouterAI."""

    NAME = "RouterAI"
    BASE_URL = "https://routerai.ru/api/v1"


class NeuroAPIProvider(BaseProvider):
    """Провайдер NeuroAPI."""

    NAME = "NeuroAPI"
    BASE_URL = "https://neuroapi.host/v1"


class CailaProvider(BaseProvider):
    """Провайдер Caila.io."""

    NAME = "Caila.io"
    BASE_URL = "https://caila.io/api/adapters/openai-direct"


class AgentPlatformProvider(BaseProvider):
    """Провайдер AgentPlatform."""

    NAME = "AgentPlatform"
    BASE_URL = "https://litellm.tokengate.ru/v1"


def main():
    """Основная функция — запускает запросы ко всем провайдерам."""
    providers = [
        RouterAIProvider(),
        NeuroAPIProvider(),
        CailaProvider(),
        AgentPlatformProvider(),
    ]

    results = {}

    for provider in providers:
        print(f"\n--- Получаем модели от {provider.name} ---")
        models = provider.fetch_models()

        if models is None:
            results[provider.name] = "Ошибка/Нет данных"
        elif len(models) == 0:
            results[provider.name] = "Список пуст"
        else:
            results[provider.name] = f"Найдено моделей: {len(models)}"
            # Сохраняем модели в файл
            filename = f"{provider.name.replace('.', '')}.models.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(models, f, ensure_ascii=False, indent=2)
            print(f"Модели сохранены в {filename}")
            # Выводим первые 3 модели для примера
            print(f"Первые 3 модели ({provider.name}):")
            pprint.pprint(models[:3])

    # Финальный отчёт
    print("\n" + "=" * 50)
    print("ФИНАЛЬНЫЙ ОТЧЁТ")
    print("=" * 50)
    for provider, status in results.items():
        print(f"{provider}: {status}")


if __name__ == "__main__":
    main()
