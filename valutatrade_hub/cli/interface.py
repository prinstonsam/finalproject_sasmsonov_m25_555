"""Команды."""

import argparse
import shlex
from datetime import datetime
from typing import Callable

from prettytable import PrettyTable

from valutatrade_hub.core.decorators import handle_errors, require_login
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

    base_currency = (args.base or "USD").upper()
    portfolio = get_user_portfolio(user.user_id)

    if not portfolio.wallets:
        return f"Портфель пользователя '{user.username}' пуст"

    # Создаём таблицу
    table = PrettyTable()
    table.field_names = ["Валюта", "Баланс", f"→ {base_currency}"]

    def calculate_wallet_value(wallet_data: tuple[str, Portfolio]) -> tuple[str, float, float]:
        """Генератор для расчёта стоимости кошелька."""
        currency_code, wallet = wallet_data
        balance = wallet.balance

        try:
            if currency_code == base_currency:
                value = balance
            else:
                rate, _ = get_exchange_rate(currency_code, base_currency, use_cache=True)
                value = balance * rate
            return currency_code, balance, value
        except ValueError:
            return currency_code, balance, None

    wallet_values = map(
        calculate_wallet_value,
        sorted(portfolio.wallets.items(), key=lambda x: x[0])
    )

    total_value = 0.0
    for currency_code, balance, value in wallet_values:
        if value is not None:
            total_value += value
            table.add_row([currency_code, f"{balance:.2f}", f"{value:.2f} {base_currency}"])
        else:
            table.add_row([currency_code, f"{balance:.2f}", "N/A"])

    result = f"Портфель пользователя '{user.username}' (база: {base_currency}):\n"
    result += table.get_string()
    result += f"\n---------------------------------\nИТОГО: {total_value:,.2f} {base_currency}"

    return result


@handle_errors
@require_login
def cmd_buy(args: argparse.Namespace) -> str:
    """Команда покупки валюты."""
    user = get_current_user()
    if user is None:
        return "Сначала выполните login"

    currency_code = validate_currency(args.currency)
    amount = validate_amount_str(args.amount)

    result = buy_currency(user, currency_code, amount)

    output_parts = [
        f"Покупка выполнена: {result['amount']:.4f} {result['currency']}",
        f" по курсу {result['rate']:.2f} USD/{result['currency']}" if result.get("rate") else "",
        "\nИзменения в портфеле:",
        f"\n- {result['currency']}: было {result['old_balance']:.4f} → стало {result['new_balance']:.4f}",
        f"\nОценочная стоимость покупки: {result['cost_usd']:,.2f} USD" if result.get("cost_usd") else "",
    ]

    return "".join(filter(None, output_parts))


@handle_errors
@require_login
def cmd_sell(args: argparse.Namespace) -> str:
    """Команда продажи валюты."""
    user = get_current_user()
    if user is None:
        return "Сначала выполните login"

    currency_code = validate_currency(args.currency)
    amount = validate_amount_str(args.amount)

    result = sell_currency(user, currency_code, amount)

    # Используем генератор для форматирования вывода
    output_parts = [
        f"Продажа выполнена: {result['amount']:.4f} {result['currency']}",
        f" по курсу {result['rate']:.2f} USD/{result['currency']}" if result.get("rate") else "",
        "\nИзменниния в портфеле:",
        f"\n- {result['currency']}: было {result['old_balance']:.4f} → стало {result['new_balance']:.4f}",
        f"\n Оценочная выручка: {result['revenue_usd']:,.2f} USD" if result.get("revenue_usd") else "",
    ]

    return "".join(filter(None, output_parts))


@handle_errors
def cmd_get_rate(args: argparse.Namespace) -> str:
    """Команда получения курса валюты."""
    from_currency = validate_currency(args.from_currency)
    to_currency = validate_currency(args.to_currency)

    rate, updated_at = get_exchange_rate(from_currency, to_currency)

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
            except ValueError:
                pass

    return "".join(format_output())


# Словарь команд с их обработчиками и парсерами
COMMAND_HANDLERS: dict[str, tuple[Callable, Callable[[argparse.ArgumentParser], None]]] = {
    "register": (
        cmd_register,
        lambda p: (p.add_argument("--username", required=True), p.add_argument("--password", required=True)),
    ),
    "login": (
        cmd_login,
        lambda p: (p.add_argument("--username", required=True), p.add_argument("--password", required=True)),
    ),
    "show-portfolio": (
        cmd_show_portfolio,
        lambda p: p.add_argument("--base", default="USD"),
    ),
    "buy": (
        cmd_buy,
        lambda p: (p.add_argument("--currency", required=True), p.add_argument("--amount", required=True)),
    ),
    "sell": (
        cmd_sell,
        lambda p: (p.add_argument("--currency", required=True), p.add_argument("--amount", required=True)),
    ),
    "get-rate": (
        cmd_get_rate,
        lambda p: (p.add_argument("--from", dest="from_currency", required=True), p.add_argument("--to", required=True)),
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
