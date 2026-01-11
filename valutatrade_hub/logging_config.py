"""Настройка логирования для проекта."""

import logging
import logging.handlers
from pathlib import Path

from valutatrade_hub.infra.settings import settings


def setup_logging(
    log_level: int = logging.INFO,
    log_dir: Path | None = None,
    log_file: str | None = None,
    max_bytes: int | None = None,
    backup_count: int | None = None,
) -> None:
    """
    Настроить логирование с ротацией файлов.

    Args:
        log_level: Уровень логирования (по умолчанию INFO)
        log_dir: Директория для логов (по умолчанию из settings)
        log_file: Имя файла лога (по умолчанию из settings)
        max_bytes: Максимальный размер файла перед ротацией (по умолчанию из settings)
        backup_count: Количество резервных файлов (по умолчанию из settings)
    """
    # Используем настройки из settings, если не указаны явно
    if log_dir is None:
        log_dir = settings.logs_dir
    else:
        log_dir = Path(log_dir)

    if log_file is None:
        log_file = settings.log_file
    if max_bytes is None:
        max_bytes = settings.log_max_bytes
    if backup_count is None:
        backup_count = settings.log_backup_count

    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / log_file

    # Формат логов (человекочитаемый)
    log_format_str = settings.get(
        "log_format", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    log_date_format = settings.get("log_date_format", "%Y-%m-%d %H:%M:%S")

    log_format = logging.Formatter(
        fmt=log_format_str,
        datefmt=log_date_format,
    )

    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    # Удаляем существующие обработчики
    root_logger.handlers.clear()

    # Обработчик для консоли
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_handler.setFormatter(log_format)
    root_logger.addHandler(console_handler)

    # Обработчик для файла с ротацией
    file_handler = logging.handlers.RotatingFileHandler(
        log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    file_handler.setLevel(log_level)
    file_handler.setFormatter(log_format)
    root_logger.addHandler(file_handler)

    # Настраиваем отдельный логгер для действий (actions.log)
    _setup_action_logger(log_dir, max_bytes, backup_count, log_level)


def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер с указанным именем.

    Args:
        name: Имя логгера (обычно __name__ модуля)

    Returns:
        Настроенный логгер
    """
    return logging.getLogger(name)


def _setup_action_logger(
    log_dir: Path,
    max_bytes: int,
    backup_count: int,
    log_level: int,
) -> None:
    """
    Настроить отдельный логгер для действий (actions.log).

    Args:
        log_dir: Директория для логов
        max_bytes: Максимальный размер файла перед ротацией
        backup_count: Количество резервных файлов
        log_level: Уровень логирования
    """
    action_log_path = log_dir / "actions.log"

    # Формат для действий: LEVEL timestamp message
    # Пример: INFO 2025-10-09T12:05:22 action=BUY user='alice' currency='BTC' amount=0.0500 rate=59300.00 base='USD' result=OK
    action_format = logging.Formatter(
        fmt="%(levelname)s %(asctime)s %(message)s",
        datefmt="%Y-%m-%dT%H:%M:%S",
    )

    # Создаём отдельный логгер для действий
    action_logger = logging.getLogger("valutatrade_hub.actions")
    action_logger.setLevel(log_level)
    action_logger.propagate = False  # Не пропускаем в корневой логгер

    # Обработчик для файла действий с ротацией
    action_file_handler = logging.handlers.RotatingFileHandler(
        action_log_path,
        maxBytes=max_bytes,
        backupCount=backup_count,
        encoding="utf-8",
    )
    action_file_handler.setLevel(log_level)
    action_file_handler.setFormatter(action_format)
    action_logger.addHandler(action_file_handler)


def get_action_logger() -> logging.Logger:
    """
    Получить логгер для действий (actions.log).

    Returns:
        Логгер для действий
    """
    # Убеждаемся, что action logger настроен
    action_logger = logging.getLogger("valutatrade_hub.actions")

    # Если обработчики еще не настроены, настраиваем их
    if not action_logger.handlers:
        log_dir = settings.logs_dir
        max_bytes = settings.log_max_bytes
        backup_count = settings.log_backup_count
        log_level = logging.getLevelName(settings.log_level)
        if isinstance(log_level, str):
            log_level = logging.INFO
        _setup_action_logger(log_dir, max_bytes, backup_count, log_level)

    return action_logger
