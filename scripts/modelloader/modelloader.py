# /// script
# requires-python = ">=3.14"
# dependencies = [
#     "requests",
#     "click",
# ]
# ///

# NOTE: `os` and `requests` must be imported here at module level — tests patch
# `modelloader.os.path.expanduser` and `modelloader.requests.Session` directly.

import csv as CSV
import json
import os
import pprint
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional

import click  # pyright: ignore[reportMissingImports, reportMissingModuleSource]
import requests  # pyright: ignore[reportMissingModuleSource]

# ---------------------------------------------------------------------------
# Currency service
# ---------------------------------------------------------------------------

_CBR_URL = "https://www.cbr-xml-daily.ru/daily_json.js"
_CACHE_TTL = 3600


class CurrencyService:
    """Сервис курсов валют с кэшированием (TTL 1 час)."""

    def __init__(self) -> None:
        self._rate: Optional[float] = None
        self._cached_at: float = 0

    def get_usd_rate(self) -> Optional[float]:
        if self._rate is not None and time.time() - self._cached_at < _CACHE_TTL:
            return self._rate
        return self._fetch()

    def _fetch(self) -> Optional[float]:
        try:
            resp = requests.get(_CBR_URL, timeout=10)
            resp.raise_for_status()
            rate = resp.json()["Valute"]["USD"]["Value"]
            self._rate, self._cached_at = rate, time.time()
            return rate
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при получении курса ЦБРФ: {e}")
        except (KeyError, ValueError) as e:
            print(f"Ошибка парсинга данных ЦБРФ: {e}")
        return None


currency_service = CurrencyService()


def get_usd_rate_from_cbr() -> Optional[float]:
    """Совместимость: делегирует вызов в currency_service."""
    return currency_service.get_usd_rate()


# ---------------------------------------------------------------------------
# Base provider
# ---------------------------------------------------------------------------

_AUTH_PATH = "~/.local/share/opencode/auth.json"


class BaseProvider(ABC):
    """Абстрактный базовый класс провайдера моделей."""

    NAME: str = ""
    BASE_URL: str = ""
    AUTH_OPENJSON_ID: str = ""

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "LLM Price Monitor Script/1.0"})

    @property
    def name(self) -> str:
        return self.NAME

    @property
    def base_url(self) -> str:
        return self.BASE_URL

    def get_api_key(self) -> Optional[str]:
        """Читает API-ключ из auth.json."""
        auth_path = os.path.expanduser(_AUTH_PATH)
        try:
            with open(auth_path, "r") as f:
                auth_data = json.load(f)
            return auth_data.get(self.AUTH_OPENJSON_ID, {}).get("key")
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Ошибка при чтении auth.json: {e}")
        return None

    def _authed_headers(self) -> Optional[Dict[str, str]]:
        key = self.get_api_key()
        return (
            {"Authorization": f"Bearer {key}", "Accept": "application/json"}
            if key
            else None
        )

    def _safe_get(self, url: str, headers: Dict[str, str]) -> Optional[Dict]:
        """GET с единой обработкой ошибок."""
        try:
            resp = self.session.get(url, headers=headers, timeout=30)
            resp.raise_for_status()
            return resp.json()
        except requests.exceptions.Timeout as e:
            print(f"Таймаут при запросе к {self.name}: {e}")
        except requests.exceptions.RequestException as e:
            print(f"Ошибка при запросе к {self.name}: {e}")
        except ValueError as e:
            print(f"Неверный JSON от {self.name}: {e}")
        return None

    def fetch_models(self) -> Optional[List[Dict]]:
        """Получает список моделей через OpenAI-compatible API."""
        headers = self._authed_headers()
        if not headers:
            return None
        data = self._safe_get(f"{self.base_url}/models", headers)
        return data.get("data", data) if data else None

    @abstractmethod
    def fetch_prices(self) -> Optional[Dict]:
        """Возвращает словарь цен по model_id или None."""


# ---------------------------------------------------------------------------
# Provider implementations
# ---------------------------------------------------------------------------


