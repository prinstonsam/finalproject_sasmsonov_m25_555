"""Реализация классов."""

import hashlib
import secrets
from datetime import datetime


class User:
    """Класс пользователя системы."""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ):
        """
        Инициализация пользователя.

        Args:
            user_id: Уникальный идентификатор пользователя
            username: Имя пользователя
            hashed_password: Пароль в зашифрованном виде
            salt: Уникальная соль для пользователя
            registration_date: Дата регистрации пользователя
        """
        self._user_id = user_id
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        """Получить идентификатор пользователя."""
        return self._user_id

    @property
    def username(self) -> str:
        """Получить имя пользователя."""
        return self._username

    @username.setter
    def username(self, value: str) -> None:
        """
        Установить имя пользователя.

        Args:
            value: Имя пользователя

        Raises:
            ValueError: Если имя пустое
        """
        if not value or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")
        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        """Получить хешированный пароль."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Получить соль."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Получить дату регистрации."""
        return self._registration_date

    def get_user_info(self) -> dict:
        """
        Получить информацию о пользователе (без пароля).

        Returns:
            Словарь с информацией о пользователе
        """
        return {
            "user_id": self._user_id,
            "username": self._username,
            "registration_date": self._registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """
        Изменить пароль пользователя с хешированием.

        Args:
            new_password: Новый пароль

        Raises:
            ValueError: Если пароль короче 4 символов
        """
        if len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        # Генерируем новую соль
        self._salt = secrets.token_hex(8)
        # Хешируем пароль с солью
        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode()
        ).hexdigest()

    def verify_password(self, password: str) -> bool:
        """
        Проверить введённый пароль на совпадение.

        Args:
            password: Пароль для проверки

        Returns:
            True если пароль совпадает, False иначе
        """
        hashed_input = hashlib.sha256((password + self._salt).encode()).hexdigest()
        return hashed_input == self._hashed_password

    def to_dict(self) -> dict:
        """
        Преобразовать пользователя в словарь для сохранения в JSON.

        Returns:
            Словарь с данными пользователя
        """
        return {
            "user_id": self._user_id,
            "username": self._username,
            "hashed_password": self._hashed_password,
            "salt": self._salt,
            "registration_date": self._registration_date.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        """
        Создать пользователя из словаря (из JSON).

        Args:
            data: Словарь с данными пользователя

        Returns:
            Экземпляр класса User
        """
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            hashed_password=data["hashed_password"],
            salt=data["salt"],
            registration_date=datetime.fromisoformat(data["registration_date"]),
        )


