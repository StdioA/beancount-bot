import requests
from beancount.core.data import Transaction
from beancount.core.compare import hash_entry
import conf
from vec_db import build_db, query_by_embedding


_TIMEOUT = 30


def embedding(texts):
    config = conf.config.embedding
    payload = {
        "model": config.model,
        "input": texts,
        "encoding_format": "float",
    }
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "authorization": f"Bearer {config.api_key}",
    }
    response = requests.post(config.api_url, json=payload, headers=headers, timeout=_TIMEOUT)
    data = response.json()
    return data["data"], data["usage"]["total_tokens"]


def convert_account(account):
    """
    Convert an account string to a specific segment.

    Args:
        account (str): The account string to convert.

    Returns:
        str: The converted account string.

    This function takes an account string and converts it to a specific segment
    based on the configuration in conf.config.beancount.account_distinguation_range.
    If the account string does not contain any segment, the original account string
    is returned.
    """
    dist_range = conf.config.beancount.account_distinguation_range
    segments = account.split(":")
    if isinstance(dist_range, int):
        segments = segments[dist_range:dist_range+1]
    else:
        segments = segments[dist_range[0]:dist_range[1]+1]
    if not segments:
        return account
    return ":".join(segments)


def escape_quotes(s):
    if not s:
        return s
    return s.replace('"', '\\"')


def convert_to_natural_language(transaction) -> str:
    """
    Convert a transaction object to a string representation of natural language for input to RAG.

    Args:
        transactions (Transation): A Transaction object.

    Returns:
        str: The natural language representation of the transaction.

    The format of the representation is:
    `"{payee}" "{description}" "{account1} {account2} ..." [{#tag1} {#tag2} ...]`,
    where `{payee}` is the payee of the transaction, `{description}` is the narration,
    and `{account1} {account2} ...` is a space-separated list of accounts in the transaction.
    The accounts are converted to the most distinguable level as specified in the configuration.
    If the transaction has tags, they are appended to the end of the sentence.
    """
    payee = f'"{escape_quotes(transaction.payee)}"'
    description = f'"{escape_quotes(transaction.narration)}"'
    accounts = " ".join([convert_account(posting.account) for posting in transaction.postings])
    sentence = f"{payee} {description} {accounts}"
    if transaction.tags:
        tags = " ".join(["#" + tag for tag in transaction.tags])
        sentence += f" {tags}"
    return sentence


def build_tx_db(transactions):
    """
    Build a transaction database from the given transactions. This function
    consolidates the latest transactions and calculates their embeddings.
    The embeddings are stored in a database for future use.

    Args:
        transactions (list): A list of Transaction objects representing the
        transactions.

    Returns:
        int: The total number of tokens used for embedding.
    """
    _content_cache = {}
    def _read_lines(fname, start, end):
        if fname not in _content_cache:
            with open(fname) as f:
                _content_cache[fname] = f.readlines()
        return _content_cache[fname][start-1:end]

    unique_txs = {}
    amount = conf.config.embedding.transaction_amount
    # Build latest transactions
    for entry in reversed(transactions):
        if not isinstance(entry, Transaction):
            continue
        sentence = convert_to_natural_language(entry)
        if sentence is None:
            continue
        if sentence in unique_txs:
            unique_txs[sentence]["occurance"] += 1
            continue
        fname = entry.meta['filename']
        start_lineno = entry.meta['lineno']
        end_lineno = max(p.meta['lineno'] for p in entry.postings)
        unique_txs[sentence] = {
            "sentence": sentence,
            "hash": hash_entry(entry),
            "occurance": 1,
            "content": "".join(_read_lines(fname, start_lineno, end_lineno)),
        }
        if len(unique_txs) >= amount:
            break
    # Build embedding by group
    total_usage = 0
    unique_txs_list = list(unique_txs.values())

    for i in range(0, len(unique_txs_list), 32):
        sentence = [s['sentence'] for s in unique_txs_list[i:i+32]]
        embed, usage = embedding(sentence)
        for s, e in zip(unique_txs_list[i:i+32], embed):
            s["embedding"] = e["embedding"]
        total_usage += usage

    build_db(unique_txs_list)
    conf.logger.info("Total token usage: %d", total_usage)
    return total_usage


def query_txs(query):
    """
    Query transactions based on the given query string.

    Args:
        query (str): The query string to search for.

    Returns:
        list: A list of matched transactions. The length of the list is determined
            by the `output_amount` configuration.
    """
    candidates = conf.config.embedding.candidates or 3
    output_amount = conf.config.embedding.output_amount or 1
    match = query_by_embedding(embedding([query])[0][0]["embedding"], query, candidates)
    if match:
        return match[:output_amount]
    return []