class RouterAIProvider(BaseProvider):
    """RouterAI — цены в USD/токен, конвертируются в рубли по курсу 1:1."""

    NAME = "RouterAI"
    BASE_URL = "https://routerai.ru/api/v1"
    AUTH_OPENJSON_ID = "routerai"

    def fetch_prices(self) -> Optional[Dict]:
        headers = self._authed_headers()
        if not headers:
            return None
        data = self._safe_get(f"{self.base_url}/models", headers)
        if not data or "data" not in data:
            return None
        return {m.get("id", "unknown"): self._parse_price(m) for m in data["data"]}

    def _parse_price(self, model: Dict) -> Dict:
        pricing = model.get("pricing", {})
        prompt, completion = pricing.get("prompt"), pricing.get("completion")
        if prompt and completion:
            return {
                "prompt": prompt,
                "completion": completion,
                "prompt_rub_per_million": prompt * 1_000_000,
                "completion_rub_per_million": completion * 1_000_000,
                "currency": "RUB",
                "conversion_note": "RouterAI цены в USD/токен, переведены в рубли по курсу 1:1",
            }
        return {
            "prompt": None,
            "completion": None,
            "prompt_rub_per_million": None,
            "completion_rub_per_million": None,
            "currency": "RUB",
            "conversion_note": "RouterAI цены недоступны для конвертации",
        }


class NeuroAPIProvider(BaseProvider):
    """NeuroAPI — цены не предоставляются через API."""

    NAME = "NeuroAPI"
    BASE_URL = "https://neuroapi.host/v1"
    AUTH_OPENJSON_ID = "neuroapi"

    def fetch_prices(self) -> Optional[Dict]:
        headers = self._authed_headers()
        if not headers:
            return None
        data = self._safe_get(f"{self.base_url}/models", headers)
        if not data or "data" not in data:
            return None
        return {
            m.get("id", "unknown"): {"info": "Цены недоступны через API"}
            for m in data["data"]
        }


class CailaProvider(BaseProvider):
    """Caila.io — цены не предоставляются через API."""

    NAME = "Caila.io"
    BASE_URL = "https://caila.io/api/adapters/openai-direct"
    AUTH_OPENJSON_ID = "caila-oai"

    def fetch_prices(self) -> Optional[Dict]:
        return None


class AgentPlatformProvider(BaseProvider):
    """AgentPlatform — цены в RUB за 1M токенов."""

    NAME = "AgentPlatform"
    BASE_URL = "https://litellm.tokengate.ru/v1"
    PRICING_URL = "https://app.agentplatform.ru/api/v1/pricing/get"
    AUTH_OPENJSON_ID = "agentplatform"

    def fetch_prices(self) -> Optional[Dict]:
        headers = self._authed_headers()
        if not headers:
            return None
        data = self._safe_get(self.PRICING_URL, headers)
        items = data and data.get("data", {}).get("items")
        if not items:
            return None
        return {
            item.get("model_name", "unknown"): self._parse_item(item) for item in items
        }

    def _parse_item(self, item: Dict) -> Dict:
        info = item.get("model_info", {})
        inp, out = info.get("input_cost_per_token"), info.get("output_cost_per_token")
        return {
            "input": inp,
            "output": out,
            "input_rub_per_million": inp,
            "output_rub_per_million": out,
            "currency": "RUB",
            "conversion_note": "AgentPlatform цены в RUB за 1M токенов",
        }


# ---------------------------------------------------------------------------
# Provider registry
# ---------------------------------------------------------------------------

_ALL_PROVIDERS: List[type[BaseProvider]] = [
    RouterAIProvider,
    NeuroAPIProvider,
    CailaProvider,
    AgentPlatformProvider,
]

_PROVIDER_NAMES = ", ".join(cls.NAME for cls in _ALL_PROVIDERS)


def _resolve_providers(name: Optional[str]) -> Optional[List[BaseProvider]]:
    instances = [cls() for cls in _ALL_PROVIDERS]
    if not name:
        return instances
    filtered = [p for p in instances if p.name == name]
    if not filtered:
        click.echo(
            f"Провайдер '{name}' не найден. Доступные провайдеры: {_PROVIDER_NAMES}",
            err=True,
        )
        return None
    return filtered


# ---------------------------------------------------------------------------
# CLI display helpers
# ---------------------------------------------------------------------------


def _fmt_rub(value: float) -> str:
    return click.style(f"{value:,.2f}", fg="green")


def _print_price_entry(model_id: str, price: Dict) -> None:
    click.echo(f"  {model_id}:")
    note = price.get("conversion_note", "")

    if "prompt" in price and "completion" in price:
        p, c = price.get("prompt"), price.get("completion")
        if p and c:
            click.echo(
                f"    Prompt: {p} USD/токен → {_fmt_rub(p * 1_000_000)} руб/1M токенов"
            )
            click.echo(
                f"    Completion: {c} USD/токен → {_fmt_rub(c * 1_000_000)} руб/1M токенов"
            )
        else:
            click.echo(f"    {price}")
    elif "input" in price and "output" in price:
        i, o = price.get("input"), price.get("output")
        if i and o:
            click.echo(f"    Input: {_fmt_rub(i)} руб/1M токенов")
            click.echo(f"    Output: {_fmt_rub(o)} руб/1M токенов")
        else:
            click.echo(f"    {price}")
    else:
        click.echo(f"    {price}")

    if note:
        click.echo(f"    Примечание: {note}")


