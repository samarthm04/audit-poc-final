from agents.retrieval_agent import retrieve_documents
from agents.reasoning_agent import analyze_documents

# Conversation Memory
conversation_memory = []


def handle_query(query):

    # =========================
    # INPUT VALIDATION
    # =========================

    if not query or len(query.strip()) == 0:
        return "Please enter a valid audit query.", []

    # Store memory
    conversation_memory.append(query)

    # =========================
    # TASK ROUTING
    # =========================

    retrieval_output = retrieve_documents(query)

    # =========================
    # WORKFLOW GOVERNANCE
    # =========================

    final_response = analyze_documents(retrieval_output)

    suggestions = retrieval_output.get("suggestions", [])

    return final_response, suggestions