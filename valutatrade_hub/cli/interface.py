"""Команды."""

import argparse
import shlex
from datetime import datetime
from typing import Callable

from prettytable import PrettyTable

from valutatrade_hub.core.exceptions import (
    ApiRequestError,
    CurrencyNotFoundError,
    ExchangeRateNotFoundError,
    InsufficientFundsError,
    ValidationError,
    WalletNotFoundError,
)
from valutatrade_hub.core.models import Portfolio
from valutatrade_hub.core.usecases import (
    buy_currency,
    get_current_user,
    get_exchange_rate,
    get_user_portfolio,
    login_user,
    register_user,
    sell_currency,
)
from valutatrade_hub.decorators import handle_errors, require_login
from valutatrade_hub.infra.settings import settings


def validate_currency(currency_code: str) -> str:
    if not currency_code or not currency_code.strip():
        raise ValueError("Код валюты не может быть пустым")
    return currency_code.strip().upper()


def validate_amount_str(amount: str | float) -> float:
    if isinstance(amount, str):
        try:
            value = float(amount)
            if value <= 0:
                raise ValueError("Сумма должна быть положительным числом")
            return value
        except ValueError as e:
            if "Сумма должна быть" in str(e):
                raise
            raise ValueError("'amount' должен быть положительным числом")
    if amount <= 0:
        raise ValueError("Сумма должна быть положительным числом")
    return float(amount)


@handle_errors
def cmd_register(args: argparse.Namespace) -> str:
    """Команда регистрации пользователя."""
    username = (args.username or "").strip()
    password = args.password

    if not username:
        return "Имя пользователя не может быть пустым"

    user, portfolio = register_user(username, password)
    return (
        f"Пользователь '{username}' зарегистрирован (id={user.user_id}). "
        f"Войдите: login --username {username} --password ****"
    )


@handle_errors
def cmd_login(args: argparse.Namespace) -> str:
    """Команда входа в систему."""
    username = args.username
    password = args.password

    login_user(username, password)
    return f"Вы вошли как '{username}'"


@handle_errors
@require_login
def cmd_show_portfolio(args: argparse.Namespace) -> str:
    """Команда показа портфеля."""
    user = get_current_user()
    if user is None:
        return "Сначала выполните login"

    # Используем настройку из конфигурации или аргумент командной строки
    default_base = settings.get("default_base_currency", "USD")
    base_currency = (args.base or default_base).upper()
    portfolio = get_user_portfolio(user.user_id)

    if not portfolio.wallets:
        return f"Портфель пользователя '{user.username}' пуст"

    # Создаём таблицу
    table = PrettyTable()
    table.field_names = ["Валюта", "Баланс", f"→ {base_currency}"]

    def calculate_wallet_value(
        wallet_data: tuple[str, Portfolio],
    ) -> tuple[str, float, float]:
        """Генератор для расчёта стоимости кошелька."""
        currency_code, wallet = wallet_data
        balance = wallet.balance

        try:
            if currency_code == base_currency:
                value = balance
            else:
                rate, _ = get_exchange_rate(
                    currency_code, base_currency, use_cache=True
                )
                value = balance * rate
            return currency_code, balance, value
        except ValueError:
            return currency_code, balance, None

    wallet_values = map(
        calculate_wallet_value, sorted(portfolio.wallets.items(), key=lambda x: x[0])
    )

    total_value = 0.0
    for currency_code, balance, value in wallet_values:
        if value is not None:
            total_value += value
            table.add_row(
                [currency_code, f"{balance:.2f}", f"{value:.2f} {base_currency}"]
            )
        else:
            table.add_row([currency_code, f"{balance:.2f}", "N/A"])

    result = f"Портфель пользователя '{user.username}' (база: {base_currency}):\n"
    result += table.get_string()
    result += f"\n---------------------------------\nИТОГО: {total_value:,.2f} {base_currency}"

    return result


