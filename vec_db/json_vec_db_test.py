import pytest
from typing import List
from conf import _load_config_from_dict, config
import tempfile
from vec_db import json_vec_db


@pytest.fixture
def mock_config():
    conf_data = {
        "embedding": {
            "enable": True,
            "db_store_folder": tempfile.gettempdir(),
        }
    }
    _load_config_from_dict(conf_data)
    return config


def easy_embedding(content: str) -> List[float]:
    embed = [float(x) for x in content.encode()]
    # right pad with zeros
    _width = 64
    for _ in range(_width - len(embed)):
        embed.append(0.0)
    return embed


def test_json_db(mock_config):
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
    json_vec_db.build_db(txs)
    db_path = json_vec_db._get_db_name()
    assert db_path.exists()
    # Query DB
    candidates = json_vec_db.query_by_embedding(
        easy_embedding("content-1"), "sentence-1", 2,
    )
    assert len(candidates) == 2
    assert candidates[0]["hash"] == "hash-1"
    assert candidates[1]["hash"] == "hash-2"
    # Cleanup
    db_path.unlink()
