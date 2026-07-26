"""Configuración de logging estructurado para TrendScope."""

import sys
from pathlib import Path

from loguru import logger

from trendscope.settings import settings


def setup_logging():
    """Configura loguru con salida a consola y archivo rotativo."""
    # Remover handlers por defecto
    logger.remove()

    # Consola
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="INFO",
        colorize=True,
    )

    # Archivo
    data_dir = Path(settings.data_dir)
    data_dir.mkdir(parents=True, exist_ok=True)
    logger.add(
        data_dir / "trendscope.log",
        rotation="1 day",
        retention="7 days",
        level="DEBUG",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )


def get_logger(name: str):
    """Retorna un logger con contexto."""
    return logger.bind(name=name)
