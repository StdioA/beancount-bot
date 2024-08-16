import logging
from operator import itemgetter
import sqlite3
import sqlite_vec
from typing import List
import struct
from vec_db.match import calculate_score


def serialize_f32(vector: List[float]) -> bytes:
    """serializes a list of floats into a compact "raw bytes" format"""
    return struct.pack("%sf" % len(vector), *vector)


db = sqlite3.connect("tx_db.sqlite")
db.enable_load_extension(True)
sqlite_vec.load(db)
db.enable_load_extension(False)


def build_db(txs):
    embedding_dimention = 1
    if txs:
        embedding_dimention = len(txs[0]["embedding"])

    # Drop table
    db.execute("DROP TABLE vec_items")
    db.execute("DROP TABLE transactions")
    db.commit()
    db.execute("VACUUM")
    db.commit()
    # Create tables
    db.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_items USING vec0(embedding float[{embedding_dimention}])")
    db.execute("""
               CREATE TABLE IF NOT EXISTS transactions (
               id integer primary key,
               hash varchar(64) unique,
               occurance integer,
               sentence text,
               content text)""")

    for id_, tx in enumerate(txs, 1):
        db.execute("INSERT INTO vec_items (rowid, embedding) VALUES (?, ?)",
                   (id_, serialize_f32(tx["embedding"])))
        db.execute("INSERT INTO transactions (id, hash, occurance, sentence, content) VALUES (?, ?, ?, ?, ?)",
                   (id_, tx["hash"], tx["occurance"], tx["sentence"], tx["content"]))
    # flush db
    db.commit()


def query_by_embedding(embedding, sentence, candidate_amount):
    try:
        rows = db.execute(
            f"""
            SELECT
            rowid,
            vec_distance_cosine(embedding, ?) AS distance
            FROM vec_items
            ORDER BY distance LIMIT {candidate_amount}
            """,
            (serialize_f32(embedding),)).fetchall()
    except sqlite3.OperationalError as e:
        # Handle exception when vec_db is not built
        if "no such table" in e.args[0]:
            logging.warning("Sqlite vector database is not built")
            return []
        raise
    if not rows:
        return []

    ids = [x[0] for x in rows]
    # Select from transactions table
    placeholder = ",".join(["?"] * len(ids))
    row_names = ["id", "occurance", "sentence", "content"]
    rows_str = ", ".join(row_names)
    txs_rows = db.execute(f"SELECT {rows_str} FROM transactions WHERE id in ({placeholder})", ids).fetchall()
    txs_rows.sort(key=lambda x: ids.index(x[0]))
    # Merge result & distance
    candidates = []
    for drow, tx in zip(rows, txs_rows):
        tx_row = dict(zip(row_names, tx))
        tx_row["distance"] = drow[1]
        tx_row["score"] = calculate_score(tx_row, sentence)
        candidates.append(tx_row)

    candidates.sort(key=itemgetter("score"), reverse=True)
    # print(candidates)
    return candidates
