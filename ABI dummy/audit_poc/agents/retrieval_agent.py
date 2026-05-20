import chromadb

client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_collection("audit_collection")


def detect_metadata_filters(query):
    query_lower = query.lower()
    filters = {}

    control_map = {
        "crb": "CHG-CRB-001",
        "arb": "CHG-CRB-001",
        "change": "CHG-CRB-001",
        "production": "CHG-CRB-001",
        "ad": "IAM-AD-REV-001",
        "active directory": "IAM-AD-REV-001",
        "revocation": "IAM-AD-REV-001",
        "sql": "IAM-SQL-UAR-001",
        "database": "IAM-SQL-UAR-001",
        "user access review": "IAM-UAR-001",
        "uar": "IAM-UAR-001"
    }

    for keyword, control_id in control_map.items():
        if keyword in query_lower:
            filters["control_id"] = control_id
            break

    if "high" in query_lower:
        filters["risk_rating"] = "High"

    if "medium" in query_lower:
        filters["risk_rating"] = "Medium"

    return filters


def build_where_clause(filters):
    if not filters:
        return None

    conditions = []

    for key, value in filters.items():
        conditions.append({key: {"$eq": value}})

    if len(conditions) == 1:
        return conditions[0]

    return {"$and": conditions}


def extract_structured_info(doc, metadata):
    return {
        "metadata": metadata,
        "document_text": doc
    }


def retrieve_documents(query, n_results=6):
    filters = detect_metadata_filters(query)
    where_clause = build_where_clause(filters)

    try:
        if where_clause:
            results = collection.query(
                query_texts=[query],
                n_results=n_results,
                where=where_clause
            )
        else:
            results = collection.query(
                query_texts=[query],
                n_results=n_results
            )

    except Exception:
        results = collection.query(
            query_texts=[query],
            n_results=n_results
        )

    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]

    extracted = []

    for doc, meta in zip(documents, metadatas):
        extracted.append(extract_structured_info(doc, meta))

    return {
        "query": query,
        "applied_filters": filters,
        "retrieved_count": len(extracted),
        "retrieved_workpapers": extracted
    }