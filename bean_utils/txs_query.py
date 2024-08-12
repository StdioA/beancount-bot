import logging
import requests
from beancount.loader import load_file
from beancount.core.data import Transaction
from beancount.core.compare import hash_entry
import conf
from vec_db import build_db, query_by_embedding


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
    filtered_transactions = []
    amount = conf.config.embedding.transaction_amount
    sentences = set()
    # Build latest transactions
    for entry in reversed(transactions):
        if not isinstance(entry, Transaction):
            continue
        try:
            sentence = convert_to_natural_language(entry)
            if sentence is None or sentence in sentences:
                continue
            fname = entry.meta['filename']
            start_lineno = entry.meta['lineno']
            end_lineno = max(p.meta['lineno'] for p in entry.postings)
            filtered_transactions.append({
                "sentence": sentence,
                "hash": hash_entry(entry),
                "content": "\n".join(read_lines(fname, start_lineno, end_lineno)),
            })
            sentences.add(sentence)
            if len(sentences) >= amount:
                break
        except Exception:
            raise
    # Build embedding by group
    total_usage = 0
    for i in range(0, len(filtered_transactions), 32):
        sentence = [s['sentence'] for s in filtered_transactions[i:i+32]]
        embed, usage = embedding(sentence)
        for s, e in zip(filtered_transactions[i:i+32], embed):
            s["embedding"] = e["embedding"]
        total_usage += usage

    build_db(filtered_transactions)
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
    print("Tokens:", build_tx_db(transactions))


if __name__ == "__main__":
    conf.load_config("config.yaml")
    # build_db_from_file()

    queries = [
        "羽毛球垫付",
        "自行车",
        "自行车 美团",
        "Wechat Bicycle",
        "Char char bistro",
    ]
    for query in queries:
        res = query_txs(query)
        if "embedding" in res:
            del res["embedding"]
        from pprint import pprint
        pprint(res)