def _round_or_empty(value: Optional[float]) -> "str | float":
    return round(value, 2) if value is not None else ""


def _build_model_row(
    provider_name: str, model: Dict, price_info: Optional[Dict]
) -> Dict:
    """Строит плоский словарь строки для CSV."""
    row: Dict = {"provider": provider_name, "model_id": model.get("id", "")}

    empty = {
        "prompt_price_rub_per_million": "",
        "completion_price_rub_per_million": "",
        "prompt_price": "",
        "completion_price": "",
    }

    if price_info:
        if "prompt_rub_per_million" in price_info:
            row.update(
                {
                    "prompt_price_rub_per_million": _round_or_empty(
                        price_info.get("prompt_rub_per_million")
                    ),
                    "completion_price_rub_per_million": _round_or_empty(
                        price_info.get("completion_rub_per_million")
                    ),
                    "prompt_price": price_info.get("prompt", ""),
                    "completion_price": price_info.get("completion", ""),
                }
            )
        elif "input_rub_per_million" in price_info:
            row.update(
                {
                    "prompt_price_rub_per_million": _round_or_empty(
                        price_info.get("input_rub_per_million")
                    ),
                    "completion_price_rub_per_million": _round_or_empty(
                        price_info.get("output_rub_per_million")
                    ),
                    "prompt_price": price_info.get("input", ""),
                    "completion_price": price_info.get("output", ""),
                }
            )
        else:
            row.update(empty)
    else:
        row.update(empty)

    for key, val in model.items():
        row[key] = (
            json.dumps(val, ensure_ascii=False)
            if isinstance(val, (dict, list))
            else (str(val) if val is not None else "")
        )

    return row


# ---------------------------------------------------------------------------
# CLI commands
# ---------------------------------------------------------------------------


@click.group()
def cli() -> None:
    """CLI для управления моделями и провайдерами LLM."""


@cli.command()  # pyright: ignore[reportFunctionMemberAccess]
@click.option(
    "--provider", help=f"Фильтрация моделей по провайдеру ({_PROVIDER_NAMES})"
)
@click.option(
    "--dump", is_flag=True, help="Сохранить модели в JSON файлы в директории data"
)
@click.option(
    "--json", "json_output", is_flag=True, help="Выводить модели в формате JSON"
)
def models(provider: Optional[str], dump: bool, json_output: bool) -> None:
    """Отображает список моделей от всех провайдеров или от указанного провайдера."""
    provider_list = _resolve_providers(provider)
    if provider_list is None:
        return

    results, all_models = {}, {}
    for p in provider_list:
        click.echo(f"\n--- Получаем модели от {p.name} ---")
        fetched = p.fetch_models()

        if fetched is None:
            results[p.name] = "Ошибка/Нет данных"
            click.echo(f"❌ Ошибка при получении моделей от {p.name}")
        elif not fetched:
            results[p.name] = "Список пуст"
            click.echo(f"⚠️ Список моделей пуст для {p.name}")
        else:
            results[p.name] = f"Найдено моделей: {len(fetched)}"
            all_models[p.name] = fetched
            if dump:
                _dump_models(p.name, fetched)
            if not json_output:
                click.echo(f"Первые 3 модели ({p.name}):")
                pprint.pprint(fetched[:3])

    if json_output:
        output = {
            name: all_models.get(name, status) for name, status in results.items()
        }
        click.echo(json.dumps(output, ensure_ascii=False, indent=2))
    else:
        click.echo("\n" + "=" * 50)
        click.echo("ФИНАЛЬНЫЙ ОТЧЁТ")
        click.echo("=" * 50)
        for name, status in results.items():
            click.echo(f"{name}: {status}")


def _dump_models(provider_name: str, fetched: List) -> None:
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    filename = f"{provider_name.replace('.', '')}.models.json"
    with open(os.path.join(data_dir, filename), "w", encoding="utf-8") as f:
        json.dump(fetched, f, ensure_ascii=False, indent=2)
    click.echo(f"✓ Модели сохранены в data/{filename}")


