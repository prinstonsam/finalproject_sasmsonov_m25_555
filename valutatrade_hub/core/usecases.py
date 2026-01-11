"""Бизнес-логика."""

import hashlib
import secrets
from datetime import datetime
from typing import Iterator

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    AuthenticationError,
    CurrencyNotFoundError,
    ExchangeRateNotFoundError,
    UserNotFoundError,
    ValidationError,
    WalletNotFoundError,
)
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.core.utils import (
    convert_currency_amount,
    get_next_user_id,
    load_portfolios,
    load_rates,
    load_users,
    save_portfolios,
    save_rates,
    save_users,
)
from valutatrade_hub.decorators import (
    log_action,
)
from valutatrade_hub.infra.settings import settings

_current_user: User | None = None


def get_current_user() -> User | None:
    """Получить текущего залогиненного пользователя."""
    return _current_user


def set_current_user(user: User | None) -> None:
    """Установить текущего пользователя."""
    global _current_user
    _current_user = user


@log_action("register_user")
def register_user(username: str, password: str) -> tuple[User, Portfolio]:
    """
    Зарегистрировать нового пользователя.

    Args:
        username: Имя пользователя
        password: Пароль

    Returns:
        Кортеж (пользователь, портфель)

    Raises:
        ValidationError: Если данные некорректны
    """
    if len(password) < 4:
        raise ValidationError("Пароль должен быть не короче 4 символов")

    users = load_users()
    if any(user["username"] == username for user in users):
        raise ValidationError(f"Имя пользователя '{username}' уже занято")

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


@log_action("login_user")
def login_user(username: str, password: str) -> User:
    """
    Войти в систему.

    Args:
        username: Имя пользователя
        password: Пароль

    Returns:
        Объект пользователя

    Raises:
        UserNotFoundError: Если пользователь не найден
        AuthenticationError: Если пароль неверный
    """
    users = load_users()
    user_data = next((u for u in users if u["username"] == username), None)

    if user_data is None:
        raise UserNotFoundError(f"Пользователь '{username}' не найден")

    user = User.from_dict(user_data)

    if not user.verify_password(password):
        raise AuthenticationError("Неверный пароль")

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


def _update_exchange_rate_from_api(
    from_currency: str, to_currency: str
) -> tuple[float, str]:
    """
    Обновить курс валют из внешнего API (заглушка).

    Args:
        from_currency: Исходная валюта
        to_currency: Целевая валюта

    Returns:
        Кортеж (курс, время обновления в ISO формате)

    Raises:
        ApiRequestError: Если ошибка при обращении к внешнему API
    """
    from datetime import datetime

    # Заглушка: в реальной реализации здесь был бы запрос к внешнему API
    # Для демонстрации используем фиксированные курсы из Portfolio
    if (
        from_currency in Portfolio.EXCHANGE_RATES
        and to_currency in Portfolio.EXCHANGE_RATES
    ):
        from_rate = Portfolio.EXCHANGE_RATES[from_currency]
        to_rate = Portfolio.EXCHANGE_RATES[to_currency]
        rate = from_rate / to_rate
        updated_at = datetime.now().isoformat()

        # Сохраняем обновлённый курс
        rates = load_rates()
        rate_key = f"{from_currency}_{to_currency}"
        rates[rate_key] = {
            "rate": rate,
            "updated_at": updated_at,
        }
        save_rates(rates)

        return rate, updated_at

    # Если курс недоступен даже в фиксированных курсах
    raise ApiRequestError(
        f"Не удалось получить курс {from_currency}→{to_currency} из внешнего API"
    )


@log_action("get_exchange_rate")
def get_exchange_rate(
    from_currency: str, to_currency: str, use_cache: bool = True
) -> tuple[float, str | None]:
    """
    Получить курс обмена валют.

    Args:
        from_currency: Исходная валюта
        to_currency: Целевая валюта
        use_cache: Использовать кеш (по умолчанию True)

    Returns:
        Кортеж (курс, время обновления или None)

    Raises:
        CurrencyNotFoundError: Если валюта не найдена
        ExchangeRateNotFoundError: Если курс недоступен
        ApiRequestError: Если ошибка при обращении к внешнему API
        InvalidCurrencyCodeError: Если код валюты некорректен
    """
    from datetime import datetime, timedelta

    from valutatrade_hub.core.currencies import get_currency

    # Валидация валют через get_currency()
    try:
        get_currency(from_currency)
    except CurrencyNotFoundError:
        raise CurrencyNotFoundError(from_currency)

    try:
        get_currency(to_currency)
    except CurrencyNotFoundError:
        raise CurrencyNotFoundError(to_currency)

    if from_currency == to_currency:
        return 1.0, None

    rates = load_rates()
    rates_ttl = settings.get("rates_ttl_seconds", 3600)

    rate_pairs = rates.get("pairs", {}) if isinstance(rates, dict) else rates

    rate_key = f"{from_currency}_{to_currency}"
    rate_data = None
    updated_at = None

    if rate_key in rate_pairs and isinstance(rate_pairs[rate_key], dict):
        rate_data = rate_pairs[rate_key]
        updated_at = rate_data.get("updated_at")

        # Проверяем свежесть курса, если use_cache=True
        if use_cache and updated_at:
            try:
                updated_time = datetime.fromisoformat(updated_at)
                ttl = timedelta(seconds=rates_ttl)
                if datetime.now() - updated_time < ttl:
                    # Курс свежий, возвращаем его
                    return rate_data["rate"], updated_at
                else:
                    # Курс устарел, пытаемся обновить
                    try:
                        rate, updated_at = _update_exchange_rate_from_api(
                            from_currency, to_currency
                        )
                        return rate, updated_at
                    except ApiRequestError:
                        # Не удалось обновить, но возвращаем старый курс
                        return rate_data["rate"], updated_at
            except (ValueError, TypeError):
                # Если не удалось распарсить время, используем курс как есть
                pass

        if rate_data:
            return rate_data["rate"], updated_at

    reverse_key = f"{to_currency}_{from_currency}"
    if reverse_key in rate_pairs and isinstance(rate_pairs[reverse_key], dict):
        rate_data = rate_pairs[reverse_key]
        updated_at = rate_data.get("updated_at")

        # Проверяем свежесть курса
        if use_cache and updated_at:
            try:
                updated_time = datetime.fromisoformat(updated_at)
                ttl = timedelta(seconds=rates_ttl)
                if datetime.now() - updated_time < ttl:
                    return 1.0 / rate_data["rate"], updated_at
                else:
                    # Курс устарел, пытаемся обновить
                    try:
                        rate, updated_at = _update_exchange_rate_from_api(
                            to_currency, from_currency
                        )
                        return 1.0 / rate, updated_at
                    except ApiRequestError:
                        return 1.0 / rate_data["rate"], updated_at
            except (ValueError, TypeError):
                pass

        return 1.0 / rate_data["rate"], updated_at

    # Пытаемся получить курс из API
    try:
        rate, updated_at = _update_exchange_rate_from_api(from_currency, to_currency)
        return rate, updated_at
    except ApiRequestError:
        # Если API недоступен, используем фиксированные курсы как fallback
        if (
            from_currency in Portfolio.EXCHANGE_RATES
            and to_currency in Portfolio.EXCHANGE_RATES
        ):
            from_rate = Portfolio.EXCHANGE_RATES[from_currency]
            to_rate = Portfolio.EXCHANGE_RATES[to_currency]
            return from_rate / to_rate, None

        raise ExchangeRateNotFoundError(
            f"Курс {from_currency}→{to_currency} недоступен"
        )


