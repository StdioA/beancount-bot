import os
import yaml


_ImmutableError = TypeError("This dictionary is immutable")


class ImmutableDict(dict):
    def __setitem__(self, key, value):
        raise _ImmutableError

    def __delitem__(self, key):
        raise _ImmutableError

    def update(self, *args, **kwargs):
        raise _ImmutableError

    def clear(self):
        raise _ImmutableError

    def pop(self, *args):
        raise _ImmutableError

    def popitem(self):
        raise _ImmutableError

    def setdefault(self, *args):
        raise _ImmutableError


class Config:
    def __init__(self, config_path):
        with open(config_path, 'r') as file:
            self._config = ImmutableDict(yaml.safe_load(file))

    def __bool__(self):
        return bool(self._config)

    def get(self, key, default=None):
        return self._config.get(key, default)

    def __getattr__(self, key):
        if key in self._config:
            value = self._config[key]
            if isinstance(value, dict):
                return Config.from_dict(value)
            return value
        # raise AttributeError(f"Config has no attribute '{key}'")
        return Config.from_dict({})

    @classmethod
    def from_dict(cls, dictionary):
        config = cls.__new__(cls)
        config._config = ImmutableDict(dictionary)  # noqa: SLF001
        return config


config = None


def load_config(config_path):
    global config
    config = Config(config_path)


def set_locale():
    if config.get("language") is not None:
        # Only in this way can I override default language for gettext.gettext
        os.environ['LANGUAGE'] = config.get("language")
        # `install` also works, but it's not recommended after python 3.8, and it will cause lint error
        # gettext.translation("beanbot", config.get("language"), fallback=True).install()
        # Otherwise, I can write my own `_` function, which can take from `some_translation.gettext`
