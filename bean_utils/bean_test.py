from datetime import datetime
import requests
import pytest
from conf import _load_config_from_dict
from conf.config_data import Config
from beancount.parser import parser
from bean_utils import bean, txs_query


today = str(datetime.now().astimezone().date())

class MockResponse:
    def __init__(self, data):
        self._data = data

    def json(self):
        return self._data


def mock_post(data):
    def _wrapped(*args, **kwargs):
        return MockResponse(data)
    return _wrapped


@pytest.fixture
def mock_config(tmp_path):
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
    config = _load_config_from_dict(conf_data)
    return config


def test_load(mock_config):
    manager = bean.BeanManager(mock_config.beancount.filename)
    assert manager is not None
    entries = manager.entries
    assert len(entries) > 0


def test_account_search(mock_config):
    manager = bean.BeanManager(mock_config.beancount.filename)
    accounts = manager.accounts
    assert len(accounts) > 0

    # Find account by full name
    exp_account = manager.find_account("Assets:US:BofA:Checking")
    assert exp_account == "Assets:US:BofA:Checking"
    # Find account by partial content
    exp_account = manager.find_account("ETrade:PnL")
    assert exp_account == "Income:US:ETrade:PnL"

    # Find account by payee
    # Select by missing unit
    exp_account = manager.find_account_by_payee("Chichipotle")
    assert exp_account == "Expenses:Food:Restaurant"
    # Select by account type
    exp_account = manager.find_account_by_payee("China Garden")
    assert exp_account == "Expenses:Food:Restaurant"


def assert_txs_equal(tx1_str, tx2_str):
    tx1 = parser.parse_string(tx1_str)[0][0]
    tx2 = parser.parse_string(tx2_str)[0][0]
    
    def clean_lineno(tx):
        tx.meta["lineno"] = 0
        for p in tx.postings:
            p.meta["lineno"] = 0
        return tx

    assert clean_lineno(tx1) == clean_lineno(tx2)


def test_build_txs(mock_config):
    manager = bean.BeanManager(mock_config.beancount.filename)

    # Test basic transaction
    args = ["10.00", "Assets:US:BofA:Checking", "Expenses:Food:Restaurant", "McDonalds", "Big Mac"]
    trx = manager.build_trx(args)
    assert trx != ""
    # Trick: The first \n is needed for further match on the line number
    exp_trx = f"""
    {today} * "McDonalds" "Big Mac"
        Assets:US:BofA:Checking  -10.00 USD
        Expenses:Food:Restaurant
    """
    assert_txs_equal(trx, exp_trx)

    # Test find account by payee
    args = ["23.4", "BofA:Checking", "Kin Soy", "Eating"]
    trx = manager.build_trx(args)
    assert trx != ""
    exp_trx = f"""
    {today} * "Kin Soy" "Eating"
        Assets:US:BofA:Checking  -23.40 USD
        Expenses:Food:Restaurant
    """
    assert_txs_equal(trx, exp_trx)

    # Test generate with tags
    args = ["23.4", "BofA:Checking", "Kin Soy", "Eating", "#tag1", "#tag2"]
    trx = manager.build_trx(args)
    assert trx != ""
    exp_trx = f"""
    {today} * "Kin Soy" "Eating" #tag1 #tag2
        Assets:US:BofA:Checking  -23.40 USD
        Expenses:Food:Restaurant
    """
    assert_txs_equal(trx, exp_trx)

    # Text account not found
    with pytest.raises(ValueError):
        manager.build_trx(["10.00", "ICBC:Checking", "NotFound", "McDonalds", "Big Mac"])
    with pytest.raises(ValueError):
        manager.build_trx(["10.00", "BofA:Checking", "McDonalds", "Big Mac"])


def test_generate_trx(mock_config):
    manager = bean.BeanManager(mock_config.beancount.filename)
    
    # Test basic generation
    args = '23.4 BofA:Checking "Kin Soy" Eating #tag1 #tag2'
    trxs = manager.generate_trx(args)
    assert len(trxs) == 1
    today = str(datetime.now().astimezone().date())
    exp_trx = f"""
    {today} * "Kin Soy" "Eating" #tag1 #tag2
        Assets:US:BofA:Checking  -23.40 USD
        Expenses:Food:Restaurant
    """
    assert_txs_equal(trxs[0], exp_trx)

    with pytest.raises(ValueError):
        manager.generate_trx("10.00 ICBC:Checking NotFound McDonalds 'Big Mac'")


