"""Shared Chroma client factory for local development and hosted persistence."""

import sys

try:
    import pysqlite3  # type: ignore

    sys.modules["sqlite3"] = pysqlite3
except ImportError:
    pass

import chromadb

import config


CHROMA_PATH = "./chroma_db"


def get_chroma_client():
    """Return Chroma Cloud when configured, otherwise local PersistentClient."""
    if config.USE_CHROMA_CLOUD:
        kwargs = {
            "tenant": config.CHROMA_TENANT,
            "database": config.CHROMA_DATABASE,
            "api_key": config.CHROMA_API_KEY,
        }
        if config.CHROMA_HOST:
            kwargs.update({"cloud_host": config.CHROMA_HOST, "cloud_port": 443})
        return chromadb.CloudClient(**kwargs)

    return chromadb.PersistentClient(path=CHROMA_PATH)
