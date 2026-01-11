"""Точка входа в проект."""

import logging

from valutatrade_hub.cli.interface import main_cli
from valutatrade_hub.logging_config import setup_logging


def main():
    """Главная функция для запуска проекта."""
    # Инициализация логирования
    setup_logging(log_level=logging.INFO)

    # Запуск CLI
    main_cli()


if __name__ == "__main__":
    main()
