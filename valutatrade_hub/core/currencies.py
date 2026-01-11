"""Классы для работы с валютами."""

from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import (
    CurrencyNotFoundError,
    InvalidCurrencyCodeError,
)


class Currency(ABC):
    """
    Абстрактный базовый класс для валют.

    Инварианты:
    - code: верхний регистр, 2-5 символов, без пробелов
    - name: не пустая строка
    """

    def __init__(self, code: str, name: str):
        """
        Инициализация валюты.

        Args:
            code: Код валюты (например, "USD", "BTC")
            name: Название валюты (например, "US Dollar", "Bitcoin")

        Raises:
            InvalidCurrencyCodeError: Если код валюты некорректен
            ValueError: Если имя пустое
        """
        # Валидация кода валюты
        if not code or not isinstance(code, str):
            raise InvalidCurrencyCodeError("Код валюты не может быть пустым")

        code = code.strip().upper()

        if " " in code:
            raise InvalidCurrencyCodeError("Код валюты не может содержать пробелы")

        if len(code) < 2 or len(code) > 5:
            raise InvalidCurrencyCodeError(
                f"Код валюты должен быть от 2 до 5 символов, получено: {code}"
            )

        # Валидация имени
        if not name or not isinstance(name, str) or not name.strip():
            raise ValueError("Имя валюты не может быть пустым")

        # Public атрибуты
        self.code = code
        self.name = name.strip()

    @abstractmethod
    def get_display_info(self) -> str:
        """
        Получить строковое представление для UI/логов.

        Returns:
            Строковое представление валюты
        """
        pass

    @abstractmethod
    def get_type(self) -> str:
        """
        Получить тип валюты (для обратной совместимости).

        Returns:
            Тип валюты (например, "fiat" или "crypto")
        """
        pass

    def __str__(self) -> str:
        """Строковое представление валюты."""
        return f"{self.code} ({self.name})"

    def __repr__(self) -> str:
        """Представление валюты для отладки."""
        return f"{self.__class__.__name__}(code='{self.code}', name='{self.name}')"

    def __eq__(self, other: object) -> bool:
        """Проверка равенства валют по коду."""
        if not isinstance(other, Currency):
            return False
        return self.code == other.code

    def __hash__(self) -> int:
        """Хеш валюты по коду."""
        return hash(self.code)


class FiatCurrency(Currency):
    """
    Класс для фиатных валют (USD, EUR, RUB и т.д.).

    Формат get_display_info(): "[FIAT] USD — US Dollar (Issuing: United States)"
    """

    def __init__(self, code: str, name: str, issuing_country: str):
        """
        Инициализация фиатной валюты.

        Args:
            code: Код валюты
            name: Название валюты
            issuing_country: Страна/зона эмиссии (например, "United States", "Eurozone")
        """
        super().__init__(code, name)
        # Public атрибут
        self.issuing_country = issuing_country

    def get_display_info(self) -> str:
        """
        Получить строковое представление для UI/логов.

        Returns:
            Строка в формате: "[FIAT] USD — US Dollar (Issuing: United States)"
        """
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"

    def get_type(self) -> str:
        """Получить тип валюты."""
        return "fiat"


class CryptoCurrency(Currency):
    """
    Класс для криптовалют (BTC, ETH и т.д.).

    Формат get_display_info(): "[CRYPTO] BTC — Bitcoin (Algo: SHA-256, MCAP: 1.12e12)"
    """

    def __init__(self, code: str, name: str, algorithm: str, market_cap: float):
        """
        Инициализация криптовалюты.

        Args:
            code: Код валюты
            name: Название валюты
            algorithm: Алгоритм консенсуса (например, "SHA-256", "Ethash")
            market_cap: Рыночная капитализация (последняя известная)
        """
        super().__init__(code, name)
        # Public атрибуты
        self.algorithm = algorithm
        self.market_cap = market_cap

    def get_display_info(self) -> str:
        """
        Получить строковое представление для UI/логов.

        Returns:
            Строка в формате: "[CRYPTO] BTC — Bitcoin (Algo: SHA-256, MCAP: 1.12e12)"
        """
        # Форматируем market_cap без знака "+" перед экспонентой
        mcap_str = f"{self.market_cap:.2e}".replace("e+", "e")
        return f"[CRYPTO] {self.code} — {self.name} (Algo: {self.algorithm}, MCAP: {mcap_str})"

    def get_type(self) -> str:
        """Получить тип валюты."""
        return "crypto"


# Реестр валют (фабрика)
_CURRENCY_REGISTRY: dict[str, Currency] = {}


def _initialize_currency_registry() -> None:
    """Инициализировать реестр валют с предопределёнными валютами."""
    global _CURRENCY_REGISTRY

    # Фиатные валюты
    fiat_currencies = [
        FiatCurrency("USD", "US Dollar", "United States"),
        FiatCurrency("EUR", "Euro", "Eurozone"),
        FiatCurrency("GBP", "British Pound", "United Kingdom"),
        FiatCurrency("RUB", "Russian Ruble", "Russia"),
        FiatCurrency("JPY", "Japanese Yen", "Japan"),
        FiatCurrency("CNY", "Chinese Yuan", "China"),
        FiatCurrency("CHF", "Swiss Franc", "Switzerland"),
        FiatCurrency("CAD", "Canadian Dollar", "Canada"),
        FiatCurrency("AUD", "Australian Dollar", "Australia"),
    ]

    # Криптовалюты
    crypto_currencies = [
        CryptoCurrency("BTC", "Bitcoin", "SHA-256", 1.12e12),
        CryptoCurrency("ETH", "Ethereum", "Ethash", 4.5e11),
        CryptoCurrency("USDT", "Tether", "Various", 8.3e10),
        CryptoCurrency("BNB", "Binance Coin", "BEP-20", 4.2e10),
        CryptoCurrency("SOL", "Solana", "Proof of History", 3.8e10),
        CryptoCurrency("ADA", "Cardano", "Ouroboros", 1.5e10),
        CryptoCurrency("XRP", "Ripple", "Consensus Protocol", 2.8e10),
        CryptoCurrency("DOGE", "Dogecoin", "Scrypt", 1.2e10),
    ]

    # Регистрируем все валюты
    for currency in fiat_currencies + crypto_currencies:
        _CURRENCY_REGISTRY[currency.code] = currency


def get_currency(code: str) -> Currency:
    """
    Фабричный метод для получения валюты по коду.

    Args:
        code: Код валюты

    Returns:
        Объект Currency

    Raises:
        CurrencyNotFoundError: Если валюта с таким кодом не найдена
        InvalidCurrencyCodeError: Если код валюты некорректен
    """
    # Инициализируем реестр при первом вызове
    if not _CURRENCY_REGISTRY:
        _initialize_currency_registry()

    # Валидация и нормализация кода
    if not code or not isinstance(code, str):
        raise InvalidCurrencyCodeError("Код валюты не может быть пустым")

    code = code.strip().upper()

    # Проверяем наличие валюты в реестре
    if code not in _CURRENCY_REGISTRY:
        raise CurrencyNotFoundError(code)

    return _CURRENCY_REGISTRY[code]


# Инициализируем реестр при импорте модуля
_initialize_currency_registry()