class Wallet:
    """Класс кошелька пользователя для одной конкретной валюты."""

    def __init__(self, currency_code: str, balance: float = 0.0):
        """
        Инициализация кошелька.

        Args:
            currency_code: Код валюты (например, "USD", "BTC")
            balance: Баланс в данной валюте (по умолчанию 0.0)
        """
        self.currency_code = currency_code
        self.balance = balance

    @property
    def balance(self) -> float:
        """
        Получить текущий баланс.

        Returns:
            Текущий баланс
        """
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """
        Установить баланс.

        Args:
            value: Новое значение баланса

        Raises:
            TypeError: Если передан некорректный тип данных
            ValueError: Если баланс отрицательный
        """
        if not isinstance(value, (int, float)):
            raise TypeError("Баланс должен быть числом")
        value = float(value)
        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")
        self._balance = value

    def deposit(self, amount: float) -> None:
        """
        Пополнить баланс.

        Args:
            amount: Сумма пополнения

        Raises:
            ValueError: Если сумма не положительная
        """
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма должна быть числом")
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительным числом")
        self._balance += amount

    def withdraw(self, amount: float) -> None:
        """
        Снять средства с баланса.

        Args:
            amount: Сумма снятия

        Raises:
            ValueError: Если сумма не положительная или превышает баланс
        """
        if not isinstance(amount, (int, float)):
            raise TypeError("Сумма должна быть числом")
        amount = float(amount)
        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительным числом")
        if amount > self._balance:
            raise ValueError("Недостаточно средств на балансе")
        self._balance -= amount

    def get_balance_info(self) -> dict:
        """
        Получить информацию о текущем балансе.

        Returns:
            Словарь с информацией о балансе
        """
        return {
            "currency_code": self.currency_code,
            "balance": self._balance,
        }

    def to_dict(self) -> dict:
        """
        Преобразовать кошелёк в словарь для сохранения в JSON.

        Returns:
            Словарь с данными кошелька
        """
        return {
            "currency_code": self.currency_code,
            "balance": self._balance,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Wallet":
        """
        Создать кошелёк из словаря (из JSON).

        Args:
            data: Словарь с данными кошелька

        Returns:
            Экземпляр класса Wallet
        """
        return cls(
            currency_code=data["currency_code"],
            balance=data["balance"],
        )


class Portfolio:
    """Класс управления всеми кошельками одного пользователя."""

    # Фиксированные курсы валют к USD (для упрощения)
    EXCHANGE_RATES = {
        "USD": 1.0,
        "EUR": 1.1,
        "BTC": 45000.0,
        "RUB": 0.011,
        "GBP": 1.27,
    }

    def __init__(self, user_id: int, wallets: dict[str, Wallet] | None = None, user: "User" | None = None):
        """
        Инициализация портфеля.

        Args:
            user_id: Уникальный идентификатор пользователя
            wallets: Словарь кошельков (ключ - код валюты, значение - Wallet)
            user: Объект пользователя (опционально)
        """
        self._user_id = user_id
        self._wallets: dict[str, Wallet] = wallets if wallets is not None else {}
        self._user = user

    @property
    def user_id(self) -> int:
        """Получить идентификатор пользователя."""
        return self._user_id

    @property
    def user(self) -> "User" | None:
        """
        Получить объект пользователя.

        Returns:
            Объект пользователя или None, если не установлен
        """
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """
        Получить копию словаря кошельков.

        Returns:
            Копия словаря кошельков
        """
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """
        Добавить новый кошелёк в портфель.

        Args:
            currency_code: Код валюты

        Returns:
            Созданный объект Wallet

        Raises:
            ValueError: Если кошелёк с таким кодом валюты уже существует
        """
        currency_code = currency_code.upper()
        if currency_code in self._wallets:
            raise ValueError(f"Кошелёк с валютой {currency_code} уже существует")
        wallet = Wallet(currency_code=currency_code, balance=0.0)
        self._wallets[currency_code] = wallet
        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        """
        Получить кошелёк по коду валюты.

        Args:
            currency_code: Код валюты

        Returns:
            Объект Wallet или None, если кошелёк не найден
        """
        currency_code = currency_code.upper()
        return self._wallets.get(currency_code)

    def get_total_value(self, base_currency: str = "USD") -> float:
        """
        Получить общую стоимость всех валют в базовой валюте.

        Args:
            base_currency: Базовая валюта для конвертации (по умолчанию USD)

        Returns:
            Общая стоимость в базовой валюте

        Raises:
            ValueError: Если курс для валюты не найден
        """
        base_currency = base_currency.upper()
        if base_currency not in self.EXCHANGE_RATES:
            raise ValueError(f"Курс для валюты {base_currency} не найден")

        total_value = 0.0
        base_rate = self.EXCHANGE_RATES[base_currency]

        for wallet in self._wallets.values():
            currency_code = wallet.currency_code
            if currency_code not in self.EXCHANGE_RATES:
                raise ValueError(f"Курс для валюты {currency_code} не найден")

            # Конвертируем баланс в базовую валюту
            currency_rate = self.EXCHANGE_RATES[currency_code]
            # Сначала конвертируем в USD, затем в базовую валюту
            usd_value = wallet.balance * currency_rate
            base_value = usd_value / base_rate
            total_value += base_value

        return total_value

    def to_dict(self) -> dict:
        """
        Преобразовать портфель в словарь для сохранения в JSON.

        Returns:
            Словарь с данными портфеля
        """
        wallets_dict = {}
        for currency_code, wallet in self._wallets.items():
            # В JSON храним только balance, currency_code уже в ключе
            wallets_dict[currency_code] = {"balance": wallet.balance}
        return {
            "user_id": self._user_id,
            "wallets": wallets_dict,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Portfolio":
        """
        Создать портфель из словаря (из JSON).

        Args:
            data: Словарь с данными портфеля

        Returns:
            Экземпляр класса Portfolio
        """
        wallets = {}
        for currency_code, wallet_data in data["wallets"].items():
            # В JSON currency_code в ключе, balance в значении
            balance = wallet_data.get("balance", 0.0)
            wallets[currency_code] = Wallet(currency_code=currency_code, balance=balance)
        return cls(user_id=data["user_id"], wallets=wallets)
