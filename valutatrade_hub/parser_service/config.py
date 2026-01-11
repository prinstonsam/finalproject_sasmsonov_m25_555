"""Конфигурация Parser Service."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ParserConfig:
    """Конфигурация для Parser Service."""

    EXCHANGERATE_API_KEY: str | None = None
    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"
    BASE_CURRENCY: str = "USD"
    FIAT_CURRENCIES: tuple = ("EUR", "GBP", "RUB", "JPY", "CNY", "CHF", "CAD", "AUD")
    CRYPTO_CURRENCIES: tuple = ("BTC", "ETH", "SOL", "USDT", "BNB", "ADA", "XRP", "DOGE")
    CRYPTO_ID_MAP: dict = {
        "BTC": "bitcoin",
        "ETH": "ethereum",
        "SOL": "solana",
        "USDT": "tether",
        "BNB": "binancecoin",
        "ADA": "cardano",
        "XRP": "ripple",
        "DOGE": "dogecoin",
    }
    REQUEST_TIMEOUT: int = 10

    def __post_init__(self) -> None:
        """Инициализация после создания объекта."""
        if self.EXCHANGERATE_API_KEY is None:
            self.EXCHANGERATE_API_KEY = os.getenv("EXCHANGERATE_API_KEY")
            if not self.EXCHANGERATE_API_KEY:
                api_key_file = Path(__file__).parent.parent.parent.parent / "api_key.txt"
                if api_key_file.exists():
                    try:
                        self.EXCHANGERATE_API_KEY = (
                            api_key_file.read_text(encoding="utf-8").strip()
                        )
                    except IOError:
                        pass

    @property
    def rates_file_path(self) -> Path:
        """Получить путь к файлу rates.json."""
        from valutatrade_hub.infra.settings import settings

        return settings.data_dir / "rates.json"

    @property
    def history_file_path(self) -> Path:
        """Получить путь к файлу exchange_rates.json."""
        from valutatrade_hub.infra.settings import settings

        return settings.data_dir / "exchange_rates.json"

    def get_exchangerate_url(self) -> str:
        """
        Получить полный URL для ExchangeRate-API.

        Returns:
            Полный URL с API-ключом

        Raises:
            ValueError: Если API-ключ не установлен
        """
        if not self.EXCHANGERATE_API_KEY:
            raise ValueError(
                "EXCHANGERATE_API_KEY не установлен. "
                "Установите переменную окружения EXCHANGERATE_API_KEY"
            )
        return f"{self.EXCHANGERATE_API_URL}/{self.EXCHANGERATE_API_KEY}/latest/{self.BASE_CURRENCY}"


config = ParserConfig()
