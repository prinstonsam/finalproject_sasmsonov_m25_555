"""Бизнес-логика."""

import hashlib
import secrets
from datetime import datetime
from typing import Iterator

from valutatrade_hub.core.decorators import (
    validate_amount,
    validate_currency_code,
)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import (
    get_next_user_id,
    load_portfolios,
    load_rates,
    load_users,
    save_portfolios,
    save_users,
)

_current_user: User | None = None


def get_current_user() -> User | None:
    """Получить текущего залогиненного пользователя."""
    return _current_user


def set_current_user(user: User | None) -> None:
    """Установить текущего пользователя."""
    global _current_user
    _current_user = user


def register_user(username: str, password: str) -> tuple[User, Portfolio]:
    """
    Зарегистрировать нового пользователя.

    Args:
        username: Имя пользователя
        password: Пароль

    Returns:
        Кортеж (пользователь, портфель)

    Raises:
        ValueError: Если имя пользователя уже занято или пароль слишком короткий
    """
    if len(password) < 4:
        raise ValueError("Пароль должен быть не короче 4 символов")

    users = load_users()
    if any(user["username"] == username for user in users):
        raise ValueError(f"Имя пользователя '{username}' уже занято")

    # Создаём пользователя
    user_id = get_next_user_id()
    salt = secrets.token_hex(8)
    hashed_password = hashlib.sha256((password + salt).encode()).hexdigest()
    registration_date = datetime.now()

    user = User(
        user_id=user_id,
        username=username,
        hashed_password=hashed_password,
        salt=salt,
        registration_date=registration_date,
    )

    # Сохраняем пользователя
    users.append(user.to_dict())
    save_users(users)

    # Создаём пустой портфель
    portfolio = Portfolio(user_id=user_id, wallets={})
    portfolios = load_portfolios()
    portfolios.append(portfolio.to_dict())
    save_portfolios(portfolios)

    return user, portfolio


def login_user(username: str, password: str) -> User:
    """
    Войти в систему.

    Args:
        username: Имя пользователя
        password: Пароль

    Returns:
        Объект пользователя

    Raises:
        ValueError: Если пользователь не найден или пароль неверный
    """
    users = load_users()
    user_data = next((u for u in users if u["username"] == username), None)

    if user_data is None:
        raise ValueError(f"Пользователь '{username}' не найден")

    user = User.from_dict(user_data)

    if not user.verify_password(password):
        raise ValueError("Неверный пароль")

    set_current_user(user)
    return user


def get_user_portfolio(user_id: int) -> Portfolio:
    """
    Получить портфель пользователя.

    Args:
        user_id: ID пользователя

    Returns:
        Объект портфеля
    """
    portfolios = load_portfolios()

    portfolio_data = next((p for p in portfolios if p["user_id"] == user_id), None)

    if portfolio_data is None:
        # Создаём пустой портфель, если его нет
        portfolio = Portfolio(user_id=user_id, wallets={})
        portfolios.append(portfolio.to_dict())
        save_portfolios(portfolios)
        return portfolio

    return Portfolio.from_dict(portfolio_data)


def get_all_portfolios() -> Iterator[Portfolio]:
    """
    Генератор всех портфелей.

    Yields:
        Объекты портфелей
    """
    portfolios = load_portfolios()
    yield from (Portfolio.from_dict(p) for p in portfolios)


def save_portfolio(portfolio: Portfolio) -> None:
    """
    Сохранить портфель.

    Args:
        portfolio: Объект портфеля
    """
    portfolios = load_portfolios()
    portfolio_dict = portfolio.to_dict()

    # Находим и обновляем существующий портфель
    for i, p in enumerate(portfolios):
        if p["user_id"] == portfolio.user_id:
            portfolios[i] = portfolio_dict
            break
    else:
        portfolios.append(portfolio_dict)

    save_portfolios(portfolios)


