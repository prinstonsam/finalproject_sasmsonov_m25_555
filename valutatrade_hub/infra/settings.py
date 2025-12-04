"""Singleton для загрузки конфигурации."""

from pathlib import Path
from typing import Any

# Попытка импорта tomllib (встроен в Python 3.11+)
_tomllib_available = False
try:
    import tomllib  # type: ignore

    _tomllib_available = True
except ImportError:
    # Fallback для Python < 3.11
    try:
        import tomli as tomllib  # type: ignore

        _tomllib_available = True
    except ImportError:
        tomllib = None  # type: ignore


class SettingsLoader:
    """
    Singleton для загрузки и хранения настроек приложения.
    
    Реализация Singleton через __new__:
    - Простота и читабельность: минимальный код, понятная логика
    - Прямой контроль над созданием экземпляра
    - Избегаем сложности метаклассов для простого случая
    - Гарантирует единственный экземпляр даже при множественных импортах
    """

    _instance: "SettingsLoader | None" = None
    _initialized: bool = False

    def __new__(cls) -> "SettingsLoader":
        """
        Создать единственный экземпляр SettingsLoader.
        
        Гарантирует, что в приложении существует ровно один экземпляр,
        даже при множественных вызовах SettingsLoader() или импортах.
        """
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Инициализация настроек (выполняется только один раз)."""
        if self._initialized:
            return

        # Базовые пути
        base_dir = Path(__file__).parent.parent.parent
        self._base_dir = base_dir
        self._data_dir = base_dir / "data"
        self._logs_dir = base_dir / "logs"

        # Пути к файлам данных
        self._users_file = self._data_dir / "users.json"
        self._portfolios_file = self._data_dir / "portfolios.json"
        self._rates_file = self._data_dir / "rates.json"

        # Настройки логирования
        self._log_level = "INFO"
        self._log_file = "valutatrade_hub.log"
        self._log_format = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        self._log_date_format = "%Y-%m-%d %H:%M:%S"
        self._log_max_bytes = 10 * 1024 * 1024  # 10 MB
        self._log_backup_count = 5

        # Настройки приложения
        self._default_base_currency = "USD"
        self._rates_ttl_seconds = 3600  # 1 час по умолчанию

        # Словарь для хранения всех настроек
        self._settings: dict[str, Any] = {}

        # Загружаем конфигурацию из pyproject.toml
        self._load_from_pyproject()

        # Применяем загруженные настройки
        self._apply_settings()

        self._initialized = True

    def _load_from_pyproject(self) -> None:
        """Загрузить конфигурацию из pyproject.toml."""
        pyproject_path = self._base_dir / "pyproject.toml"

        if not pyproject_path.exists():
            return

        if not _tomllib_available:
            # Если tomllib недоступен, используем значения по умолчанию
            return

        try:
            with open(pyproject_path, "rb") as f:
                pyproject_data = tomllib.load(f)  # type: ignore

            # Извлекаем секцию [tool.valutatrade]
            valutatrade_config = pyproject_data.get("tool", {}).get("valutatrade", {})
            self._settings.update(valutatrade_config)
        except (KeyError, ValueError, IOError):
            # Если ошибка при загрузке, используем значения по умолчанию
            pass

    def _apply_settings(self) -> None:
        """Применить загруженные настройки к атрибутам."""
        # Пути к данным
        if "data_dir" in self._settings:
            self._data_dir = Path(self._settings["data_dir"])
            self._users_file = self._data_dir / "users.json"
            self._portfolios_file = self._data_dir / "portfolios.json"
            self._rates_file = self._data_dir / "rates.json"

        if "logs_dir" in self._settings:
            self._logs_dir = Path(self._settings["logs_dir"])

        # Настройки логирования
        if "log_level" in self._settings:
            self._log_level = self._settings["log_level"]
        if "log_file" in self._settings:
            self._log_file = self._settings["log_file"]
        if "log_format" in self._settings:
            self._log_format = self._settings["log_format"]
        if "log_date_format" in self._settings:
            self._log_date_format = self._settings["log_date_format"]
        if "log_max_bytes" in self._settings:
            self._log_max_bytes = int(self._settings["log_max_bytes"])
        if "log_backup_count" in self._settings:
            self._log_backup_count = int(self._settings["log_backup_count"])

        # Настройки приложения
        if "default_base_currency" in self._settings:
            self._default_base_currency = self._settings["default_base_currency"]
        if "rates_ttl_seconds" in self._settings:
            self._rates_ttl_seconds = int(self._settings["rates_ttl_seconds"])

    def get(self, key: str, default: Any = None) -> Any:
        """
        Получить настройку по ключу.

        Args:
            key: Ключ настройки
            default: Значение по умолчанию, если ключ не найден

        Returns:
            Значение настройки или default

        Примеры ключей:
        - "data_dir" - путь к директории с данными
        - "rates_ttl_seconds" - TTL для курсов валют (в секундах)
        - "default_base_currency" - дефолтная базовая валюта
        - "log_level" - уровень логирования
        - "log_format" - формат логов
        """
        # Сначала проверяем специальные атрибуты
        attr_map = {
            "data_dir": self._data_dir,
            "logs_dir": self._logs_dir,
            "users_file": self._users_file,
            "portfolios_file": self._portfolios_file,
            "rates_file": self._rates_file,
            "log_level": self._log_level,
            "log_file": self._log_file,
            "log_format": self._log_format,
            "log_date_format": self._log_date_format,
            "log_max_bytes": self._log_max_bytes,
            "log_backup_count": self._log_backup_count,
            "default_base_currency": self._default_base_currency,
            "rates_ttl_seconds": self._rates_ttl_seconds,
        }

        if key in attr_map:
            return attr_map[key]

        # Затем проверяем словарь настроек
        return self._settings.get(key, default)

    def reload(self) -> None:
        """
        Перезагрузить конфигурацию из pyproject.toml.

        Полезно при изменении конфигурации во время выполнения.
        """
        # Сбрасываем настройки
        self._settings.clear()

        # Перезагружаем из pyproject.toml
        self._load_from_pyproject()

        # Применяем загруженные настройки
        self._apply_settings()

    # Properties для обратной совместимости
    @property
    def base_dir(self) -> Path:
        """Получить базовую директорию проекта."""
        return self._base_dir

    @property
    def data_dir(self) -> Path:
        """Получить директорию с данными."""
        return self._data_dir

    @property
    def logs_dir(self) -> Path:
        """Получить директорию с логами."""
        return self._logs_dir

    @property
    def users_file(self) -> Path:
        """Получить путь к файлу пользователей."""
        return self._users_file

    @property
    def portfolios_file(self) -> Path:
        """Получить путь к файлу портфелей."""
        return self._portfolios_file

    @property
    def rates_file(self) -> Path:
        """Получить путь к файлу курсов."""
        return self._rates_file

    @property
    def log_level(self) -> str:
        """Получить уровень логирования."""
        return self._log_level

    @property
    def log_file(self) -> str:
        """Получить имя файла лога."""
        return self._log_file

    @property
    def log_max_bytes(self) -> int:
        """Получить максимальный размер файла лога."""
        return self._log_max_bytes

    @property
    def log_backup_count(self) -> int:
        """Получить количество резервных файлов лога."""
        return self._log_backup_count

    @property
    def default_base_currency(self) -> str:
        """Получить дефолтную базовую валюту."""
        return self._default_base_currency

    @property
    def rates_ttl_seconds(self) -> int:
        """Получить TTL для курсов валют (в секундах)."""
        return self._rates_ttl_seconds


# Глобальный экземпляр для удобного доступа
# Гарантирует единственный экземпляр даже при множественных импортах
settings = SettingsLoader()
