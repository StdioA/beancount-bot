import pathlib
import json
import logging
from operator import itemgetter
import numpy as np
from numpy.linalg import norm
from vec_db.match import calculate_score
import conf


def _get_db_name():
    DB_NAME = "tx_db.json"
    db_dir = conf.config.embedding.get("db_store_folder", ".")
    return pathlib.Path(db_dir) / DB_NAME


def build_db(transactions):
    with open(_get_db_name(), "w") as f:
        json.dump(transactions, f)


def query_by_embedding(embedding, sentence, candidate_amount):
    try:
        with open(_get_db_name()) as f:
            transactions = json.load(f)
    except FileExistsError:
        logging.warning("JSON vector database is not built")
        return None
    embed_query = np.array(embedding)
    # Calculate cosine similarity
    for txs in transactions:
        embed_tx = np.array(txs["embedding"])
        txs["distance"] = np.dot(embed_tx, embed_query) / (norm(embed_tx) * norm(embed_query))
        txs["score"] = calculate_score(txs, sentence)
    transactions.sort(key=itemgetter("distance"), reverse=True)
    candidates = transactions[:candidate_amount]
    candidates.sort(key=lambda x: x["distance"], reverse=True)
    return candidates
