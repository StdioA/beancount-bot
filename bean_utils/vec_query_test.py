import pytest
from bean_utils import vec_query
from conf.conf_test import load_config_from_dict, clear_config
from conf.config_data import Config
from beancount.parser import parser
from bean_utils.bean import parse_args


@pytest.fixture
def mock_config():
    conf_data = {
        "beancount": {
            "account_distinguation_range": [1, 2],
        },
    }
    config = load_config_from_dict(conf_data)
    yield config
    clear_config()


@pytest.mark.parametrize(
    ("account", "arg", "exp"),
    [
        ("Assets:BoFA:Checking", 1, "BoFA"),
        ("Assets:BoFA:Checking", [1, 1], "BoFA"),
        ("Assets:BoFA:Checking", [1, 2], "BoFA:Checking"),
        ("Assets:BoFA:Checking", [1, 5], "BoFA:Checking"),
    ],
)
def test_convert_account(account, arg, exp, mock_config, monkeypatch):
    mock_config["beancount"] = {
        "account_distinguation_range": arg,
    }
    assert vec_query.convert_account(account) == exp


def test_convert_to_natual_language(monkeypatch, mock_config):
    trx_str = """
    2022-01-01 * "Discount 'abc'" "Discount"
      Assets:US:BofA:Checking                         4264.93 USD
      Equity:Opening-Balances                        -4264.93 USD
    """
    mock_config["beancount"] = {
        "account_distinguation_range": [1, 2],
    }
    trx, _, _ = parser.parse_string(trx_str)

    result = vec_query.convert_to_natural_language(trx[0])
    assert result == '"Discount \'abc\'" "Discount" US:BofA Opening-Balances'
    args = parse_args(result)
    assert args == ["Discount 'abc'", "Discount", "US:BofA", "Opening-Balances"]
