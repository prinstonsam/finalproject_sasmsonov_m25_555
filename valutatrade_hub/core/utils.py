"""Вспомогательные функции."""

from functools import reduce
from typing import Iterator

from valutatrade_hub.core.exceptions import InvalidCurrencyCodeError, ValidationError
from valutatrade_hub.core.models import Portfolio, Wallet
from valutatrade_hub.infra.database import database

# Совместимость со старым кодом - используем database manager
load_users = database.load_users
save_users = database.save_users
load_portfolios = database.load_portfolios
save_portfolios = database.save_portfolios
load_rates = database.load_rates
save_rates = database.save_rates


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


# Валидация валютных кодов
FIAT_CURRENCIES = {"USD", "EUR", "GBP", "RUB", "JPY", "CNY", "CHF", "CAD", "AUD"}
CRYPTO_CURRENCIES = {"BTC", "ETH", "USDT", "BNB", "SOL", "ADA", "XRP", "DOGE"}


def validate_currency_code(currency_code: str) -> str:
    """
    Валидация кода валюты.

    Args:
        currency_code: Код валюты для валидации

    Returns:
        Валидированный код валюты (в верхнем регистре)

    Raises:
        InvalidCurrencyCodeError: Если код валюты некорректен
    """
    if not currency_code or not isinstance(currency_code, str):
        raise InvalidCurrencyCodeError("Код валюты не может быть пустым")
    
    currency_code = currency_code.strip().upper()
    
    if len(currency_code) < 2 or len(currency_code) > 10:
        raise InvalidCurrencyCodeError(f"Код валюты должен быть от 2 до 10 символов: {currency_code}")
    
    if not currency_code.isalnum():
        raise InvalidCurrencyCodeError(f"Код валюты должен содержать только буквы и цифры: {currency_code}")
    
    return currency_code


def is_fiat_currency(currency_code: str) -> bool:
    """
    Проверить, является ли валюта фиатной.

    Args:
        currency_code: Код валюты

    Returns:
        True если фиатная, False иначе
    """
    currency_code = validate_currency_code(currency_code)
    return currency_code in FIAT_CURRENCIES


def is_crypto_currency(currency_code: str) -> bool:
    """
    Проверить, является ли валюта криптовалютой.

    Args:
        currency_code: Код валюты

    Returns:
        True если криптовалюта, False иначе
    """
    currency_code = validate_currency_code(currency_code)
    return currency_code in CRYPTO_CURRENCIES


def convert_currency_amount(
    amount: float,
    from_currency: str,
    to_currency: str,
    exchange_rate: float,
) -> float:
    """
    Конвертировать сумму из одной валюты в другую.

    Args:
        amount: Сумма для конвертации
        from_currency: Исходная валюта
        to_currency: Целевая валюта
        exchange_rate: Курс обмена (from_currency к to_currency)

    Returns:
        Конвертированная сумма

    Raises:
        ValidationError: Если данные некорректны
    """
    if not isinstance(amount, (int, float)):
        raise ValidationError("Сумма должна быть числом")
    
    if amount < 0:
        raise ValidationError("Сумма не может быть отрицательной")
    
    if not isinstance(exchange_rate, (int, float)) or exchange_rate <= 0:
        raise ValidationError("Курс обмена должен быть положительным числом")
    
    validate_currency_code(from_currency)
    validate_currency_code(to_currency)
    
    if from_currency == to_currency:
        return amount
    
    return amount * exchange_rate


def format_currency_amount(amount: float, currency_code: str, decimals: int = 2) -> str:
    """
    Форматировать сумму валюты для отображения.

    Args:
        amount: Сумма
        currency_code: Код валюты
        decimals: Количество знаков после запятой

    Returns:
        Отформатированная строка
    """
    validate_currency_code(currency_code)
    return f"{amount:,.{decimals}f} {currency_code}"
