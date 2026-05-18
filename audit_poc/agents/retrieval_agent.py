import chromadb

# Connect to ChromaDB
client = chromadb.PersistentClient(path="./chroma_db")

collection = client.get_collection("audit_collection")


def retrieve_documents(query):

    # =========================
    # PRIMARY FILTERING
    # =========================

    keywords = []

    possible_keywords = [
        "change",
        "access",
        "review",
        "security",
        "approval",
        "risk",
        "production",
        "SOX",
        "ITGC"
    ]

    # Search suggestions
    suggestions = []

    for word in possible_keywords:

        if query.lower() in word.lower():
            suggestions.append(word)

        if word.lower() in query.lower():
            keywords.append(word)

    # =========================
    # SEMANTIC SEARCH
    # =========================

    results = collection.query(
        query_texts=[query],
        n_results=3
    )

    retrieved_docs = results["documents"][0]

    # =========================
    # SECONDARY FILTERING
    # =========================

    filtered_docs = []

    for doc in retrieved_docs:

        if len(keywords) == 0:
            filtered_docs.append(doc)

        elif any(keyword.lower() in doc.lower() for keyword in keywords):
            filtered_docs.append(doc)

    # =========================
    # ENHANCED REASONING INPUT
    # =========================

    enhanced_input = {
        "query": query,
        "keywords": keywords,
        "documents": filtered_docs,
        "suggestions": suggestions
    }

    return enhanced_input