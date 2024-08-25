import pytest
import os
from conf import _load_config_from_dict
from conf.i18n import init_locale, gettext as _


@pytest.fixture
def override_env():
    backup = os.environ.get("LANG")
    os.environ["LANG"] = "zh_CN.UTF-8"
    yield
    if backup is None:
        del os.environ["LANG"]
    else:
        os.environ["LANG"] = backup


def test_default_locale(override_env):
    _load_config_from_dict({})
    init_locale()
    assert _("Position") == "持仓"


def test_override_locale_with_config(override_env):
    _load_config_from_dict({
        "language": "fr_FR",
    })
    init_locale()
    assert _("Query account changes") == "Interroger les changements de compte"
