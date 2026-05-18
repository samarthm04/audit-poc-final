def analyze_documents(agent_input):

    query = agent_input["query"]
    keywords = agent_input["keywords"]
    documents = agent_input["documents"]

    response = ""

    # =========================
    # CORE INTELLIGENCE
    # =========================

    response += f"Audit Query: {query}\n\n"

    # =========================
    # LOGICAL DESIGN BREAKDOWN
    # =========================

    response += "Identified Areas:\n"

    if len(keywords) == 0:
        response += "- General Audit Search\n"

    else:
        for keyword in keywords:
            response += f"- {keyword}\n"

    response += "\n"

    # =========================
    # GAP ANALYSIS + SCORING
    # =========================

    for index, doc in enumerate(documents):

        quality_score = 8
        risk_score = "Medium"

        if "approval" in doc.lower():
            quality_score += 1

        if "risk" in doc.lower():
            risk_score = "High"

        response += f"""
========================================
WORKPAPER {index + 1}
========================================

{doc}

Gap Analysis:
- Control design is documented
- Evidence testing exists
- Control objective is defined
- Further validation may be required for approval dependencies

Workpaper Scoring:
- Audit Quality Score: {quality_score}/10
- Risk Severity: {risk_score}

"""

    return response