@handle_errors
@require_login
def cmd_buy(args: argparse.Namespace) -> str:
    """
    Команда покупки валюты.

    Обрабатывает исключения:
    - ValidationError: некорректные данные
    - CurrencyNotFoundError: неизвестная валюта
    - ExchangeRateNotFoundError: курс недоступен
    """
    user = get_current_user()
    if user is None:
        return "Сначала выполните login"

    currency_code = validate_currency(args.currency)
    amount = validate_amount_str(args.amount)

    try:
        result = buy_currency(user, currency_code, amount)
    except CurrencyNotFoundError as e:
        return f"Ошибка: {str(e)}\nИспользуйте 'get-rate --help' для списка поддерживаемых валют."
    except ValidationError as e:
        return f"Ошибка валидации: {str(e)}"
    except ExchangeRateNotFoundError:
        # Курс недоступен, но покупка выполнена
        result = buy_currency(user, currency_code, amount)
        return (
            f"Покупка выполнена: {result['amount']:.4f} {result['currency']}\n"
            f"Изменения в портфеле:\n"
            f"- {result['currency']}: было {result['old_balance']:.4f} → стало {result['new_balance']:.4f}\n"
            f"Примечание: Курс обмена недоступен, оценочная стоимость не рассчитана."
        )

    # Успешная покупка
    output_parts = [
        f"✓ Покупка выполнена: {result['amount']:.4f} {result['currency']}",
        f" по курсу {result['rate']:.2f} USD/{result['currency']}"
        if result.get("rate")
        else "",
        "\nИзменения в портфеле:",
        f"\n- {result['currency']}: было {result['old_balance']:.4f} → стало {result['new_balance']:.4f}",
        f"\nОценочная стоимость покупки: {result['cost_usd']:,.2f} USD"
        if result.get("cost_usd")
        else "",
    ]

    return "".join(filter(None, output_parts))


@handle_errors
@require_login
def cmd_sell(args: argparse.Namespace) -> str:
    """
    Команда продажи валюты.

    Обрабатывает исключения:
    - ValidationError: некорректные данные
    - CurrencyNotFoundError: неизвестная валюта
    - WalletNotFoundError: кошелёк не найден
    - InsufficientFundsError: недостаточно средств
    - ExchangeRateNotFoundError: курс недоступен
    """
    user = get_current_user()
    if user is None:
        return "Сначала выполните login"

    currency_code = validate_currency(args.currency)
    amount = validate_amount_str(args.amount)

    try:
        result = sell_currency(user, currency_code, amount)
    except CurrencyNotFoundError as e:
        return f"Ошибка: {str(e)}\nИспользуйте 'get-rate --help' для списка поддерживаемых валют."
    except ValidationError as e:
        return f"Ошибка валидации: {str(e)}"
    except WalletNotFoundError as e:
        return f"Ошибка: {str(e)}"
    except InsufficientFundsError as e:
        # InsufficientFundsError уже содержит подробное сообщение
        return str(e)
    except ExchangeRateNotFoundError:
        # Курс недоступен, но продажа выполнена
        result = sell_currency(user, currency_code, amount)
        return (
            f"Продажа выполнена: {result['amount']:.4f} {result['currency']}\n"
            f"Изменения в портфеле:\n"
            f"- {result['currency']}: было {result['old_balance']:.4f} → стало {result['new_balance']:.4f}\n"
            f"Примечание: Курс обмена недоступен, оценочная выручка не рассчитана."
        )

    # Успешная продажа
    output_parts = [
        f"✓ Продажа выполнена: {result['amount']:.4f} {result['currency']}",
        f" по курсу {result['rate']:.2f} USD/{result['currency']}"
        if result.get("rate")
        else "",
        "\nИзменения в портфеле:",
        f"\n- {result['currency']}: было {result['old_balance']:.4f} → стало {result['new_balance']:.4f}",
        f"\nОценочная выручка: {result['revenue_usd']:,.2f} USD"
        if result.get("revenue_usd")
        else "",
    ]

    return "".join(filter(None, output_parts))


def _get_supported_currencies() -> str:
    """
    Получить список поддерживаемых валют.

    Returns:
        Строка со списком валют
    """
    from valutatrade_hub.core.currencies import get_currency

    # Попробуем получить несколько известных валют для примера
    known_currencies = ["USD", "EUR", "GBP", "RUB", "BTC", "ETH"]
    supported = []

    for code in known_currencies:
        try:
            currency = get_currency(code)
            supported.append(f"  {code} - {currency.name}")
        except CurrencyNotFoundError:
            pass

    if supported:
        return "\nПоддерживаемые валюты (примеры):\n" + "\n".join(supported)
    return "\nИспользуйте команду 'get-rate --help' для справки."


