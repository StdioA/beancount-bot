import pytest
import yaml
from conf.config_data import Config, ImmutableDict


@pytest.mark.parametrize(
    ("method", "args", "kwargs"),
    [
        ("__setitem__", ["key", "value"], {}),
        ("__delitem__", ["key"], {}),
        ("update", [["key", "value"]], {}),
        ("clear", [], {}),
        ("pop", ["key"], {}),
        ("popitem", [], {}),
        ("setdefault", ["key", "value"], {}),
    ],
)
def test_immutable_dict(method, args, kwargs):
    immutable_dict = ImmutableDict({"key": "value"})

    with pytest.raises(TypeError):
        getattr(immutable_dict, method)(*args, **kwargs)


def test_config(tmp_path):
    conf_data = {
        "embedding": {
            "enable": False,
        "db_store_folder": str(tmp_path),
        },
        "beancount": {
            "filename": "testdata/example.bean",
            "currency": "USD",
            "account_distinguation_range": [2, 3],
        }
    }
    config_path = tmp_path / "config.yaml"
    with open(config_path, 'w') as file:
        yaml.dump(conf_data, file)
    config =  Config(str(config_path))

    assert config
    assert config.embedding.enable is False
    assert config.beancount.filename == "testdata/example.bean"
    assert config.beancount.get("whatever") is None
