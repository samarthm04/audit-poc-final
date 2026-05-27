"""Tests for retrieval_agent: filter detection, where-clause building, document retrieval."""

import pytest

from agents.retrieval_agent import (
    build_where_clause,
    detect_metadata_filters,
    retrieve_documents,
)


# ---------------------------------------------------------------------------
# detect_metadata_filters — OS filters
# ---------------------------------------------------------------------------

def test_detect_windows():
    """'windows' in query maps to os: Windows."""
    assert detect_metadata_filters("review windows server access controls")["os"] == "Windows"


def test_detect_linux():
    """'linux' in query maps to os: Linux."""
    assert detect_metadata_filters("linux system password policy review")["os"] == "Linux"


# ---------------------------------------------------------------------------
# detect_metadata_filters — database filters
# ---------------------------------------------------------------------------

def test_detect_sql_server_full():
    """'sql server' maps to database: SQL Server."""
    assert detect_metadata_filters("sql server database access review")["database"] == "SQL Server"


def test_detect_oracle():
    """'oracle' maps to database: Oracle."""
    assert detect_metadata_filters("oracle database privileged access")["database"] == "Oracle"


def test_detect_sql_shorthand():
    """'sql' alone maps to database: SQL Server."""
    assert detect_metadata_filters("sql database audit review")["database"] == "SQL Server"


# ---------------------------------------------------------------------------
# detect_metadata_filters — control_type filters
# ---------------------------------------------------------------------------

def test_detect_access_management():
    """'access management' maps to control_type: Access Management."""
    assert detect_metadata_filters("access management control review")["control_type"] == "Access Management"


def test_detect_provisioning():
    """'provisioning' maps to control_type: Access Management."""
    assert detect_metadata_filters("user provisioning process audit")["control_type"] == "Access Management"


def test_detect_change_management():
    """'change management' maps to control_type: Change Management."""
    assert detect_metadata_filters("change management process effectiveness")["control_type"] == "Change Management"


def test_detect_change_control():
    """'change control' maps to control_type: Change Management."""
    assert detect_metadata_filters("change control approval workflow")["control_type"] == "Change Management"


def test_detect_password():
    """'password' maps to control_type: Password Policy."""
    assert detect_metadata_filters("password complexity and expiry review")["control_type"] == "Password Policy"


# ---------------------------------------------------------------------------
# detect_metadata_filters — control_subtype filters
# ---------------------------------------------------------------------------

def test_detect_privileged():
    """'privileged' maps to control_subtype: Privileged Access."""
    assert detect_metadata_filters("privileged access review for server admins")["control_subtype"] == "Privileged Access"


def test_detect_termination():
    """'termination' maps to control_subtype: Access Revocation."""
    assert detect_metadata_filters("employee termination access revocation process")["control_subtype"] == "Access Revocation"


def test_detect_offboarding():
    """'offboarding' maps to control_subtype: Access Revocation."""
    assert detect_metadata_filters("offboarding checklist and access review")["control_subtype"] == "Access Revocation"


# ---------------------------------------------------------------------------
# detect_metadata_filters — edge cases
# ---------------------------------------------------------------------------

def test_detect_empty_query():
    """Empty query returns no filters."""
    assert detect_metadata_filters("") == {}


def test_detect_no_match():
    """Query with no recognised keywords returns empty dict."""
    assert detect_metadata_filters("general documentation review") == {}


def test_detect_combined_filters():
    """Query containing multiple keywords populates all matched filter keys."""
    filters = detect_metadata_filters("windows sql server access management review")
    assert filters.get("os") == "Windows"
    assert filters.get("database") == "SQL Server"
    assert filters.get("control_type") == "Access Management"


# ---------------------------------------------------------------------------
# build_where_clause
# ---------------------------------------------------------------------------

def test_build_where_empty():
    """Empty filters produce None."""
    assert build_where_clause({}) is None


def test_build_where_single():
    """Single filter produces a simple equality clause."""
    clause = build_where_clause({"os": "Windows"})
    assert clause == {"os": {"$eq": "Windows"}}


def test_build_where_multiple():
    """Two filters produce a ChromaDB $and clause with two conditions."""
    clause = build_where_clause({"os": "Windows", "database": "SQL Server"})
    assert clause is not None
    assert "$and" in clause
    assert len(clause["$and"]) == 2


# ---------------------------------------------------------------------------
# retrieve_documents
# ---------------------------------------------------------------------------

def test_retrieve_documents_shaped_correctly(mocker):
    """retrieve_documents returns list of {id, document, metadata, distance} dicts."""
    mock_collection = mocker.MagicMock()
    mock_collection.count.return_value = 2
    mock_collection.query.return_value = {
        "ids": [["WP001", "WP002"]],
        "documents": [["Access Management User Provisioning...", "Access Management Revocation..."]],
        "metadatas": [[
            {"os": "Windows", "database": "SQL Server", "control_type": "Access Management"},
            {"os": "Linux", "database": "Oracle", "control_type": "Access Management"},
        ]],
        "distances": [[0.12, 0.28]],
    }

    mocker.patch("agents.retrieval_agent._get_client", return_value=mocker.MagicMock())
    mocker.patch("agents.retrieval_agent._get_collection", return_value=mock_collection)

    results = retrieve_documents("access management review")

    assert len(results) == 2
    assert results[0] == {
        "id": "WP001",
        "document": "Access Management User Provisioning...",
        "metadata": {"os": "Windows", "database": "SQL Server", "control_type": "Access Management"},
        "distance": 0.12,
    }


def test_retrieve_documents_empty_collection(mocker):
    """retrieve_documents returns [] when collection is empty without raising."""
    mock_collection = mocker.MagicMock()
    mock_collection.count.return_value = 0

    mocker.patch("agents.retrieval_agent._get_client", return_value=mocker.MagicMock())
    mocker.patch("agents.retrieval_agent._get_collection", return_value=mock_collection)

    results = retrieve_documents("any query")
    assert results == []
