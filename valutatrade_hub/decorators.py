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
            # Обрабатываем пользовательские исключения
            from valutatrade_hub.core.exceptions import ValutaTradeError

            if isinstance(e, ValutaTradeError):
                return str(e)
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


def log_action(action_name: str | None = None, verbose: bool = False):
    """
    Декоратор для логирования доменных операций.

    Логирует структурированную информацию об операциях:
    - timestamp (ISO)
    - action (BUY/SELL/REGISTER/LOGIN)
    - username/user_id
    - currency_code, amount
    - rate и base (если применимо)
    - result (OK/ERROR)
    - error_type/error_message при исключениях

    Args:
        action_name: Имя действия для логирования (если None, используется имя функции)
        verbose: Если True, добавляет дополнительный контекст (состояние кошелька и т.п.)

    Returns:
        Обёрнутая функция с логированием

    """
    from valutatrade_hub.logging_config import get_action_logger

    def decorator(func: F) -> F:
        logger = get_action_logger()
        action = (action_name or func.__name__).upper()

        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # Извлекаем информацию о пользователе и параметрах
            user_info = _extract_user_info(args, kwargs)
            currency_code = _extract_currency_code(args, kwargs)
            amount = _extract_amount(args, kwargs)

            try:
                result = func(*args, **kwargs)

                # Извлекаем rate и base из результата, если есть
                rate = None
                base = None
                if isinstance(result, dict):
                    rate = result.get("rate")
                    base = result.get("base")
                    # Если rate есть, но base нет, используем USD по умолчанию
                    if rate is not None and base is None:
                        base = "USD"

                # Формируем сообщение лога
                log_parts = [
                    f"action={action}",
                    f"user={user_info}",
                ]

                if currency_code:
                    log_parts.append(f"currency='{currency_code}'")
                if amount is not None:
                    log_parts.append(f"amount={amount:.4f}")
                if rate is not None:
                    log_parts.append(f"rate={rate:.2f}")
                if base:
                    log_parts.append(f"base='{base}'")

                log_parts.append("result=OK")

                # Добавляем verbose информацию
                if verbose and isinstance(result, dict):
                    if "old_balance" in result and "new_balance" in result:
                        log_parts.append(
                            f"wallet_balance={result['old_balance']:.4f}→{result['new_balance']:.4f}"
                        )

                log_message = " ".join(log_parts)
                logger.info(log_message)

                return result
            except Exception as e:
                # Извлекаем тип ошибки
                error_type = type(e).__name__
                error_message = str(e)

                # Формируем сообщение лога с ошибкой
                log_parts = [
                    f"action={action}",
                    f"user={user_info}",
                ]

                if currency_code:
                    log_parts.append(f"currency='{currency_code}'")
                if amount is not None:
                    log_parts.append(f"amount={amount:.4f}")

                log_parts.extend(
                    [
                        "result=ERROR",
                        f"error_type={error_type}",
                        f"error_message='{error_message}'",
                    ]
                )

                log_message = " ".join(log_parts)
                logger.error(log_message, exc_info=True)

                # Пробрасываем исключение дальше
                raise

        return wrapper  # type: ignore

    return decorator


def _extract_user_info(args: tuple, kwargs: dict) -> str:
    """Извлечь информацию о пользователе из аргументов."""
    from valutatrade_hub.core.models import User
    from valutatrade_hub.core.usecases import get_current_user

    # Пробуем найти user в аргументах
    for arg in args:
        if isinstance(arg, User):
            return f"'{arg.username}'"

    # Пробуем найти user в kwargs
    if "user" in kwargs:
        user = kwargs["user"]
        if isinstance(user, User):
            return f"'{user.username}'"

    # Пробуем найти username в kwargs
    if "username" in kwargs:
        return f"'{kwargs['username']}'"

    # Пробуем получить текущего пользователя
    current_user = get_current_user()
    if current_user:
        return f"'{current_user.username}'"

    return "unknown"


def _extract_currency_code(args: tuple, kwargs: dict) -> str | None:
    """Извлечь код валюты из аргументов."""
    # Пробуем найти currency_code в kwargs
    if "currency_code" in kwargs:
        return kwargs["currency_code"]
    if "currency" in kwargs:
        return kwargs["currency"]

    # Пробуем найти в args (обычно второй аргумент после user)
    for arg in args:
        if isinstance(arg, str) and len(arg) in (2, 3, 4, 5):
            # Простая эвристика: короткие строки могут быть кодами валют
            if arg.isupper() or arg.isalnum():
                return arg

    return None


def _extract_amount(args: tuple, kwargs: dict) -> float | None:
    """Извлечь сумму из аргументов."""
    if "amount" in kwargs:
        amount = kwargs["amount"]
        if isinstance(amount, (int, float)):
            return float(amount)
        if isinstance(amount, str):
            try:
                return float(amount)
            except ValueError:
                pass

    # Пробуем найти в args
    for arg in args:
        if isinstance(arg, (int, float)):
            return float(arg)

    return None
