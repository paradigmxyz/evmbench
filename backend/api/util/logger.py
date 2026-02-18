import logging
import os
import sys

from loguru import logger as _logger
from uvicorn.config import LOGGING_CONFIG


class LoguruHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = _logger.level(record.levelname).name
        except ValueError:
            level = record.levelname

        frame, depth = logging.currentframe(), 6
        while frame.f_code.co_filename == logging.__file__:
            if frame.f_back is None:
                break

            frame = frame.f_back
            depth += 1

        _logger.opt(depth=depth, exception=record.exc_info).log(
            level,
            record.getMessage(),
        )


def _is_dev() -> bool:
    value = os.getenv('BACKEND_DEV', '').strip().lower()
    return value in {'1', 'true', 'yes', 'y', 'on'}


def _filter_min_level(record: dict) -> bool:
    current_level_name: str = 'DEBUG' if _is_dev() else 'INFO'
    current_level: int = _logger.level(current_level_name).no
    return record['level'].no >= current_level


def _filter_stderr(record: dict) -> bool:
    return _filter_min_level(record)


def _filter_stdout(record: dict) -> bool:
    record_no: int = record['level'].no
    error_no: int = _logger.level('ERROR').no
    return _filter_min_level(record) and record_no != error_no


def init_logger() -> None:
    loguru_handler = LoguruHandler()
    logging.basicConfig(handlers=[loguru_handler])

    for key in LOGGING_CONFIG['handlers']:
        handler_conf = LOGGING_CONFIG['handlers'][key]

        handler_conf['class'] = 'api.util.logger.LoguruHandler'
        if 'stream' in handler_conf:
            handler_conf.pop('stream')

    fmt = (
        '<level>{time}</level> | <level>{level: <8}</level> | '
        '<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - '
        '<level>{message}</level>'
    )

    _logger.remove()
    _logger.configure(
        handlers=[
            {'sink': sys.stderr, 'level': 'ERROR', 'format': fmt, 'filter': _filter_stderr},
            {'sink': sys.stdout, 'format': fmt, 'filter': _filter_stdout},
        ]  # type: ignore[invalid-argument-type]
    )


init_logger()
logger = _logger
