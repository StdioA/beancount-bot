import logging
import requests
from beancount.loader import load_file
from beancount.core.data import Transaction
from beancount.core.compare import hash_entry
import conf

try:
    from vec_db import build_db, query_by_embedding
except ImportError:
    from json_vec_db import build_db, query_by_embedding


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
    response = requests.post(config.api_url, json=payload, headers=headers)
    data = response.json()
    return data["data"], data["usage"]["total_tokens"]


def convert_to_natural_language(transaction) -> str:
    def convert_account(account):
        segments = account.split(":")
        if len(segments) < 3:
            return segments[-1]
        return segments[2]

    # date = transaction.date.strftime('%Y-%m-%d')
    payee = transaction.payee or '""'
    description = transaction.narration or '""'
    accounts = " ".join([convert_account(posting.account) for posting in transaction.postings])
    return f"{payee} {description} {accounts}"


content_cache = {}


def read_lines(fname, start, end):
    global content_cache
    if fname not in content_cache:
        with open(fname) as f:
            lines = f.readlines()
        content_cache[fname] = lines
    return content_cache[fname][start-1:end]


def build_tx_db(transactions):
    sentences = []
    for entry in transactions:
        if not isinstance(entry, Transaction):
            continue

        try:
            sentence = convert_to_natural_language(entry)
            if sentence is None:
                continue
            fname = entry.meta['filename']
            start_lineno = entry.meta['lineno']
            end_lineno = max(p.meta['lineno'] for p in entry.postings)
            sentences.append({
                "sentence": sentence,
                "hash": hash_entry(entry),
                "content": "\n".join(read_lines(fname, start_lineno, end_lineno)),
            })
        except Exception:
            raise
    # Build embedding by group
    total_usage = 0
    for i in range(0, len(sentences), 32):
        sentence = [s['sentence'] for s in sentences[i:i+32]]
        embed, usage = embedding(sentence)
        for s, e in zip(sentences[i:i+32], embed):
            s["embedding"] = e["embedding"]
        total_usage += usage

    build_db(sentences)
    logging.info(f"Total token usage: {total_usage}")
    return total_usage


def query_txs(query):
    match = query_by_embedding(embedding([query])[0][0]["embedding"])
    if match:
        return match[0]


def build_db_from_file():
    file_path = "main.bean"
    entries, errors, options = load_file(file_path)
    transactions = [e for e in entries if isinstance(e, Transaction)][-1000:]
    build_tx_db(transactions)


if __name__ == "__main__":
    conf.load_config("config.yaml")
    build_db_from_file()
    # res = query_txs("羽毛球垫付")
    # del res["embedding"]
    # from pprint import pprint
    # pprint(res)
