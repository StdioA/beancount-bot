from datetime import datetime
import shutil
from pathlib import Path
import requests
import pytest
from conf.conf_test import load_config_from_dict, clear_config
from beancount.parser import parser
from bean_utils import bean, vec_query


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
    config = load_config_from_dict(conf_data)
    yield config
    clear_config()


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
    if isinstance(tx1_str, str):
        tx1 = parser.parse_string(tx1_str)[0][0]
    else:
        tx1 = tx1_str
    if isinstance(tx2_str, str):
        tx2 = parser.parse_string(tx2_str)[0][0]
    else:
        tx2 = tx2_str
    
    def clean_meta(tx):
        keys = list(tx.meta.keys())
        for key in keys:
            del tx.meta[key]
        for p in tx.postings:
            keys = list(p.meta.keys())
            for key in keys:
                del p.meta[key]
        return tx

    assert clean_meta(tx1) == clean_meta(tx2)


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
    with pytest.raises(ValueError, match=r"Account .+ not found"):
        manager.build_trx(["10.00", "ICBC:Checking", "NotFound", "McDonalds", "Big Mac"])
    with pytest.raises(ValueError, match=r"Account .+ not found"):
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

    with pytest.raises(ValueError, match=r"Account .+ not found"):
        manager.generate_trx("10.00 ICBC:Checking NotFound McDonalds 'Big Mac'")


def mock_embedding(texts):
    from vec_db.json_vec_db_test import easy_embedding
    return [{
        "embedding": easy_embedding(text)
    } for text in texts], len(texts)


def test_generate_trx_with_vector_db(mock_config, monkeypatch):
    # Test vector DB fallback
    mock_config["embedding"] = {
        "enable": True,
        "transaction_amount": 100,
        "candidates": 3,
        "output_amount": 2,
    }
    def _mock_embedding_post(*args, json, **kwargs):
        result, tokens = mock_embedding(json["input"])
        return MockResponse({
            "data": result,
            "usage": {"total_tokens": tokens},
        })
    monkeypatch.setattr(requests, "post", _mock_embedding_post)

    manager = bean.BeanManager(mock_config.beancount.filename)
    vec_query.build_tx_db(manager.entries)
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
    mock_config.update({
        "embedding": {
            "enable": True,
            "transaction_amount": 100,
            "candidates": 3,
            "output_amount": 2,
        },
        "rag": {
            "enable": True
            }
        })
    monkeypatch.setattr(vec_query, "embedding", mock_embedding)
    monkeypatch.setattr(requests, "post", mock_post({"message": {"content": exp_trx}}))

    # Test RAG fallback
    manager = bean.BeanManager(mock_config.beancount.filename)
    trx = manager.generate_trx('10.00 "Kin Soy", "Eating"')
    vec_query.build_tx_db(manager.entries)
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

    with pytest.raises(ValueError, match=bean.ArgsError.args[0]):
        bean.parse_args("a 'b")

    with pytest.raises(ValueError, match=bean.ArgsError.args[0]):
        bean.parse_args("a 'b c")

    with pytest.raises(ValueError, match=bean.ArgsError.args[0]):
        bean.parse_args("a “b c'")


@pytest.fixture
def copied_bean(tmp_path):
    new_bean = tmp_path / "example.bean"
    shutil.copyfile("testdata/example.bean", new_bean)
    yield new_bean
    Path(new_bean).unlink()


def test_manager_reload(mock_config, copied_bean):
    manager = bean.BeanManager(copied_bean)
    account_amount = len(manager.accounts)
    entry_amount = len(manager.entries)
    assert len(manager.accounts) == 63
    assert len(manager.entries) == 2037

    # Append a "close" entry
    with open(copied_bean, "a") as f:
        f.write(f"{today} close Assets:US:BofA:Checking\n")
    
    # The account amount should reloaded
    assert len(manager.accounts) == account_amount - 1
    assert len(manager.entries) == entry_amount + 1


def test_manager_commmit(mock_config, copied_bean):
    manager = bean.BeanManager(copied_bean)
    assert len(manager.entries) == 2037
    txs = f"""
    {today} * "Test Payee" "Test Narration"
        Liabilities:US:Chase:Slate                       -12.30 USD
        Expenses:Food:Restaurant                          12.30 USD
    """
    manager.commit_trx(txs)
    assert len(manager.entries) == 2038
    assert_txs_equal(manager.entries[-1], txs)
