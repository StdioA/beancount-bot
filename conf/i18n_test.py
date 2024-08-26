from conf.conf_test import load_config_from_dict
from conf.i18n import init_locale, gettext as _


def test_default_locale(monkeypatch):
    monkeypatch.setenv("LANG", "zh_CN.UTF-8")
    load_config_from_dict({})
    init_locale()
    assert _("Position") == "持仓"


def test_override_locale_with_config(monkeypatch):
    monkeypatch.setenv("LANG", "zh_CN.UTF-8")
    load_config_from_dict({
        "language": "fr_FR",
    })
    init_locale()
    assert _("Query account changes") == "Interroger les changements de compte"
