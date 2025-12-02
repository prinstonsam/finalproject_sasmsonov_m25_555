"""Вспомогательные функции."""

import json
from functools import reduce
from pathlib import Path
from typing import Iterator

from valutatrade_hub.core.models import Portfolio, Wallet

# Пути к файлам данных
BASE_DIR = Path(__file__).parent.parent.parent
DATA_DIR = BASE_DIR / "data"
USERS_FILE = DATA_DIR / "users.json"
PORTFOLIOS_FILE = DATA_DIR / "portfolios.json"
RATES_FILE = DATA_DIR / "rates.json"


def load_users() -> list[dict]:
    """
    Загрузить список пользователей из JSON.

    Returns:
        Список пользователей
    """
    if not USERS_FILE.exists():
        return []
    with open(USERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_users(users: list[dict]) -> None:
    """
    Сохранить список пользователей в JSON.

    Args:
        users: Список пользователей
    """
    USERS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2, ensure_ascii=False)


def load_portfolios() -> list[dict]:
    """
    Загрузить список портфелей из JSON.

    Returns:
        Список портфелей
    """
    if not PORTFOLIOS_FILE.exists():
        return []
    with open(PORTFOLIOS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_portfolios(portfolios: list[dict]) -> None:
    """
    Сохранить список портфелей в JSON.

    Args:
        portfolios: Список портфелей
    """
    PORTFOLIOS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(PORTFOLIOS_FILE, "w", encoding="utf-8") as f:
        json.dump(portfolios, f, indent=2, ensure_ascii=False)


def load_rates() -> dict:
    """
    Загрузить курсы валют из JSON.

    Returns:
        Словарь с курсами валют
    """
    if not RATES_FILE.exists():
        return {}
    with open(RATES_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_rates(rates: dict) -> None:
    """
    Сохранить курсы валют в JSON.

    Args:
        rates: Словарь с курсами валют
    """
    RATES_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(RATES_FILE, "w", encoding="utf-8") as f:
        json.dump(rates, f, indent=2, ensure_ascii=False)


def get_next_user_id() -> int:
    """
    Получить следующий доступный ID пользователя.

    Returns:
        Следующий ID пользователя
    """
    users = load_users()
    if not users:
        return 1
    return max((user["user_id"] for user in users), default=0) + 1


def filter_users_by_username(username: str) -> Iterator[dict]:
    """
    Генератор для фильтрации пользователей по имени.

    Args:
        username: Имя пользователя для поиска

    Yields:
        Словари пользователей, соответствующих критерию
    """
    users = load_users()
    yield from (user for user in users if user.get("username") == username)


def map_wallets_to_currency_codes(portfolio: Portfolio) -> Iterator[str]:
    """
    Генератор кодов валют из портфеля.

    Args:
        portfolio: Портфель

    Yields:
        Коды валют
    """
    yield from (wallet.currency_code for wallet in portfolio.wallets.values())


def reduce_portfolio_value(portfolio: Portfolio, base_currency: str = "USD") -> float:
    """
    Функциональный подход к подсчёту стоимости портфеля.

    Args:
        portfolio: Портфель
        base_currency: Базовая валюта

    Returns:
        Общая стоимость портфеля
    """
    from valutatrade_hub.core.usecases import get_exchange_rate

    def calculate_value(acc: float, wallet: Wallet) -> float:
        """Аккумулятор для подсчёта стоимости."""
        try:
            if wallet.currency_code == base_currency:
                return acc + wallet.balance
            rate, _ = get_exchange_rate(wallet.currency_code, base_currency)
            return acc + wallet.balance * rate
        except ValueError:
            return acc

    return reduce(calculate_value, portfolio.wallets.values(), 0.0)
