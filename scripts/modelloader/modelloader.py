# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "requests",
#     "click",
# ]
# ///

import json
import os
import pprint
import requests  # pyright: ignore[reportMissingModuleSource]
import click  # pyright: ignore[reportMissingImports, reportMissingModuleSource]
from typing import Dict, List, Optional


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


@click.group()
def cli():
    """CLI для управления моделями и провайдерами LLM."""
    pass


@cli.command()  # pyright: ignore[reportFunctionMemberAccess]
@click.option(
    "--provider",
    help="Фильтрация моделей по провайдеру (RouterAI, NeuroAPI, Caila.io, AgentPlatform)",
)
def models(provider: Optional[str]):
    """Отображает список моделей от всех провайдеров или от указанного провайдера."""
    providers = [
        RouterAIProvider(),
        NeuroAPIProvider(),
        CailaProvider(),
        AgentPlatformProvider(),
    ]

    if provider:
        # Фильтрация по провайдеру
        providers = [p for p in providers if p.name == provider]
        if not providers:
            click.echo(
                f"Провайдер '{provider}' не найден. Доступные провайдеры: RouterAI, NeuroAPI, Caila.io, AgentPlatform",
                err=True,
            )
            return

    results = {}

    for provider_obj in providers:
        click.echo(f"\n--- Получаем модели от {provider_obj.name} ---")
        models = provider_obj.fetch_models()

        if models is None:
            results[provider_obj.name] = "Ошибка/Нет данных"
            click.echo(f"❌ Ошибка при получении моделей от {provider_obj.name}")
        elif len(models) == 0:
            results[provider_obj.name] = "Список пуст"
            click.echo(f"⚠️ Список моделей пуст для {provider_obj.name}")
        else:
            results[provider_obj.name] = f"Найдено моделей: {len(models)}"
            # Сохраняем модели в файл
            filename = f"{provider_obj.name.replace('.', '')}.models.json"
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(models, f, ensure_ascii=False, indent=2)
            click.echo(f"✓ Модели сохранены в {filename}")
            # Выводим первые 3 модели для примера
            click.echo(f"Первые 3 модели ({provider_obj.name}):")
            pprint.pprint(models[:3])

    # Финальный отчёт
    click.echo("\n" + "=" * 50)
    click.echo("ФИНАЛЬНЫЙ ОТЧЁТ")
    click.echo("=" * 50)
    for provider_name, status in results.items():
        click.echo(f"{provider_name}: {status}")


@cli.command()  # pyright: ignore[reportFunctionMemberAccess]
@click.option(
    "--provider",
    help="Информация о конкретном провайдере (RouterAI, NeuroAPI, Caila.io, AgentPlatform)",
)
def providers(provider: Optional[str]):
    """Отображает информацию о всех провайдерах или о конкретном провайдере."""
    providers_list = [
        RouterAIProvider(),
        NeuroAPIProvider(),
        CailaProvider(),
        AgentPlatformProvider(),
    ]

    if provider:
        # Фильтрация по провайдеру
        providers_list = [p for p in providers_list if p.name == provider]
        if not providers_list:
            click.echo(
                f"Провайдер '{provider}' не найден. Доступные провайдеры: RouterAI, NeuroAPI, Caila.io, AgentPlatform",
                err=True,
            )
            return

    for prov in providers_list:
        click.echo(f"\n--- Информация о провайдере: {prov.name} ---")
        click.echo(f"Название: {prov.name}")
        click.echo(f"Базовый URL: {prov.base_url}")

        api_key = prov.get_api_key()
        if api_key:
            click.echo(f"API ключ: {'Доступен' if api_key else 'Не найден'}")
        else:
            click.echo("API ключ: Не найден")


if __name__ == "__main__":
    cli()