@handle_errors
def cmd_get_rate(args: argparse.Namespace) -> str:
    """
    Команда получения курса валюты.

    Обрабатывает исключения:
    - CurrencyNotFoundError: предлагает help или список валют
    - ApiRequestError: предлагает повторить позже / проверить сеть
    """
    from_currency = validate_currency(args.from_currency)
    to_currency = validate_currency(args.to_currency)

    try:
        rate, updated_at = get_exchange_rate(from_currency, to_currency)
    except CurrencyNotFoundError as e:
        # Предлагаем help или список валют
        error_msg = str(e)
        help_msg = "\nИспользуйте 'get-rate --help' для справки или проверьте список поддерживаемых валют."
        currencies_list = _get_supported_currencies()
        return f"{error_msg}{help_msg}{currencies_list}"
    except ApiRequestError as e:
        # Предлагаем повторить позже / проверить сеть
        error_msg = str(e)
        suggestion = (
            "\nПопробуйте повторить запрос позже или проверьте подключение к сети."
        )
        return f"{error_msg}{suggestion}"

    def format_output() -> str:
        yield f"Курс {from_currency}→{to_currency}: {rate:.8f}"

        if updated_at:
            try:
                dt = datetime.fromisoformat(updated_at)
                yield f" (обновлено: {dt.strftime('%Y-%m-%d %H:%M:%S')})"
            except (ValueError, AttributeError):
                pass

        if from_currency != to_currency:
            try:
                reverse_rate, _ = get_exchange_rate(to_currency, from_currency)
                yield f"\nОбратный курс {to_currency}→{from_currency}: {reverse_rate:.2f}"
            except (ValueError, CurrencyNotFoundError, ApiRequestError):
                pass

    return "".join(format_output())


@handle_errors
def cmd_update_rates(args: argparse.Namespace) -> str:
    """
    Команда обновления курсов валют.

    Обрабатывает исключения:
    - ApiRequestError: ошибки при обращении к внешнему API
    """
    from valutatrade_hub.core.exceptions import ApiRequestError
    from valutatrade_hub.parser_service.updater import RatesUpdater

    source = args.source.lower() if args.source else None

    if source and source not in ("coingecko", "exchangerate"):
        return f"Неизвестный источник: {source}. Используйте 'coingecko' или 'exchangerate'"

    try:
        updater = RatesUpdater()
        result = updater.run_update(source=source)

        if result["errors"]:
            error_msg = "\n".join(result["errors"])
            return (
                f"Update completed with errors. Check logs for details.\n"
                f"Errors: {error_msg}\n"
                f"Total rates updated: {result['updated']}"
            )

        return (
            f"Update successful. Total rates updated: {result['updated']}. "
            f"Last refresh: {result.get('last_refresh', 'N/A')}"
        )
    except ApiRequestError as e:
        return f"Ошибка при обновлении курсов: {str(e)}\nПопробуйте повторить позже."
    except Exception as e:
        return f"Ошибка: {str(e)}"


@handle_errors
def cmd_show_rates(args: argparse.Namespace) -> str:
    """
    Команда показа курсов валют из кеша.

    Обрабатывает исключения:
    - CurrencyNotFoundError: валюта не найдена в кеше
    """
    from datetime import datetime

    from valutatrade_hub.core.utils import load_rates

    rates = load_rates()

    if not rates or not isinstance(rates, dict):
        return "Локальный кеш курсов пуст. Выполните 'update-rates', чтобы загрузить данные."

    last_refresh = rates.get("last_refresh", "неизвестно")

    if "pairs" in rates:
        rate_pairs = rates["pairs"]
    else:
        rate_pairs = {
            k: v
            for k, v in rates.items()
            if k not in ("source", "last_refresh") and isinstance(v, dict)
        }

    if not rate_pairs:
        return "Локальный кеш курсов пуст. Выполните 'update-rates', чтобы загрузить данные."

    # Применяем фильтры
    result_lines = []

    # Фильтр по валюте
    if args.currency:
        currency = args.currency.upper()
        filtered_pairs = {k: v for k, v in rate_pairs.items() if currency in k}

        if not filtered_pairs:
            return f"Курс для '{currency}' не найден в кеше."

        rate_pairs = filtered_pairs

    # Фильтр --top (топ N самых дорогих)
    if args.top:
        try:
            top_n = int(args.top)
            # Сортируем по значению курса (по убыванию)
            sorted_pairs = sorted(
                rate_pairs.items(), key=lambda x: x[1].get("rate", 0), reverse=True
            )[:top_n]
            rate_pairs = dict(sorted_pairs)
        except ValueError:
            return f"Некорректное значение для --top: {args.top}"

    # Форматируем вывод
    try:
        if last_refresh != "неизвестно":
            dt = datetime.fromisoformat(last_refresh)
            refresh_str = dt.strftime("%Y-%m-%dT%H:%M:%S")
        else:
            refresh_str = last_refresh
    except (ValueError, TypeError):
        refresh_str = last_refresh

    result_lines.append(f"Rates from cache (updated at {refresh_str}):")

    # Сортируем по алфавиту для вывода
    sorted_items = sorted(rate_pairs.items())

    for pair_key, rate_data in sorted_items:
        if isinstance(rate_data, dict):
            rate = rate_data.get("rate", "N/A")
            source = rate_data.get("source", "")
            source_str = f" ({source})" if source else ""
            result_lines.append(f"- {pair_key}: {rate}{source_str}")

    return "\n".join(result_lines)


