"""API клиенты для получения курсов валют."""

from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import config


class BaseApiClient(ABC):
    """Базовый класс для API клиентов."""

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """
        Получить курсы валют.

        Returns:
            Словарь с курсами в формате {"CURRENCY_USD": rate, ...}

        Raises:
            ApiRequestError: При ошибке запроса к API
        """
        pass


class CoinGeckoClient(BaseApiClient):
    """Клиент для работы с CoinGecko API."""

    def fetch_rates(self) -> dict[str, float]:
        """
        Получить курсы криптовалют из CoinGecko.

        Returns:
            Словарь с курсами в формате {"BTC_USD": 59337.21, ...}

        Raises:
            ApiRequestError: При ошибке запроса к API
        """
        crypto_ids = [
            config.CRYPTO_ID_MAP[code]
            for code in config.CRYPTO_CURRENCIES
            if code in config.CRYPTO_ID_MAP
        ]

        if not crypto_ids:
            return {}

        ids_param = ",".join(crypto_ids)
        url = f"{config.COINGECKO_URL}?ids={ids_param}&vs_currencies=usd"

        try:
            response = requests.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            rates = {}
            for code in config.CRYPTO_CURRENCIES:
                if code in config.CRYPTO_ID_MAP:
                    coin_id = config.CRYPTO_ID_MAP[code]
                    if coin_id in data and "usd" in data[coin_id]:
                        rates[f"{code}_{config.BASE_CURRENCY}"] = float(
                            data[coin_id]["usd"]
                        )

            return rates

        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"Ошибка при запросе к CoinGecko: {str(e)}")
        except (KeyError, ValueError, TypeError) as e:
            raise ApiRequestError(f"Ошибка при обработке ответа CoinGecko: {str(e)}")


class ExchangeRateApiClient(BaseApiClient):
    """Клиент для работы с ExchangeRate-API."""

    def fetch_rates(self) -> dict[str, float]:
        """
        Получить курсы фиатных валют из ExchangeRate-API.

        Returns:
            Словарь с курсами в формате {"EUR_USD": 1.0786, ...}

        Raises:
            ApiRequestError: При ошибке запроса к API
        """
        url = config.get_exchangerate_url()

        try:
            response = requests.get(url, timeout=config.REQUEST_TIMEOUT)
            response.raise_for_status()
            data = response.json()

            if data.get("result") != "success":
                error_msg = data.get("error-type", "Unknown error")
                raise ApiRequestError(f"ExchangeRate-API вернул ошибку: {error_msg}")

            rates_data = data.get("rates", {})
            rates = {}

            for code in config.FIAT_CURRENCIES:
                if code in rates_data:
                    if code == config.BASE_CURRENCY:
                        rates[f"{code}_{config.BASE_CURRENCY}"] = 1.0
                    else:
                        rate = float(rates_data[code])
                        rates[f"{code}_{config.BASE_CURRENCY}"] = rate

            return rates

        except requests.exceptions.RequestException as e:
            raise ApiRequestError(f"Ошибка при запросе к ExchangeRate-API: {str(e)}")
        except (KeyError, ValueError, TypeError) as e:
            raise ApiRequestError(
                f"Ошибка при обработке ответа ExchangeRate-API: {str(e)}"
            )
