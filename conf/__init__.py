import logging
import logging.config
from .i18n import init_locale
from .config_data import Config
from .utils import merge_dicts


__all__ = ['config', 'init_locale', "load_config", "logger", "init_logging"]

config = None

_logger_name = "beanbot"
logger = logging.getLogger(_logger_name)


def load_config(config_path):
    global config
    config = Config(config_path)


_default_logging_config = {
    "version": 1,
    "formatters": {
        "standard": {
            "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        }
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "WARNING",
            "formatter": "standard",
            "stream": "ext://sys.stdout"
        }
    },
    "loggers": {
        _logger_name: {
            "level": "WARNING",
            "handlers": ["console"],
            "propagate": False,
        }
    }
}


def init_logging():
    logging_conf = merge_dicts(_default_logging_config, config.get("logging", {}))
    logging.config.dictConfig(logging_conf)
