import logging
import requests
from beancount.loader import load_file
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
    return s.replace('"', '\\"').replace("'", "\\'")


def convert_to_natural_language(transaction) -> str:
    # date = transaction.date.strftime('%Y-%m-%d')
    payee = f'"{escape_quotes(transaction.payee)}"'
    description = f'"{escape_quotes(transaction.narration)}"'
    accounts = " ".join([convert_account(posting.account) for posting in transaction.postings])
    sentence = f"{payee} {description} {accounts}"
    if transaction.tags:
        tags = " ".join(["#" + tag for tag in transaction.tags])
        sentence += f" {tags}"
    return sentence


content_cache = {}


def read_lines(fname, start, end):
    global content_cache
    if fname not in content_cache:
        with open(fname) as f:
            lines = f.readlines()
        content_cache[fname] = lines
    return content_cache[fname][start-1:end]


def build_tx_db(transactions):
    unique_txs = {}
    amount = conf.config.embedding.transaction_amount
    # Build latest transactions
    for entry in reversed(transactions):
        if not isinstance(entry, Transaction):
            continue
        try:
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
                "content": "".join(read_lines(fname, start_lineno, end_lineno)),
            }
            if len(unique_txs) >= amount:
                break
        except Exception:
            raise
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
    logging.info("Total token usage: %d", total_usage)
    return total_usage


def query_txs(query):
    candidates = conf.config.embedding.candidates or 3
    output_amount = conf.config.embedding.output_amount or 1
    match = query_by_embedding(embedding([query])[0][0]["embedding"], query, candidates)
    if match:
        return match[:output_amount]
    return []


def build_db_from_file():
    file_path = "main.bean"
    entries, errors, options = load_file(file_path)
    transactions = [e for e in entries if isinstance(e, Transaction)][-1000:]
    logging.debug("Tokens:", build_tx_db(transactions))
