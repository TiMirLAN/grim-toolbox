# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "requests",
#     "click",
# ]
# ///

import csv as CSV
import json
import os
import pprint
from datetime import datetime
from typing import Dict, List, Optional
import time

import click  # pyright: ignore[reportMissingImports, reportMissingModuleSource]
import requests  # pyright: ignore[reportMissingModuleSource]

# Кэш для курса валют
_currency_cache = {"rate": None, "timestamp": 0, "currency": "USD"}


def get_usd_rate_from_cbr() -> Optional[float]:
    """
    Получает курс доллара к рублю от ЦБРФ.

    Returns:
        Курс USD/RUB или None в случае ошибки
    """
    global _currency_cache

    # Проверяем кэш (обновляем раз в час)
    current_time = time.time()
    if (
        _currency_cache["rate"] is not None
        and current_time - _currency_cache["timestamp"] < 3600
    ):
        return _currency_cache["rate"]

    try:
        # Используем официальный API ЦБРФ
        response = requests.get(
            "https://www.cbr-xml-daily.ru/daily_json.js", timeout=10
        )
        response.raise_for_status()
        data = response.json()

        if "Valute" in data and "USD" in data["Valute"]:
            rate = data["Valute"]["USD"]["Value"]
            _currency_cache = {
                "rate": rate,
                "timestamp": current_time,
                "currency": "USD",
            }
            return rate

    except requests.exceptions.RequestException as e:
        print(f"Ошибка при получении курса ЦБРФ: {e}")
    except (KeyError, ValueError) as e:
        print(f"Ошибка парсинга данных ЦБРФ: {e}")

    return None


