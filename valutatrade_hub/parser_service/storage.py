"""Хранение курсов валют."""

import json
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any

from valutatrade_hub.core.exceptions import DatabaseError
from valutatrade_hub.parser_service.config import config


def save_rate_to_history(
    from_currency: str,
    to_currency: str,
    rate: float,
    source: str,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Сохранить курс в историю exchange_rates.json.

    Args:
        from_currency: Исходная валюта
        to_currency: Целевая валюта
        rate: Курс обмена
        source: Источник данных
        meta: Дополнительные метаданные

    Returns:
        Словарь с записью истории
    """
    timestamp = datetime.utcnow().isoformat() + "Z"
    record_id = f"{from_currency}_{to_currency}_{timestamp}"

    record = {
        "id": record_id,
        "from_currency": from_currency.upper(),
        "to_currency": to_currency.upper(),
        "rate": rate,
        "timestamp": timestamp,
        "source": source,
        "meta": meta or {},
    }

    history_file = config.history_file_path
    history_file.parent.mkdir(parents=True, exist_ok=True)

    history = []
    if history_file.exists():
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                history = json.load(f)
        except (json.JSONDecodeError, IOError):
            history = []

    history.append(record)

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=history_file.parent, delete=False
        ) as tmp_file:
            json.dump(history, tmp_file, indent=2, ensure_ascii=False)
            tmp_path = Path(tmp_file.name)

        tmp_path.replace(history_file)
    except IOError as e:
        raise DatabaseError(f"Ошибка сохранения истории курсов: {str(e)}") from e

    return record


def save_rates_cache(rates: dict[str, float], sources: dict[str, str]) -> None:
    """
    Сохранить курсы в кеш rates.json.

    Args:
        rates: Словарь курсов {"CURRENCY_USD": rate, ...}
        sources: Словарь источников {"CURRENCY_USD": "CoinGecko", ...}
    """
    timestamp = datetime.utcnow().isoformat() + "Z"

    cache_data = {
        "pairs": {},
        "source": "ParserService",
        "last_refresh": timestamp,
    }

    for pair_key, rate in rates.items():
        source = sources.get(pair_key, "Unknown")
        cache_data["pairs"][pair_key] = {
            "rate": rate,
            "updated_at": timestamp,
            "source": source,
        }

    cache_file = config.rates_file_path
    cache_file.parent.mkdir(parents=True, exist_ok=True)

    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=cache_file.parent, delete=False
        ) as tmp_file:
            json.dump(cache_data, tmp_file, indent=2, ensure_ascii=False)
            tmp_path = Path(tmp_file.name)

        tmp_path.replace(cache_file)
    except IOError as e:
        raise DatabaseError(f"Ошибка сохранения кеша курсов: {str(e)}") from e
