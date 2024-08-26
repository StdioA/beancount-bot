import pytest
from vec_db.json_vec_db_test import easy_embedding, mock_config

try:
    import sqlite_vec
except ImportError:
    pytest.skip("skipping module tests due to sqlite_vec not installed", allow_module_level=True)
else:
    from vec_db import sqlite_vec_db


def test_sqlite_db(tmp_path, mock_config, monkeypatch):
    monkeypatch.setattr(sqlite_vec_db, "_db", None)
    # Build DB
    txs = [
        {
            "hash": "hash-1",
            "occurance": 1,
            "sentence": "sentence-1",
            "content": "content-1",
            "embedding": easy_embedding("content-1"),
        },
        {
            "hash": "hash-2",
            "occurance": 1,
            "sentence": "sentence-2",
            "content": "content-2",
            "embedding": easy_embedding("content-2"),
        },
        {
            "hash": "hash-3",
            "occurance": 1,
            "sentence": "sentence-3",
            "content": "another-3",
            "embedding": easy_embedding("another-3"),
        },
    ]
    # Query without db built
    candidates = sqlite_vec_db.query_by_embedding(
        easy_embedding("content-1"), "sentence-1", 2,
    )
    assert len(candidates) == 0
    # Query with empty table
    sqlite_vec_db.build_db([])
    candidates = sqlite_vec_db.query_by_embedding(
        easy_embedding("content-1"), "sentence-1", 2,
    )
    assert len(candidates) == 0
    # Build DB
    sqlite_vec_db.build_db(txs)
    db_path = sqlite_vec_db._get_db_name()
    assert db_path.exists()
    # Query DB
    candidates = sqlite_vec_db.query_by_embedding(
        easy_embedding("content-1"), "sentence-1", 2,
    )
    assert len(candidates) == 2
    assert candidates[0]["content"] == "content-1"
    assert candidates[1]["content"] == "content-2"
    # Cleanup
    db_path.unlink()
