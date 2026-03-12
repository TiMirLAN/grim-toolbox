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
    AUTH_OPENJSON_ID: str = ""

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
            if self.AUTH_OPENJSON_ID in auth_data:
                return auth_data[self.AUTH_OPENJSON_ID].get("key")
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

    def fetch_prices(self):
        raise NotImplementedError(
            "Метод fetch_prices должен быть реализован в подклассе."
        )


class RouterAIProvider(BaseProvider):
    """Провайдер RouterAI."""

    NAME = "RouterAI"
    BASE_URL = "https://routerai.ru/api/v1"
    AUTH_OPENJSON_ID = "routerai"

    def fetch_prices(self) -> Optional[Dict]:
        """
        Получает цены моделей от RouterAI.

        Returns:
            Словарь с ценами или None в случае ошибки
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
                prices = {}
                for model in data["data"]:
                    model_id = model.get("id", "unknown")
                    pricing = model.get("pricing", {})
                    if pricing:
                        prices[model_id] = {
                            "prompt": pricing.get("prompt"),
                            "completion": pricing.get("completion"),
                        }
                    else:
                        prices[model_id] = {"info": "Цены недоступны"}
                return prices
            return None
        except requests.exceptions.Timeout as e:
            print(f"Таймаут при запросе цен от {self.name}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе цен от {self.name}: {e}")
            return None
        except ValueError as e:
            print(f"Неверный JSON при запросе цен от {self.name}: {e}")
            return None


class NeuroAPIProvider(BaseProvider):
    """Провайдер NeuroAPI."""

    NAME = "NeuroAPI"
    BASE_URL = "https://neuroapi.host/v1"
    AUTH_OPENJSON_ID = "neuroapi"

    def fetch_prices(self) -> Optional[Dict]:
        """
        Получает цены моделей от NeuroAPI.

        Returns:
            Словарь с ценами или None в случае ошибки
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
                models = data["data"]
                prices = {}
                for model in models:
                    model_id = model.get("id", "unknown")
                    prices[model_id] = {"info": "Цены недоступны через API"}
                return prices
            return None
        except requests.exceptions.Timeout as e:
            print(f"Таймаут при запросе цен от {self.name}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе цен от {self.name}: {e}")
            return None
        except ValueError as e:
            print(f"Неверный JSON при запросе цен от {self.name}: {e}")
            return None


class CailaProvider(BaseProvider):
    """Провайдер Caila.io."""

    NAME = "Caila.io"
    BASE_URL = "https://caila.io/api/adapters/openai-direct"
    AUTH_OPENJSON_ID = "caila-oai"


class AgentPlatformProvider(BaseProvider):
    """Провайдер AgentPlatform."""

    NAME = "AgentPlatform"
    BASE_URL = "https://litellm.tokengate.ru/v1"
    PRICING_URL = "https://app.agentplatform.ru/api/v1/pricing/get"
    AUTH_OPENJSON_ID = "agentplatform"

    def fetch_prices(self) -> Optional[Dict]:
        """
        Получает цены моделей от AgentPlatform.

        Returns:
            Словарь с ценами или None в случае ошибки
        """
        api_key = self.get_api_key()
        if not api_key:
            return None

        headers = {"Authorization": f"Bearer {api_key}", "Accept": "application/json"}

        try:
            response = self.session.get(self.PRICING_URL, headers=headers, timeout=30)
            response.raise_for_status()
            data = response.json()
            if "data" in data and "items" in data["data"]:
                prices = {}
                for item in data["data"]["items"]:
                    model_name = item.get("model_name", "unknown")
                    model_info = item.get("model_info", {})
                    prices[model_name] = {
                        "input": model_info.get("input_cost_per_token"),
                        "output": model_info.get("output_cost_per_token"),
                    }
                return prices
            return None
        except requests.exceptions.Timeout as e:
            print(f"Таймаут при запросе цен от {self.name}: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе цен от {self.name}: {e}")
            return None
        except ValueError as e:
            print(f"Неверный JSON при запросе цен от {self.name}: {e}")
            return None


@click.group()
def cli():
    """CLI для управления моделями и провайдерами LLM."""
    pass


@cli.command()  # pyright: ignore[reportFunctionMemberAccess]
@click.option(
    "--provider",
    help="Фильтрация моделей по провайдеру (RouterAI, NeuroAPI, Caila.io, AgentPlatform)",
)
@click.option(
    "--dump",
    is_flag=True,
    help="Сохранить модели в JSON файлы в директории data",
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Выводить модели в формате JSON",
)
def models(provider: Optional[str], dump: bool, json_output: bool):
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
    all_models = {}

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
            all_models[provider_obj.name] = models

            # Сохраняем модели в файл в директории data при --dump
            if dump:
                data_dir = os.path.join(os.path.dirname(__file__), "data")
                os.makedirs(data_dir, exist_ok=True)
                filename = f"{provider_obj.name.replace('.', '')}.models.json"
                filepath = os.path.join(data_dir, filename)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(models, f, ensure_ascii=False, indent=2)
                click.echo(f"✓ Модели сохранены в data/{filename}")

            # Выводим первые 3 модели для примера, если не --json
            if not json_output:
                click.echo(f"Первые 3 модели ({provider_obj.name}):")
                pprint.pprint(models[:3])

    # Вывод результатов
    if json_output:
        # Вывод в формате JSON
        output = {}
        for provider_name, status in results.items():
            if isinstance(status, str) and status.startswith("Найдено моделей"):
                output[provider_name] = all_models.get(provider_name, [])
            else:
                output[provider_name] = status
        click.echo(json.dumps(output, ensure_ascii=False, indent=2))
    else:
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
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Выводить информацию о провайдере в формате JSON",
)
def providers(provider: Optional[str], json_output: bool):
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

    output_data = {}

    for prov in providers_list:
        if json_output:
            output_data[prov.name] = {
                "name": prov.name,
                "base_url": prov.base_url,
                "api_key": "Доступен" if prov.get_api_key() else "Не найден",
            }
        else:
            click.echo(f"\n--- Информация о провайдере: {prov.name} ---")
            click.echo(f"Название: {prov.name}")
            click.echo(f"Базовый URL: {prov.base_url}")

            api_key = prov.get_api_key()
            if api_key:
                click.echo(f"API ключ: Доступен")
            else:
                click.echo("API ключ: Не найден")

    if json_output:
        click.echo(json.dumps(output_data, ensure_ascii=False, indent=2))


@cli.command()  # pyright: ignore[reportFunctionMemberAccess]
def prices():
    """Вызывает метод fetch_prices для всех провайдеров и отображает результаты."""
    providers_list = [
        RouterAIProvider(),
        NeuroAPIProvider(),
        CailaProvider(),
        AgentPlatformProvider(),
    ]

    for provider in providers_list:
        try:
            prices_data = provider.fetch_prices()
            if prices_data:
                click.echo(f"Цены для {provider.name}:")
                for model, price in prices_data.items():
                    click.echo(f"  {model}: {price}")
            else:
                click.echo(f"Не удалось получить цены для {provider.name}")
        except NotImplementedError:
            click.echo(f"Метод fetch_prices не реализован для {provider.name}")


if __name__ == "__main__":
    cli()
