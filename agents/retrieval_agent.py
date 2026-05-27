"""Retrieval agent: queries ChromaDB for relevant audit workpaper excerpts."""

import logging
import os

import chromadb

logger = logging.getLogger(__name__)

_CHROMA_PATH = "./chroma_db"
_COLLECTION_NAME = "audit_workpapers"

# Ordered longest-match-first to avoid substring collisions (e.g. "sql" inside "sql server")
_OS_KEYWORDS: list[tuple[str, str]] = [
    ("windows", "Windows"),
    ("linux", "Linux"),
]

_DB_KEYWORDS: list[tuple[str, str]] = [
    ("sql server", "SQL Server"),
    ("oracle", "Oracle"),
    ("sql", "SQL Server"),
]

_CONTROL_TYPE_KEYWORDS: list[tuple[str, str]] = [
    ("access management", "Access Management"),
    ("user access", "Access Management"),
    ("provisioning", "Access Management"),
    ("change management", "Change Management"),
    ("change control", "Change Management"),
    ("password", "Password Policy"),
]

_CONTROL_SUBTYPE_KEYWORDS: list[tuple[str, str]] = [
    ("privileged", "Privileged Access"),
    ("admin", "Privileged Access"),
    ("revocation", "Access Revocation"),
    ("termination", "Access Revocation"),
    ("offboarding", "Access Revocation"),
]


def _get_client() -> chromadb.PersistentClient:
    """Create the chroma_db directory if absent and return a persistent client."""
    os.makedirs(_CHROMA_PATH, exist_ok=True)
    return chromadb.PersistentClient(path=_CHROMA_PATH)


def _get_collection(client: chromadb.PersistentClient) -> chromadb.Collection:
    """Get or create the audit workpapers collection."""
    return client.get_or_create_collection(_COLLECTION_NAME)


def detect_metadata_filters(query: str) -> dict[str, str]:
    """Extract os, database, control_type, and control_subtype filters from a free-text query."""
    lower = query.lower()
    filters: dict[str, str] = {}

    for keyword, value in _OS_KEYWORDS:
        if keyword in lower:
            filters["os"] = value
            break

    for keyword, value in _DB_KEYWORDS:
        if keyword in lower:
            filters["database"] = value
            break

    for keyword, value in _CONTROL_TYPE_KEYWORDS:
        if keyword in lower:
            filters["control_type"] = value
            break

    for keyword, value in _CONTROL_SUBTYPE_KEYWORDS:
        if keyword in lower:
            filters["control_subtype"] = value
            break

    logger.info("Detected metadata filters: %s", filters)
    return filters


def build_where_clause(filters: dict[str, str]) -> dict | None:
    """Convert a flat filters dict to a ChromaDB $and where clause, or None if empty."""
    if not filters:
        return None
    if len(filters) == 1:
        key, val = next(iter(filters.items()))
        return {key: {"$eq": val}}
    return {"$and": [{k: {"$eq": v}} for k, v in filters.items()]}


def _query_collection(
    collection: chromadb.Collection,
    query: str,
    n_results: int,
    where: dict | None,
) -> dict:
    """Run a ChromaDB query, falling back to no where clause if the filter yields no matches."""
    kwargs: dict = {"query_texts": [query], "n_results": n_results}
    if where is not None:
        kwargs["where"] = where
    try:
        return collection.query(**kwargs)
    except Exception as exc:
        if where is None:
            raise
        logger.warning("Filtered query failed (%s) — retrying without where clause", exc)
        return collection.query(query_texts=[query], n_results=n_results)


def retrieve_documents(query: str, n_results: int = 6) -> list[dict]:
    """Query ChromaDB and return a list of {id, document, metadata, distance} dicts."""
    client = _get_client()
    collection = _get_collection(client)

    if collection.count() == 0:
        logger.info("Collection is empty — returning no documents")
        return []

    filters = detect_metadata_filters(query)
    where = build_where_clause(filters)
    effective_n = min(n_results, collection.count())

    logger.info("Querying collection with n_results=%d, where=%s", effective_n, where)
    results = _query_collection(collection, query, effective_n, where)

    ids = results.get("ids", [[]])[0]
    docs = results.get("documents", [[]])[0]
    metas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]

    records = [
        {"id": i, "document": d, "metadata": m, "distance": dist}
        for i, d, m, dist in zip(ids, docs, metas, distances)
    ]
    logger.info("Retrieved %d documents", len(records))
    return records