@log_action("buy_currency", verbose=True)
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
        ValidationError: Если amount <= 0
        CurrencyNotFoundError: Если валюта не найдена
        ExchangeRateNotFoundError: Если курс недоступен
    """
    from valutatrade_hub.core.currencies import get_currency

    # Валидация amount > 0
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise ValidationError("Сумма покупки должна быть положительным числом")
    amount = float(amount)

    # Валидация currency_code через get_currency()
    try:
        currency = get_currency(currency_code)
        currency_code = currency.code  # Нормализованный код
    except CurrencyNotFoundError:
        raise CurrencyNotFoundError(currency_code)

    # Безопасная операция: чтение → модификация → запись
    portfolio = get_user_portfolio(user.user_id)

    # Получаем или создаём кошелёк
    wallet = portfolio.get_wallet(currency_code)
    if wallet is None:
        wallet = portfolio.add_currency(currency_code)

    old_balance = wallet.balance
    wallet.deposit(amount)
    new_balance = wallet.balance

    # Получаем курс для расчёта стоимости
    rate = None
    cost_usd = None
    try:
        rate, _ = get_exchange_rate(currency_code, "USD")
        cost_usd = convert_currency_amount(amount, currency_code, "USD", rate)
    except ExchangeRateNotFoundError:
        # Курс недоступен, но операция продолжается
        pass

    # Сохраняем портфель
    save_portfolio(portfolio)

    return {
        "currency": currency_code,
        "amount": amount,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "rate": rate,
        "base": "USD" if rate is not None else None,
        "cost_usd": cost_usd,
    }


@log_action("sell_currency", verbose=True)
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
        ValidationError: Если amount <= 0
        CurrencyNotFoundError: Если валюта не найдена
        WalletNotFoundError: Если кошелёк не найден
        InsufficientFundsError: Если недостаточно средств
        ExchangeRateNotFoundError: Если курс недоступен
    """
    from valutatrade_hub.core.currencies import get_currency

    # Валидация amount > 0
    if not isinstance(amount, (int, float)) or amount <= 0:
        raise ValidationError("Сумма продажи должна быть положительным числом")
    amount = float(amount)

    # Валидация currency_code через get_currency()
    try:
        currency = get_currency(currency_code)
        currency_code = currency.code  # Нормализованный код
    except CurrencyNotFoundError:
        raise CurrencyNotFoundError(currency_code)

    # Безопасная операция: чтение → модификация → запись
    portfolio = get_user_portfolio(user.user_id)
    wallet = portfolio.get_wallet(currency_code)

    if wallet is None:
        raise WalletNotFoundError(
            f"У вас нет кошелька '{currency_code}'. "
            "Добавьте валюту: она создаётся автоматически при первой покупке."
        )

    # Проверка средств (InsufficientFundsError выбрасывается в wallet.withdraw)
    old_balance = wallet.balance
    wallet.withdraw(amount)  # Может выбросить InsufficientFundsError
    new_balance = wallet.balance

    # Получаем курс для расчёта выручки
    rate = None
    revenue_usd = None
    try:
        rate, _ = get_exchange_rate(currency_code, "USD")
        revenue_usd = convert_currency_amount(amount, currency_code, "USD", rate)
    except ExchangeRateNotFoundError:
        # Курс недоступен, но операция продолжается
        pass

    # Сохраняем портфель
    save_portfolio(portfolio)

    return {
        "currency": currency_code,
        "amount": amount,
        "old_balance": old_balance,
        "new_balance": new_balance,
        "rate": rate,
        "base": "USD" if rate is not None else None,
        "revenue_usd": revenue_usd,
    }
