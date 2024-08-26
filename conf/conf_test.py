import conf
from conf.config_data import Config


class MutableConfig(Config):
    def __setitem__(self, key, value):
        self._config[key] = value
    
    def update(self, *args, **kwargs):
        self._config.update(*args, **kwargs)

    @classmethod
    def from_dict(cls, dictionary):
        config = cls.__new__(cls)
        config._config = dictionary
        return config


def load_config_from_dict(config_dict):
    conf.config = MutableConfig.from_dict(config_dict)
    return conf.config


def clear_config():
    conf.config = None
