"""Supervisor agent: validates input and routes to the reasoning agent."""

import logging

from agents import reasoning_agent

logger = logging.getLogger(__name__)

_MIN_QUERY_LENGTH = 10
_SHORT_QUERY_ERROR = "Query too short. Please describe the control being tested."


def handle_query(query: str) -> dict:
    """Validate query then delegate to reasoning_agent; return error dict if invalid."""
    logger.info("Supervisor received query (length=%d)", len(query) if isinstance(query, str) else -1)

    if not isinstance(query, str) or len(query.strip()) <= _MIN_QUERY_LENGTH:
        logger.warning("Query rejected — too short: %r", query)
        return {"error": _SHORT_QUERY_ERROR, "documents": [], "analysis": ""}

    result = reasoning_agent.analyze_documents(query.strip())
    logger.info("Supervisor returning result for query: %.60s", query)
    return result