def convert_to_rub_per_million_tokens(
    price_per_token: Optional[float], currency: str = "USD"
) -> Optional[float]:
    """
    Конвертирует цену в рубли за 1 миллион токенов.

    Args:
        price_per_token: Цена за один токен
        currency: Валюта исходной цены ("USD" или "RUB")

    Returns:
        Цена в рублях за 1 миллион токенов или None
    """
    if price_per_token is None:
        return None

    if currency == "RUB":
        # Если уже в рублях, просто умножаем на 1M
        return price_per_token * 1000000

    elif currency == "USD":
        # Конвертируем из USD в RUB
        usd_rate = get_usd_rate_from_cbr()
        if usd_rate is None:
            return None
        return price_per_token * 1000000 * usd_rate

    return None


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
                        prompt_price = pricing.get("prompt")
                        completion_price = pricing.get("completion")

                        # RouterAI API возвращает цены в USD за 1 токен (например, 0.0001798797 USD/токен)
                        # На сайте цены отображаются как рубли, но по факту это USD/1M (внутренний курс 1:1)
                        # Пример: 0.0001798797 USD/токен * 1,000,000 = 179.8797 USD/1M = 179₽ на сайте
                        if prompt_price and completion_price:
                            prompt_price_per_million = prompt_price * 1_000_000
                            completion_price_per_million = completion_price * 1_000_000
                            # Используем прямой перевод USD -> рубли (внутренний курс 1:1)
                            prompt_price_rub = prompt_price_per_million
                            completion_price_rub = completion_price_per_million
                            conversion_note = "RouterAI цены в USD/токен, переведены в рубли по курсу 1:1"
                        else:
                            prompt_price_rub = None
                            completion_price_rub = None
                            conversion_note = "RouterAI цены недоступны для конвертации"

                        prices[model_id] = {
                            "prompt": prompt_price,
                            "completion": completion_price,
                            "prompt_rub_per_million": prompt_price_rub,
                            "completion_rub_per_million": completion_price_rub,
                            "currency": "RUB",
                            "conversion_note": conversion_note,
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

    def fetch_prices(self) -> Optional[Dict]:
        """
        Получает цены моделей от Caila.io.

        Returns:
            Словарь с ценами или None в случае ошибки
        """
        # Caila.io не предоставляет информацию о ценах через API
        # Возвращаем None, так как цены недоступны
        return None


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
                    input_price = model_info.get("input_cost_per_token")
                    output_price = model_info.get("output_cost_per_token")

                    # AgentPlatform уже предоставляет цены в рублях за 1M токенов
                    # Добавляем их как есть, плюс исходные значения для отладки
                    prices[model_name] = {
                        "input": input_price,
                        "output": output_price,
                        "input_rub_per_million": input_price,
                        "output_rub_per_million": output_price,
                        "currency": "RUB",
                        "conversion_note": "AgentPlatform цены в RUB за 1M токенов",
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
                click.echo("API ключ: Доступен")
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

    # Выводим информацию о курсе валют
    usd_rate = get_usd_rate_from_cbr()
    if usd_rate:
        click.echo(f"Курс USD/RUB (ЦБРФ): {usd_rate:.2f}")
    else:
        click.echo("Предупреждение: Не удалось получить курс USD/RUB от ЦБРФ")
    click.echo()

    for provider in providers_list:
        try:
            prices_data = provider.fetch_prices()
            if prices_data:
                click.echo(f"Цены для {provider.name}:")
                for model, price in prices_data.items():
                    if isinstance(price, dict):
                        # Форматируем вывод для моделей с детальной информацией о ценах
                        conversion_note = price.get("conversion_note", "")

                        if "prompt" in price and "completion" in price:
                            # RouterAI формат
                            prompt_orig = price.get("prompt")
                            completion_orig = price.get("completion")

                            click.echo(f"  {model}:")
                            if prompt_orig and completion_orig:
                                prompt_per_million = prompt_orig * 1_000_000
                                completion_per_million = completion_orig * 1_000_000
                                prompt_rub = click.style(
                                    f"{prompt_per_million:,.2f}", fg="green"
                                )
                                completion_rub = click.style(
                                    f"{completion_per_million:,.2f}", fg="green"
                                )
                                click.echo(
                                    f"    Prompt: {prompt_orig} USD/токен → {prompt_rub} руб/1M токенов"
                                )
                                click.echo(
                                    f"    Completion: {completion_orig} USD/токен → {completion_rub} руб/1M токенов"
                                )
                            else:
                                click.echo(f"    {price}")
                            if conversion_note:
                                click.echo(f"    Примечание: {conversion_note}")
                        elif "input" in price and "output" in price:
                            # AgentPlatform формат
                            input_price = price.get("input")
                            output_price = price.get("output")

                            click.echo(f"  {model}:")
                            if input_price and output_price:
                                input_rub = click.style(
                                    f"{input_price:,.2f}", fg="green"
                                )
                                output_rub = click.style(
                                    f"{output_price:,.2f}", fg="green"
                                )
                                click.echo(f"    Input: {input_rub} руб/1M токенов")
                                click.echo(f"    Output: {output_rub} руб/1M токенов")
                            else:
                                click.echo(f"    {price}")
                            if conversion_note:
                                click.echo(f"    Примечание: {conversion_note}")
                        elif "input" in price and "output" in price:
                            # AgentPlatform формат
                            input_price = price.get("input")
                            output_price = price.get("output")

                            click.echo(f"  {model}:")
                            if input_price and output_price:
                                input_rub = click.style(
                                    f"{input_price:,.2f} руб/1M токенов", fg="green"
                                )
                                output_rub = click.style(
                                    f"{output_price:,.2f} руб/1M токенов", fg="green"
                                )
                                click.echo(f"    Input: → {input_rub}")
                                click.echo(f"    Output: → {output_rub}")
                            else:
                                click.echo(f"    {price}")
                            if conversion_note:
                                click.echo(f"    Примечание: {conversion_note}")
                        else:
                            click.echo(f"  {model}: {price}")
                    else:
                        click.echo(f"  {model}: {price}")
            else:
                click.echo(f"Не удалось получить цены для {provider.name}")
        except NotImplementedError:
            click.echo(f"Метод fetch_prices не реализован для {provider.name}")
        click.echo()


@cli.command()  # pyright: ignore[reportFunctionMemberAccess]
@click.option(
    "--field",
    "-f",
    multiple=True,
    help="Поля для включения в CSV (можно указать несколько раз). По умолчанию: provider, model_id, prompt_price, completion_price",
)
def csv(field):
    """
    Экспортирует данные о моделях и ценах в CSV файл.
    Принимает на вход множество опций --field/-f для указания полей, которые нужно включить в CSV.
    По умолчанию "provider name", "model id", "prompt (input) price" и "completion (output) price".
    Может включать все поля из JSON ответа каждого провайдера. Если поле отсутствует для модели, оставляет его пустым в CSV.
    CSV файл сохраняется в директории data с именем, включающим дату и время создания, например: llm_prices_2024-06-01_12-00-00.csv.
    """

    # Определяем поля по умолчанию (теперь используем конвертированные цены в рублях за 1M токенов)
    default_fields = [
        "provider",
        "model_id",
        "prompt_price_rub_per_million",
        "completion_price_rub_per_million",
    ]

    # Используем указанные поля или поля по умолчанию
    fields_to_include = list(field) if field else default_fields

    # Инициализация провайдеров
    providers = [
        RouterAIProvider(),
        NeuroAPIProvider(),
        CailaProvider(),
        AgentPlatformProvider(),
    ]

    # Собираем данные о моделях и ценах
    all_data = []

    for provider in providers:
        click.echo(f"Получаем данные от {provider.name}...")

        # Получаем модели
        models = provider.fetch_models()
        if not models:
            click.echo(f"  ❌ Не удалось получить модели от {provider.name}")
            continue

        # Получаем цены
        prices = provider.fetch_prices()

        # Обрабатываем каждую модель
        for model in models:
            model_data = {"provider": provider.name}

            # Добавляем базовые поля
            model_id = model.get("id", "")
            model_data["model_id"] = model_id

            # Добавляем цены в зависимости от провайдера
            if prices and model_id in prices:
                price_info = prices[model_id]

                # RouterAI использует prompt/completion (конвертированные цены)
                if "prompt_rub_per_million" in price_info:
                    prompt_val = price_info.get("prompt_rub_per_million")
                    completion_val = price_info.get("completion_rub_per_million")
                    model_data["prompt_price_rub_per_million"] = (
                        round(prompt_val, 2) if prompt_val is not None else ""
                    )
                    model_data["completion_price_rub_per_million"] = (
                        round(completion_val, 2) if completion_val is not None else ""
                    )
                    # Для совместимости добавляем исходные цены
                    model_data["prompt_price"] = price_info.get("prompt", "")
                    model_data["completion_price"] = price_info.get("completion", "")
                # AgentPlatform использует input/output (уже в рублях за 1M токенов)
                elif "input_rub_per_million" in price_info:
                    input_val = price_info.get("input_rub_per_million")
                    output_val = price_info.get("output_rub_per_million")
                    model_data["prompt_price_rub_per_million"] = (
                        round(input_val, 2) if input_val is not None else ""
                    )
                    model_data["completion_price_rub_per_million"] = (
                        round(output_val, 2) if output_val is not None else ""
                    )
                    # Для совместимости добавляем исходные цены
                    model_data["prompt_price"] = price_info.get("input", "")
                    model_data["completion_price"] = price_info.get("output", "")
                # NeuroAPI и Caila не предоставляют цены через API
                else:
                    model_data["prompt_price_rub_per_million"] = ""
                    model_data["completion_price_rub_per_million"] = ""
                    model_data["prompt_price"] = ""
                    model_data["completion_price"] = ""
            else:
                model_data["prompt_price_rub_per_million"] = ""
                model_data["completion_price_rub_per_million"] = ""
                model_data["prompt_price"] = ""
                model_data["completion_price"] = ""

            # Добавляем все поля из JSON ответа провайдера
            for key, value in model.items():
                # Преобразуем вложенные объекты в строки для CSV
                if isinstance(value, dict):
                    model_data[key] = json.dumps(value, ensure_ascii=False)
                elif isinstance(value, list):
                    model_data[key] = json.dumps(value, ensure_ascii=False)
                else:
                    model_data[key] = str(value) if value is not None else ""

            all_data.append(model_data)

    if not all_data:
        click.echo("❌ Не удалось получить данные ни от одного провайдера")
        return

    # Создаем директорию data, если её нет
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)

    # Генерируем имя файла с датой и временем
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"llm_prices_{timestamp}.csv"
    filepath = os.path.join(data_dir, filename)

    # Определяем заголовки CSV
    # Используем только указанные поля, но добавляем все доступные поля из данных
    available_fields = set()
    for row in all_data:
        available_fields.update(row.keys())

    # Фильтруем поля, оставляя только те, что указаны в --field или доступны в данных
    final_fields = []
    for f in fields_to_include:
        if f in available_fields:
            final_fields.append(f)
        else:
            click.echo(f"⚠️  Поле '{f}' не найдено в данных, пропускаем")

    # Filter all_data to include only final_fields
    filtered_data = []
    for row in all_data:
        filtered_row = {field: row.get(field, "") for field in final_fields}
        filtered_data.append(filtered_row)

    # Записываем CSV файл
    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = CSV.DictWriter(csvfile, fieldnames=final_fields)
        writer.writeheader()
        writer.writerows(filtered_data)

    click.echo(f"✓ Данные экспортированы в {filepath}")
    click.echo(f"  Всего моделей: {len(filtered_data)}")
    click.echo(f"  Поля: {', '.join(final_fields)}")


if __name__ == "__main__":
    cli()