# Словарь команд с их обработчиками и парсерами
COMMAND_HANDLERS: dict[
    str, tuple[Callable, Callable[[argparse.ArgumentParser], None]]
] = {
    "register": (
        cmd_register,
        lambda p: (
            p.add_argument("--username", required=True),
            p.add_argument("--password", required=True),
        ),
    ),
    "login": (
        cmd_login,
        lambda p: (
            p.add_argument("--username", required=True),
            p.add_argument("--password", required=True),
        ),
    ),
    "show-portfolio": (
        cmd_show_portfolio,
        lambda p: p.add_argument("--base", default="USD"),
    ),
    "buy": (
        cmd_buy,
        lambda p: (
            p.add_argument("--currency", required=True),
            p.add_argument("--amount", required=True),
        ),
    ),
    "sell": (
        cmd_sell,
        lambda p: (
            p.add_argument("--currency", required=True),
            p.add_argument("--amount", required=True),
        ),
    ),
    "get-rate": (
        cmd_get_rate,
        lambda p: (
            p.add_argument("--from", dest="from_currency", required=True),
            p.add_argument("--to", required=True),
        ),
    ),
    "update-rates": (
        cmd_update_rates,
        lambda p: p.add_argument(
            "--source",
            default=None,
            help="Источник данных: 'coingecko' или 'exchangerate'",
        ),
    ),
    "show-rates": (
        cmd_show_rates,
        lambda p: (
            p.add_argument(
                "--currency",
                default=None,
                help="Показать курс только для указанной валюты",
            ),
            p.add_argument(
                "--top",
                default=None,
                type=int,
                help="Показать N самых дорогих криптовалют",
            ),
            p.add_argument(
                "--base",
                default=None,
                help="Показать курсы относительно указанной базы",
            ),
        ),
    ),
}


def parse_command(command_line: str) -> str:
    """
    Распарсить и выполнить команду.

    Args:
        command_line: Строка команды

    Returns:
        Результат выполнения команды
    """
    if not command_line.strip():
        return ""

    try:
        parts = shlex.split(command_line)
        if not parts:
            return ""

        command = parts[0]
        args = parts[1:]

        if command in ("exit", "quit"):
            return "Выход из программы"

        if command not in COMMAND_HANDLERS:
            return f"Неизвестная команда: {command}"

        handler, setup_parser = COMMAND_HANDLERS[command]
        parser = argparse.ArgumentParser(prog=command, exit_on_error=False)
        setup_parser(parser)
        parsed_args = parser.parse_args(args)
        return handler(parsed_args)

    except SystemExit:
        return "Ошибка в аргументах команды"
    except Exception as e:
        return f"Ошибка: {str(e)}"


def main_cli() -> None:
    """Главная функция CLI интерфейса."""
    print("Добро пожаловать в ValutaTrade Hub!")
    print("Введите команду или 'exit' для выхода")
    print()

    while True:
        try:
            command_line = input("> ").strip()
            if not command_line:
                continue

            if command_line in ("exit", "quit"):
                print("До свидания!")
                break

            result = parse_command(command_line)
            if result:
                print(result)
                print()

        except KeyboardInterrupt:
            print()
            print("До свидания!")
            break
        except EOFError:
            print()
            print("До свидания!")
            break