@cli.command()  # pyright: ignore[reportFunctionMemberAccess]
@click.option(
    "--provider", help=f"Информация о конкретном провайдере ({_PROVIDER_NAMES})"
)
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Выводить информацию о провайдере в формате JSON",
)
def providers(provider: Optional[str], json_output: bool) -> None:
    """Отображает информацию о всех провайдерах или о конкретном провайдере."""
    provider_list = _resolve_providers(provider)
    if provider_list is None:
        return

    output_data = {}
    for p in provider_list:
        key_status = "Доступен" if p.get_api_key() else "Не найден"
        if json_output:
            output_data[p.name] = {
                "name": p.name,
                "base_url": p.base_url,
                "api_key": key_status,
            }
        else:
            click.echo(f"\n--- Информация о провайдере: {p.name} ---")
            click.echo(f"Название: {p.name}")
            click.echo(f"Базовый URL: {p.base_url}")
            click.echo(f"API ключ: {key_status}")

    if json_output:
        click.echo(json.dumps(output_data, ensure_ascii=False, indent=2))


@cli.command()  # pyright: ignore[reportFunctionMemberAccess]
def prices() -> None:
    """Вызывает метод fetch_prices для всех провайдеров и отображает результаты."""
    usd_rate = currency_service.get_usd_rate()
    click.echo(
        f"Курс USD/RUB (ЦБРФ): {usd_rate:.2f}"
        if usd_rate
        else "Предупреждение: Не удалось получить курс USD/RUB от ЦБРФ"
    )
    click.echo()

    for p in [cls() for cls in _ALL_PROVIDERS]:
        try:
            prices_data = p.fetch_prices()
            if prices_data:
                click.echo(f"Цены для {p.name}:")
                for model_id, price in prices_data.items():
                    if isinstance(price, dict):
                        _print_price_entry(model_id, price)
                    else:
                        click.echo(f"  {model_id}: {price}")
            else:
                click.echo(f"Не удалось получить цены для {p.name}")
        except NotImplementedError:
            click.echo(f"Метод fetch_prices не реализован для {p.name}")
        click.echo()


@cli.command()  # pyright: ignore[reportFunctionMemberAccess]
@click.option(
    "--field",
    "-f",
    multiple=True,
    help="Поля для включения в CSV (можно указать несколько раз). По умолчанию: provider, model_id, prompt_price, completion_price",
)
def csv(field) -> None:
    """
    Экспортирует данные о моделях и ценах в CSV файл.
    Принимает на вход множество опций --field/-f для указания полей, которые нужно включить в CSV.
    По умолчанию "provider name", "model id", "prompt (input) price" и "completion (output) price".
    Может включать все поля из JSON ответа каждого провайдера. Если поле отсутствует для модели, оставляет его пустым в CSV.
    CSV файл сохраняется в директории data с именем, включающим дату и время создания, например: llm_prices_2024-06-01_12-00-00.csv.
    """
    default_fields = [
        "provider",
        "model_id",
        "prompt_price_rub_per_million",
        "completion_price_rub_per_million",
    ]
    fields_to_include = list(field) if field else default_fields

    all_data = []
    for p in [cls() for cls in _ALL_PROVIDERS]:
        click.echo(f"Получаем данные от {p.name}...")
        fetched = p.fetch_models()
        if not fetched:
            click.echo(f"  ❌ Не удалось получить модели от {p.name}")
            continue
        prices_data = p.fetch_prices()
        for model in fetched:
            price_info = (prices_data or {}).get(model.get("id", ""))
            all_data.append(_build_model_row(p.name, model, price_info))

    if not all_data:
        click.echo("❌ Не удалось получить данные ни от одного провайдера")
        return

    available = {k for row in all_data for k in row}
    final_fields = [f for f in fields_to_include if f in available]
    for f in (f for f in fields_to_include if f not in available):
        click.echo(f"⚠️  Поле '{f}' не найдено в данных, пропускаем")

    data_dir = os.path.join(os.path.dirname(__file__), "data")
    os.makedirs(data_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filepath = os.path.join(data_dir, f"llm_prices_{timestamp}.csv")

    with open(filepath, "w", newline="", encoding="utf-8") as csvfile:
        writer = CSV.DictWriter(csvfile, fieldnames=final_fields)
        writer.writeheader()
        writer.writerows({f: row.get(f, "") for f in final_fields} for row in all_data)

    click.echo(f"✓ Данные экспортированы в {filepath}")
    click.echo(f"  Всего моделей: {len(all_data)}")
    click.echo(f"  Поля: {', '.join(final_fields)}")


if __name__ == "__main__":
    cli()
