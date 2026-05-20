def check_keyword_presence(text, keywords):
    found = []
    missing = []

    text_lower = text.lower()

    for keyword in keywords:
        if keyword.lower() in text_lower:
            found.append(keyword)
        else:
            missing.append(keyword)

    return found, missing


def diagnose_workpaper(item):
    text = item["document_text"]
    meta = item["metadata"]

    required_elements = [
        "Control Design",
        "Test Steps",
        "Testing Performed",
        "Actual Evidence",
        "Expected Evidence",
        "Risk Statement",
        "Audit Conclusion"
    ]

    found, missing = check_keyword_presence(text, required_elements)

    gap_keywords = [
        "missing",
        "not clearly indicate",
        "not available",
        "potential missing evidence",
        "exceptions"
    ]

    detected_gap_words = []

    for word in gap_keywords:
        if word in text.lower():
            detected_gap_words.append(word)

    completeness = "Complete"

    if len(missing) > 0 or len(detected_gap_words) > 0:
        completeness = "Needs Review"

    return {
        "workpaper_id": meta.get("workpaper_id", "N/A"),
        "control_id": meta.get("control_id", "N/A"),
        "control_name": meta.get("control_name", "N/A"),
        "risk_rating": meta.get("risk_rating", "N/A"),
        "source_document": meta.get("source_document", "N/A"),
        "completeness": completeness,
        "missing_sections": missing,
        "gap_indicators": detected_gap_words
    }


def compare_across_workpapers(workpapers):
    control_groups = {}

    for item in workpapers:
        meta = item["metadata"]
        control_id = meta.get("control_id", "Unknown")

        if control_id not in control_groups:
            control_groups[control_id] = []

        control_groups[control_id].append(item)

    comparison_output = ""

    for control_id, papers in control_groups.items():
        comparison_output += f"\nControl Group: {control_id}\n"
        comparison_output += f"Historical Workpapers Reviewed: {len(papers)}\n"

        all_text = " ".join([p["document_text"] for p in papers]).lower()

        expected_steps = []

        if "approval" in all_text:
            expected_steps.append("Documented approval should be retained.")

        if "rollback" in all_text:
            expected_steps.append("Rollback plan or rollback evidence should be tested.")

        if "testing" in all_text:
            expected_steps.append("Testing evidence should be inspected.")

        if "timestamp" in all_text or "deployment" in all_text:
            expected_steps.append("Approval timestamp should be compared against deployment timestamp.")

        if "manager approval" in all_text or "reviewer sign-off" in all_text:
            expected_steps.append("Reviewer or manager sign-off should be validated.")

        for step in expected_steps:
            comparison_output += f"- {step}\n"

    return comparison_output


def generate_recommendations(diagnosis_list):
    recommendations = []

    for diagnosis in diagnosis_list:
        workpaper_id = diagnosis["workpaper_id"]

        if diagnosis["completeness"] == "Needs Review":
            recommendations.append(
                f"{workpaper_id}: Review the identified gaps and obtain missing evidence."
            )

        for gap in diagnosis["gap_indicators"]:
            gap_lower = gap.lower()

            if "missing" in gap_lower:
                recommendations.append(
                    f"{workpaper_id}: Validate whether all expected evidence was inspected and attached."
                )

            if "not clearly indicate" in gap_lower:
                recommendations.append(
                    f"{workpaper_id}: Update the conclusion to clearly state operating effectiveness."
                )

            if "exceptions" in gap_lower:
                recommendations.append(
                    f"{workpaper_id}: Confirm exception count and document whether remediation was required."
                )

    if not recommendations:
        recommendations.append("No major remediation required based on retrieved workpapers.")

    return recommendations


def analyze_documents(agent_input):
    query = agent_input["query"]
    filters = agent_input["applied_filters"]
    workpapers = agent_input["retrieved_workpapers"]

    response = ""

    response += f"Audit Query: {query}\n\n"

    response += "Applied Metadata Filters:\n"

    if filters:
        for key, value in filters.items():
            response += f"- {key}: {value}\n"
    else:
        response += "- No metadata filter applied. Semantic search used across all workpapers.\n"

    response += "\n"

    if not workpapers:
        response += "No relevant workpapers found.\n"
        return response

    diagnosis_list = []

    response += "Workpaper Diagnosis:\n\n"

    for item in workpapers:
        diagnosis = diagnose_workpaper(item)
        diagnosis_list.append(diagnosis)

        response += f"""
Workpaper: {diagnosis['workpaper_id']}
Control: {diagnosis['control_name']}
Control ID: {diagnosis['control_id']}
Risk Rating: {diagnosis['risk_rating']}
Source: {diagnosis['source_document']}

Completeness Status:
{diagnosis['completeness']}

Missing Sections:
{', '.join(diagnosis['missing_sections']) if diagnosis['missing_sections'] else 'None'}

Gap Indicators:
{', '.join(diagnosis['gap_indicators']) if diagnosis['gap_indicators'] else 'None'}

"""

    response += "\nHistorical Comparison:\n"
    response += compare_across_workpapers(workpapers)

    response += "\nRecommended Remediation Steps:\n"

    recommendations = generate_recommendations(diagnosis_list)

    for rec in recommendations:
        response += f"- {rec}\n"

    return response