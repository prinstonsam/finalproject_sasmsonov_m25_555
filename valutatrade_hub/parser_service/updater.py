"""Обновление курсов валют."""

import logging
from typing import Any

from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import config
from valutatrade_hub.parser_service.storage import (
    save_rate_to_history,
    save_rates_cache,
)

logger = logging.getLogger(__name__)


class RatesUpdater:
    """Класс для обновления курсов валют."""

    def __init__(
        self,
        coingecko_client: CoinGeckoClient | None = None,
        exchangerate_client: ExchangeRateApiClient | None = None,
    ) -> None:
        """
        Инициализация обновлятора курсов.

        Args:
            coingecko_client: Клиент CoinGecko (по умолчанию создается новый)
            exchangerate_client: Клиент ExchangeRate-API (по умолчанию создается новый)
        """
        self.coingecko_client = coingecko_client or CoinGeckoClient()
        self.exchangerate_client = exchangerate_client or ExchangeRateApiClient()

    def run_update(self, source: str | None = None) -> dict[str, Any]:
        """
        Запустить обновление курсов.

        Args:
            source: Источник для обновления ('coingecko', 'exchangerate' или None для всех)

        Returns:
            Словарь с результатами обновления
        """
        all_rates = {}
        all_sources = {}
        errors = []

        if source is None or source.lower() == "coingecko":
            try:
                logger.info("Fetching from CoinGecko...")
                rates = self.coingecko_client.fetch_rates()
                count = len(rates)
                all_rates.update(rates)
                for pair_key in rates:
                    all_sources[pair_key] = "CoinGecko"
                logger.info(f"Fetching from CoinGecko... OK ({count} rates)")
            except Exception as e:
                error_msg = f"Failed to fetch from CoinGecko: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        if source is None or source.lower() == "exchangerate":
            try:
                logger.info("Fetching from ExchangeRate-API...")
                rates = self.exchangerate_client.fetch_rates()
                count = len(rates)
                all_rates.update(rates)
                for pair_key in rates:
                    all_sources[pair_key] = "ExchangeRate-API"
                logger.info(f"Fetching from ExchangeRate-API... OK ({count} rates)")
            except Exception as e:
                error_msg = f"Failed to fetch from ExchangeRate-API: {str(e)}"
                logger.error(error_msg)
                errors.append(error_msg)

        if not all_rates:
            if errors:
                raise Exception("; ".join(errors))
            return {"updated": 0, "errors": []}

        logger.info(f"Writing {len(all_rates)} rates to {config.rates_file_path}...")

        save_rates_cache(all_rates, all_sources)

        for pair_key, rate in all_rates.items():
            from_currency, to_currency = pair_key.split("_", 1)
            source_name = all_sources.get(pair_key, "Unknown")
            save_rate_to_history(
                from_currency,
                to_currency,
                rate,
                source_name,
                meta={"request_timeout": config.REQUEST_TIMEOUT},
            )

        result = {
            "updated": len(all_rates),
            "errors": errors,
            "last_refresh": all_rates.get("last_refresh"),
        }

        return result
