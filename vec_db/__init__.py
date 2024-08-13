try:
    from .sqlite_vec_db import build_db, query_by_embedding
except ImportError:
    from .json_vec_db import build_db, query_by_embedding


__all__ = ["build_db", "query_by_embedding"]
