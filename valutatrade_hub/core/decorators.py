"""Декораторы для функционального программирования."""

from functools import wraps
from typing import Any, Callable, TypeVar

F = TypeVar("F", bound=Callable[..., Any])


def require_login(func: F) -> F:
    """
    Декоратор для проверки авторизации пользователя.

    Args:
        func: Функция, требующая авторизации

    Returns:
        Обёрнутая функция
    """
    from valutatrade_hub.core.usecases import get_current_user

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if get_current_user() is None:
            raise ValueError("Сначала выполните login")
        return func(*args, **kwargs)

    return wrapper  # type: ignore


def validate_currency_code(func: F) -> F:
    """
    Декоратор для валидации кода валюты в аргументах.

    Args:
        func: Функция с аргументом currency или currency_code

    Returns:
        Обёрнутая функция
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Ищем currency или currency_code в kwargs или args
        currency_keys = ["currency", "currency_code", "from_currency", "to_currency"]
        for key in currency_keys:
            if key in kwargs:
                value = kwargs[key]
                if isinstance(value, str) and value.strip():
                    kwargs[key] = value.strip().upper()
                elif not value or not str(value).strip():
                    raise ValueError("Код валюты не может быть пустым")

        return func(*args, **kwargs)

    return wrapper  # type: ignore


def validate_amount(func: F) -> F:
    """
    Декоратор для валидации суммы в аргументах.

    Args:
        func: Функция с аргументом amount

    Returns:
        Обёрнутая функция
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        if "amount" in kwargs:
            amount = kwargs["amount"]
            if isinstance(amount, str):
                try:
                    amount = float(amount)
                except ValueError:
                    raise ValueError("'amount' должен быть положительным числом")
            if not isinstance(amount, (int, float)) or amount <= 0:
                raise ValueError("'amount' должен быть положительным числом")
            kwargs["amount"] = float(amount)

        return func(*args, **kwargs)

    return wrapper  # type: ignore


def handle_errors(func: F) -> F:
    """
    Декоратор для обработки ошибок с понятными сообщениями.

    Args:
        func: Функция для обёртки

    Returns:
        Обёрнутая функция
    """

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        try:
            return func(*args, **kwargs)
        except ValueError as e:
            return str(e)
        except KeyError as e:
            return f"Отсутствует обязательный параметр: {e}"
        except Exception as e:
            return f"Ошибка: {str(e)}"

    return wrapper  # type: ignore


def cache_result(func: F) -> F:
    """
    Декоратор для кеширования результатов функции.

    Args:
        func: Функция для кеширования

    Returns:
        Обёрнутая функция с кешем
    """
    cache: dict[tuple, Any] = {}

    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # Создаём ключ кеша из аргументов
        cache_key = (args, tuple(sorted(kwargs.items())))
        if cache_key not in cache:
            cache[cache_key] = func(*args, **kwargs)
        return cache[cache_key]

    return wrapper  # type: ignore

