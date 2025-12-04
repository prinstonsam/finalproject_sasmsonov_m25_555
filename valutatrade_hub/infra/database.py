"""Singleton для управления JSON-хранилищем."""

import json
from pathlib import Path
from typing import Any

from valutatrade_hub.infra.settings import settings


class DatabaseManager:
    """Singleton для управления JSON-хранилищем данных."""

    _instance: "DatabaseManager | None" = None
    _initialized: bool = False

    def __new__(cls) -> "DatabaseManager":
        """Создать единственный экземпляр DatabaseManager."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Инициализация менеджера базы данных (выполняется только один раз)."""
        if self._initialized:
            return

        self._users_file = settings.users_file
        self._portfolios_file = settings.portfolios_file
        self._rates_file = settings.rates_file

        # Создаём директории, если их нет
        settings.data_dir.mkdir(parents=True, exist_ok=True)

        self._initialized = True

    def _load_json(self, file_path: Path, default: Any = None) -> Any:
        """
        Загрузить данные из JSON файла.

        Args:
            file_path: Путь к файлу
            default: Значение по умолчанию, если файл не существует

        Returns:
            Загруженные данные или default
        """
        if not file_path.exists():
            return default if default is not None else ([] if "portfolio" in str(file_path) or "user" in str(file_path) else {})
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            from valutatrade_hub.core.exceptions import DatabaseError
            raise DatabaseError(f"Ошибка загрузки файла {file_path}: {str(e)}") from e

    def _save_json(self, file_path: Path, data: Any) -> None:
        """
        Сохранить данные в JSON файл.

        Args:
            file_path: Путь к файлу
            data: Данные для сохранения

        Raises:
            DatabaseError: Если не удалось сохранить файл
        """
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            from valutatrade_hub.core.exceptions import DatabaseError
            raise DatabaseError(f"Ошибка сохранения файла {file_path}: {str(e)}") from e

    def load_users(self) -> list[dict]:
        """
        Загрузить список пользователей.

        Returns:
            Список пользователей
        """
        return self._load_json(self._users_file, [])

    def save_users(self, users: list[dict]) -> None:
        """
        Сохранить список пользователей.

        Args:
            users: Список пользователей
        """
        self._save_json(self._users_file, users)

    def load_portfolios(self) -> list[dict]:
        """
        Загрузить список портфелей.

        Returns:
            Список портфелей
        """
        return self._load_json(self._portfolios_file, [])

    def save_portfolios(self, portfolios: list[dict]) -> None:
        """
        Сохранить список портфелей.

        Args:
            portfolios: Список портфелей
        """
        self._save_json(self._portfolios_file, portfolios)

    def load_rates(self) -> dict:
        """
        Загрузить курсы валют.

        Returns:
            Словарь с курсами валют
        """
        return self._load_json(self._rates_file, {})

    def save_rates(self, rates: dict) -> None:
        """
        Сохранить курсы валют.

        Args:
            rates: Словарь с курсами валют
        """
        self._save_json(self._rates_file, rates)


# Глобальный экземпляр для удобного доступа
database = DatabaseManager()

