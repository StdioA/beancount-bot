import json
import numpy


DB_NAME = "tx_db.json"


def build_db(transactions):
    with open(DB_NAME, "w") as f:
        json.dump(transactions, f)


def query_by_embedding(embedding):
    try:
        with open("tx_db.json") as f:
            transactions = json.load(f)
    except FileExistsError:
        return
    embed_query = numpy.array(embedding)
    # Calculate cosine similarity
    max_similarity = -3
    matched_txs = None
    for txs in transactions:
        # Calculate cosine similarity
        distance = numpy.dot(txs["embedding"], embed_query)
        if distance > max_similarity:
            max_similarity = distance
            matched_txs = txs

    return [matched_txs]
