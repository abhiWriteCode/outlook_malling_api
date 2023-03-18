import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import datetime
import ecs_logging


LOG_DIR = '/logs'
POD_NAME = os.environ['POD_NAME']
LOG_FILE_PATH = os.path.join(LOG_DIR, POD_NAME)
ERROR_FILE_NAME = f"{LOG_FILE_PATH}-{datetime.date.today()}.applog"

if not os.path.exists(LOG_DIR):
    os.mkdir(LOG_DIR)


def get_file_handler():
    file_handler = RotatingFileHandler(filename=ERROR_FILE_NAME, mode='a', encoding='utf-8')
    file_handler.setLevel(level=logging.DEBUG)  # less severe than DEBUG will be ignored
    file_log_format = ecs_logging.StdlibFormatter(exclude_fields=["log.logger", "log.original", "process"])
    file_handler.setFormatter(fmt=file_log_format)
    return file_handler


def get_console_handler():
    console_handler = logging.StreamHandler(stream=sys.stdout)
    console_handler.setLevel(level=logging.DEBUG)  # less severe than DEBUG will be ignored
    console_log_format = "%(asctime)s - [%(levelname)s] - {%(filename)s-%(funcName)s : %(lineno)d} - %(message)s"
    console_handler.setFormatter(fmt=logging.Formatter(fmt=console_log_format))
    return console_handler


def get_logger(name):
    logger = logging.getLogger(name)
    logger = set_logger_level(logger)
    logger.addHandler(get_file_handler())
    logger.addHandler(get_console_handler())
    return logger


def set_logger_level(logger):
    level = logging.DEBUG
    logger.setLevel(level=level)
    return logger


class Logger(object):
    r"""
    Singleton Logger

    Example
    --------
    >>> from app_logger import Logger
    >>> logger = Logger.get_singleton_logger()
    >>> try:
    ...     logger.debug('Debugging')
    ...     logger.info('Information')
    ...     logger.error('Error')
    ... except Exception as e:
    ...     logger.exception(e)
    """
    __instance = None

    def __init__(self):
        if Logger.__instance is not None:
            raise Exception("This class is a singleton! To get instance call Logger.get_singleton_logger()")
        else:
            self.logger = get_logger(__name__)
            Logger.__instance = self

    @staticmethod
    def get_singleton_logger():
        if Logger.__instance is None:
            Logger()

        return Logger.__instance.logger

    @staticmethod
    def update_logger_level():
        logger = Logger.get_singleton_logger()
        logger = set_logger_level(logger)
        Logger.__instance.logger = logger
