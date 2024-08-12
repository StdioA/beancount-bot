import sqlite3
import sqlite_vec
from typing import List
import struct


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
    # Create tables
    db.execute(f"CREATE VIRTUAL TABLE IF NOT EXISTS vec_items USING vec0(embedding float[{embedding_dimention}])")
    db.execute("""
               CREATE TABLE IF NOT EXISTS transactions (
               id integer primary key,
               hash varchar(64) unique,
               sentence text,
               content text)""")
    # truncate tables
    db.execute("DELETE FROM vec_items")
    db.execute("DELETE FROM transactions")
    db.commit()
    db.execute("VACUUM")
    db.commit()

    for id, tx in enumerate(txs, 1):
        db.execute("INSERT INTO vec_items (rowid, embedding) VALUES (?, ?)",
                   (id, serialize_f32(tx["embedding"])))
        db.execute("INSERT INTO transactions (id, hash, sentence, content) VALUES (?, ?, ?, ?)",
                   (id, tx["hash"], tx["sentence"], tx["content"]))
    # flush db
    db.commit()


def query_by_embedding(embedding):
    rows = db.execute(
        """
        SELECT
          rowid,
          vec_distance_cosine(embedding, ?) AS distance
        FROM vec_items
        ORDER BY distance LIMIT 3
        """,
        (serialize_f32(embedding),)).fetchall()
    if not rows:
        return []

    ids = [x[0] for x in rows]
    # Select from transactions table
    placeholder = ",".join(["?"] * len(ids))
    txs_rows = db.execute(f"SELECT id, sentence, content FROM transactions WHERE id in ({placeholder})", ids).fetchall()
    txs_rows.sort(key=lambda x: ids.index(x[0]))
    row_names = ["id", "sentence", "content"]
    txs_rows = [dict(zip(row_names, tx)) for tx in txs_rows]
    return txs_rows
