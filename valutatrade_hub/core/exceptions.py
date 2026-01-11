"""Пользовательские исключения для проекта."""


class ValutaTradeError(Exception):
    """Базовое исключение для всех ошибок ValutaTrade Hub."""

    pass


class CurrencyError(ValutaTradeError):
    """Ошибка, связанная с валютами."""

    pass


class CurrencyNotFoundError(CurrencyError):
    """Валюта не найдена."""

    def __init__(self, code: str):
        """
        Инициализация исключения.

        Args:
            code: Код валюты
        """
        message = f"Неизвестная валюта '{code}'"
        super().__init__(message)
        self.code = code


class InvalidCurrencyCodeError(CurrencyError):
    """Некорректный код валюты."""

    pass


class ExchangeRateError(ValutaTradeError):
    """Ошибка, связанная с курсами обмена."""

    pass


class ExchangeRateNotFoundError(ExchangeRateError):
    """Курс обмена не найден."""

    pass


class UserError(ValutaTradeError):
    """Ошибка, связанная с пользователями."""

    pass


class UserNotFoundError(UserError):
    """Пользователь не найден."""

    pass


class AuthenticationError(UserError):
    """Ошибка аутентификации."""

    pass


class WalletError(ValutaTradeError):
    """Ошибка, связанная с кошельками."""

    pass


class InsufficientFundsError(WalletError):
    """Недостаточно средств на балансе."""

    def __init__(self, available: float, required: float, code: str):
        """
        Инициализация исключения.

        Args:
            available: Доступная сумма
            required: Требуемая сумма
            code: Код валюты
        """
        message = f"Недостаточно средств: доступно {available} {code}, требуется {required} {code}"
        super().__init__(message)
        self.available = available
        self.required = required
        self.code = code


class WalletNotFoundError(WalletError):
    """Кошелёк не найден."""

    pass


class ValidationError(ValutaTradeError):
    """Ошибка валидации данных."""

    pass


class DatabaseError(ValutaTradeError):
    """Ошибка работы с базой данных."""

    pass


class ApiRequestError(ExchangeRateError):
    """Ошибка при обращении к внешнему API."""

    def __init__(self, reason: str):
        """
        Инициализация исключения.

        Args:
            reason: Причина ошибки
        """
        message = f"Ошибка при обращении к внешнему API: {reason}"
        super().__init__(message)
        self.reason = reason
