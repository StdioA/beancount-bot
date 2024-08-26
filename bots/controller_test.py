import pytest
from datetime import datetime, date
from bean_utils import vec_query
from conf.conf_test import load_config_from_dict, clear_config
from bean_utils.bean import init_bean_manager
from bots import controller
from bean_utils.bean_test import assert_txs_equal, mock_embedding
from conf.config_data import Config


today = str(datetime.now().astimezone().date())


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    conf_data = {
        "embedding": {
            "enable": False,
            "db_store_folder": tmp_path,
        },
        "beancount": {
            "filename": "testdata/example.bean",
            "currency": "USD",
            "account_distinguation_range": [2, 3],
        }
    }
    config = load_config_from_dict(conf_data)
    manager = init_bean_manager()
    monkeypatch.setattr(controller, "bean_manager", manager)
    yield config
    clear_config()


def test_fetch_expense(mock_env):
    # Start and end is the same
    start, end = date(2023, 6, 29), date(2023, 6, 30)
    resp_table = controller.fetch_expense(start, end)
    assert resp_table.title == "Expenditures on 2023-06-29"
    assert resp_table.headers == ["Account", "Position"]
    assert resp_table.rows == [
        ["Expenses:Food", "31.59 USD"],
    ]
    
    # Start and end is different
    # Test level
    start, end = date(2023, 6, 1), date(2023, 7, 1)
    resp_table = controller.fetch_expense(start, end, root_level=1)
    assert resp_table.title == "Expenditures between 2023-06-01 - 2023-07-01"
    assert resp_table.headers == ["Account", "Position"]
    assert resp_table.rows == [
        ["Expenses", "7207.08 USD, 2400.00 IRAUSD"],
    ]


def test_fetch_bill(mock_env):
        # Start and end is the same
    start, end = date(2023, 6, 29), date(2023, 6, 30)
    resp_table = controller.fetch_bill(start, end)
    assert resp_table.title == "Account changes on 2023-06-29"
    assert resp_table.headers == ["Account", "Position"]
    assert resp_table.rows == [
        ["Expenses:Food", "31.59 USD"],
        ["Liabilities:US", "-31.59 USD"],
    ]
    
    # Start and end is different
    # Test level
    start, end = date(2023, 6, 1), date(2023, 7, 1)
    resp_table = controller.fetch_bill(start, end, root_level=1)
    assert resp_table.title == "Account changes between 2023-06-01 - 2023-07-01"
    assert resp_table.headers == ["Account", "Position"]
    assert resp_table.rows == [
        ['Assets', '3210.66768 USD, 10 VACHR, -2400.00 IRAUSD'],
        ['Expenses', '7207.08 USD, 2400.00 IRAUSD'],
        ['Income', '-10532.95 USD, -10 VACHR'],
        ['Liabilities', '115.20 USD']
    ]


def test_clone_txs(mock_env):
    # Normal generation
    param = """
    2023-05-23 * "Kin Soy" "Eating" #tag1 #tag2
        Assets:US:BofA:Checking  -23.40 USD
        Expenses:Food:Restaurant
    """
    exp_trx = f"""
    {today} * "Kin Soy" "Eating" #tag1 #tag2
        Assets:US:BofA:Checking  -23.40 USD
        Expenses:Food:Restaurant
    """
    response = controller.clone_txs(param)
    assert isinstance(response, controller.BaseMessage)
    assert_txs_equal(response.content, exp_trx)

    # Generate with error
    response = controller.clone_txs('')
    assert isinstance(response, controller.ErrorMessage)
    assert response.content == "No transaction found"


def test_render_txs(mock_env):
    # Normal generation
    responses = controller.render_txs('23.4 BofA:Checking "Kin Soy" Eating #tag1 #tag2')
    assert len(responses) == 1
    exp_trx = f"""
    {today} * "Kin Soy" "Eating" #tag1 #tag2
        Assets:US:BofA:Checking  -23.40 USD
        Expenses:Food:Restaurant
    """
    assert isinstance(responses[0], controller.BaseMessage)
    assert_txs_equal(responses[0].content, exp_trx)

    # Generate with error
    response = controller.render_txs('10.00 ICBC:Checking NotFound McDonalds "Big Mac"')
    assert isinstance(response, controller.ErrorMessage)
    assert response.content == 'ValueError: Account ICBC:Checking not found'


def test_build_db(monkeypatch, mock_env):
    # Build db without embedding enabled
    response = controller.build_db()
    assert isinstance(response, controller.BaseMessage)
    assert response.content == "Embedding is not enabled."

    # Build db with embedding enabled
    monkeypatch.setattr(mock_env, "embedding", Config.from_dict({
        "enable": True,
        "transaction_amount": 100,
        "candidates": 3,
        "output_amount": 2,
    }))
    monkeypatch.setattr(vec_query, "embedding", mock_embedding)
    response = controller.build_db()
    assert isinstance(response, controller.BaseMessage)
    assert response.content == f"Token usage: {mock_env.embedding.transaction_amount}"
