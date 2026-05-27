from agents.retrieval_agent import retrieve_documents
from agents.reasoning_agent import analyze_documents

conversation_memory = []


def classify_query(query):
    query_lower = query.lower()

    if "gap" in query_lower or "missing" in query_lower or "complete" in query_lower:
        return "diagnosis"

    if "compare" in query_lower or "historical" in query_lower:
        return "comparison"

    if "recommend" in query_lower or "remediate" in query_lower:
        return "recommendation"

    return "general_search"


def handle_query(query):
    if not query or len(query.strip()) == 0:
        return "Please enter a valid audit query.", []

    task_type = classify_query(query)

    conversation_memory.append({
        "query": query,
        "task_type": task_type
    })

    retrieval_output = retrieve_documents(query)

    final_response = analyze_documents(retrieval_output)

    suggestions = [
        "Check completeness for CRB controls",
        "Find missing evidence in SQL access reviews",
        "Compare historical user access review workpapers",
        "Show high risk change management gaps"
    ]

    return final_response, suggestions