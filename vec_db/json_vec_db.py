import json
import logging
import numpy as np
from numpy.linalg import norm


DB_NAME = "tx_db.json"


def build_db(transactions):
    with open(DB_NAME, "w") as f:
        json.dump(transactions, f)


def query_by_embedding(embedding):
    try:
        with open("tx_db.json") as f:
            transactions = json.load(f)
    except FileExistsError:
        logging.warn("JSON vector database is not built")
        return
    embed_query = np.array(embedding)
    # Calculate cosine similarity
    max_similarity = -3
    matched_txs = None
    for txs in transactions:
        embed_tx = np.array(txs["embedding"])
        distance = np.dot(embed_tx, embed_query) / (norm(embed_tx) * norm(embed_query))
        if distance > max_similarity:
            max_similarity = distance
            matched_txs = txs

    return [matched_txs]
