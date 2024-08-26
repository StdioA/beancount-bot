from .i18n import init_locale
from .config_data import Config


__all__ = ['config', 'init_locale', "load_config"]


config = None


def load_config(config_path):
    global config
    config = Config(config_path)