def get_exchange_rate(from_currency: str, to_currency: str, use_cache: bool = True) -> tuple[float, str | None]:
    """
    Получить курс обмена валют.

    Args:
        from_currency: Исходная валюта
        to_currency: Целевая валюта
        use_cache: Использовать кеш (по умолчанию True)

    Returns:
        Кортеж (курс, время обновления или None)

    Raises:
        ValueError: Если курс недоступен
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return 1.0, None

    rates = load_rates()

    # Пробуем найти прямой курс
    rate_key = f"{from_currency}_{to_currency}"
    if rate_key in rates and isinstance(rates[rate_key], dict):
        rate_data = rates[rate_key]
        updated_at = rate_data.get("updated_at")
        return rate_data["rate"], updated_at

    # Пробуем обратный курс
    reverse_key = f"{to_currency}_{from_currency}"
    if reverse_key in rates and isinstance(rates[reverse_key], dict):
        rate_data = rates[reverse_key]
        updated_at = rate_data.get("updated_at")
        return 1.0 / rate_data["rate"], updated_at

    # Используем фиксированные курсы из Portfolio как fallback
    if from_currency in Portfolio.EXCHANGE_RATES and to_currency in Portfolio.EXCHANGE_RATES:
        from_rate = Portfolio.EXCHANGE_RATES[from_currency]
        to_rate = Portfolio.EXCHANGE_RATES[to_currency]
        return from_rate / to_rate, None

    raise ValueError(f"Курс {from_currency}→{to_currency} недоступен")


@validate_currency_code
@validate_amount
def buy_currency(user: User, currency_code: str, amount: float) -> dict:
    """
    Купить валюту.

    Args:
        user: Пользователь
        currency_code: Код валюты
        amount: Количество валюты

    Returns:
        Словарь с информацией о покупке

    Raises:
        ValueError: Если данные некорректны или курс недоступен
    """

    portfolio = get_user_portfolio(user.user_id)

    # Получаем или создаём кошелёк
    wallet = portfolio.get_wallet(currency_code)
    if wallet is None:
        wallet = portfolio.add_currency(currency_code)

    old_balance = wallet.balance
    wallet.deposit(amount)
    new_balance = wallet.balance

    # Получаем курс для расчёта стоимости
    try:
        rate, _ = get_exchange_rate(currency_code, "USD")
        cost_usd = amount * rate
    except ValueError:
        cost_usd = None
        rate = None

    save_portfolio(portfolio)

    return {
        "currency": currency_code,
        "amount": amount,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "rate": rate if cost_usd is not None else None,
        "cost_usd": cost_usd,
    }


@validate_currency_code
@validate_amount
def sell_currency(user: User, currency_code: str, amount: float) -> dict:
    """
    Продать валюту.

    Args:
        user: Пользователь
        currency_code: Код валюты
        amount: Количество валюты

    Returns:
        Словарь с информацией о продаже

    Raises:
        ValueError: Если данные некорректны, кошелёк не найден или недостаточно средств
    """

    portfolio = get_user_portfolio(user.user_id)
    wallet = portfolio.get_wallet(currency_code)

    if wallet is None:
        raise ValueError(
            f"У вас нет кошелька '{currency_code}'. "
            "Добавьте валюту: она создаётся автоматически при первой покупке."
        )

    if amount > wallet.balance:
        raise ValueError(
            f"Недостаточно средств: доступно {wallet.balance:.4f} {currency_code}, "
            f"требуется {amount:.4f} {currency_code}"
        )

    old_balance = wallet.balance
    wallet.withdraw(amount)
    new_balance = wallet.balance

    # Получаем курс для расчёта выручки
    try:
        rate, _ = get_exchange_rate(currency_code, "USD")
        revenue_usd = amount * rate
    except ValueError:
        revenue_usd = None
        rate = None

    save_portfolio(portfolio)

    return {
        "currency": currency_code,
        "amount": amount,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "rate": rate if revenue_usd is not None else None,
        "revenue_usd": revenue_usd,
    }