def mock_embedding(texts):
    from vec_db.json_vec_db_test import easy_embedding
    return [{
        "embedding": easy_embedding(text)
    } for text in texts], len(texts)


def test_generate_trx_with_vector_db(mock_config, monkeypatch):
    # Test vector DB fallback
    monkeypatch.setattr(mock_config, "embedding", Config.from_dict({
        "enable": True,
        "transaction_amount": 100,
        "candidates": 3,
        "output_amount": 2,
    }))
    # monkeypatch.setattr(txs_query, "embedding", mock_embedding)
    def _mock_embedding_post(*args, json={}, **kwargs):
        result, tokens = mock_embedding(json["input"])
        return MockResponse({
            "data": result,
            "usage": {"total_tokens": tokens},
        })
    monkeypatch.setattr(requests, "post", _mock_embedding_post)

    manager = bean.BeanManager(mock_config.beancount.filename)
    txs_query.build_tx_db(manager.entries)
    trx = manager.generate_trx('10.00 "Kin Soy", "Eating"')
    # The match effect is not garanteed in this test due to incorrect embedding implementation
    assert len(trx) == 2
    exp = f"""
    {today} * "Verizon Wireless" ""
        Assets:US:BofA:Checking -10.00 USD
        Expenses:Home:Phone
    """
    assert_txs_equal(trx[0], exp)
    exp = f"""
    {today} * "Wine-Tarner Cable" ""
        Assets:US:BofA:Checking -10.00 USD
        Expenses:Home:Internet
    """
    assert_txs_equal(trx[1], exp)


def test_generate_trx_with_rag(mock_config, monkeypatch):
    exp_trx = f"""
    {today} * "Kin Soy" "Eating" #tag1 #tag2
        Assets:US:BofA:Checking  -23.40 USD
        Expenses:Food:Restaurant
    """
    monkeypatch.setattr(mock_config, "embedding", Config.from_dict({
        "enable": True,
        "transaction_amount": 100,
        "candidates": 3,
        "output_amount": 2,
    }))
    monkeypatch.setattr(mock_config, "rag", Config.from_dict({
        "enable": True,
    }))
    monkeypatch.setattr(txs_query, "embedding", mock_embedding)
    monkeypatch.setattr(requests, "post", mock_post({"message": {"content": exp_trx}}))

    # Test RAG fallback
    manager = bean.BeanManager(mock_config.beancount.filename)
    trx = manager.generate_trx('10.00 "Kin Soy", "Eating"')
    txs_query.build_tx_db(manager.entries)
    # The match effect is not garanteed in this test due to incorrect embedding implementation
    assert len(trx) == 1
    assert_txs_equal(trx[0], exp_trx)


def test_run_query(mock_config):
    manager = bean.BeanManager(mock_config.beancount.filename)
    result = manager.run_query('SELECT SUM(position) WHERE account="Assets:US:BofA:Checking"')
    assert result
    assert result[1][0].sum_position.to_string() == "(3076.17 USD)"


def test_clone_trx(mock_config):
    manager = bean.BeanManager(mock_config.beancount.filename)
    param = """
    2023-05-23 * "Kin Soy" "Eating" #tag1 #tag2
        Assets:US:BofA:Checking  -23.40 USD
        Expenses:Food:Restaurant
    """
    trx = manager.clone_trx(param)
    assert trx != ""
    exp_trx = f"""
    {today} * "Kin Soy" "Eating" #tag1 #tag2
        Assets:US:BofA:Checking  -23.40 USD
        Expenses:Food:Restaurant
    """
    assert_txs_equal(trx, exp_trx)


def test_parse_args():
    assert bean.parse_args("") == []
    assert bean.parse_args("  ") == []
    assert bean.parse_args("a b c") == ["a", "b", "c"]
    assert bean.parse_args("a 'b c' d") == ["a", "b c", "d"]
    assert bean.parse_args("a 'b\"' c") == ["a", "b\"", "c"]
    assert bean.parse_args("a 'b' c d") == ["a", "b", "c", "d"]
    assert bean.parse_args("a ”b“ c d") == ["a", "b", "c", "d"]
    assert bean.parse_args("a “b    ”   c   d") == ["a", "b    ", "c", "d"]

    with pytest.raises(ValueError):
        bean.parse_args("a 'b")

    with pytest.raises(ValueError):
        bean.parse_args("a 'b c")

    with pytest.raises(ValueError):
        bean.parse_args("a “b c'")
