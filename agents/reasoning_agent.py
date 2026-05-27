"""Reasoning agent: composes a structured audit prompt and calls the LLM."""

import logging

from agents import llm_agent, retrieval_agent

logger = logging.getLogger(__name__)

_SYSTEM_PROMPT = (
    "You are a senior IT auditor with expertise in SOX, ISO 27001, and PCI-DSS. "
    "Analyse the workpaper excerpts provided and return your findings in exactly "
    "four labeled sections as instructed."
)

_OUTPUT_FORMAT = (
    "Return your findings as plain text using exactly these four labeled sections "
    "(each label on its own line, followed by your content):\n\n"
    "PRESENT STEPS\n"
    "MISSING STEPS\n"
    "EVIDENCE GAPS\n"
    "AUGMENTED PROCEDURE"
)


def _format_excerpt(index: int, doc: dict) -> str:
    """Format one workpaper as a numbered excerpt with key metadata inline."""
    meta = doc.get("metadata", {})
    return (
        f"{index}. [ID: {doc['id']}]  "
        f"OS: {meta.get('os', 'N/A')} | DB: {meta.get('database', 'N/A')} | "
        f"Control: {meta.get('control_type', 'N/A')}\n"
        f"{doc.get('document', '')}"
    )


def _compose_prompt(query: str, docs: list[dict]) -> str:
    """Build the full LLM prompt from the audit query and retrieved workpaper excerpts."""
    if docs:
        excerpts = "\n\n".join(_format_excerpt(i + 1, d) for i, d in enumerate(docs))
    else:
        excerpts = "No relevant workpaper excerpts found in the knowledge base."

    analysis_instruction = (
        "Identify: "
        "(a) which test steps are present in the retrieved workpapers, "
        "(b) which test steps are missing compared to best practice, "
        "(c) what evidence gaps exist, "
        "(d) your augmented recommended test steps."
    )

    return (
        f"{_SYSTEM_PROMPT}\n\n"
        f"Audit Query: {query}\n\n"
        f"Retrieved Workpaper Excerpts:\n{excerpts}\n\n"
        f"{analysis_instruction}\n\n"
        f"{_OUTPUT_FORMAT}"
    )


def analyze_documents(query: str) -> dict:
    """Retrieve relevant workpapers and return LLM analysis alongside source docs."""
    logger.info("Analyzing query: %s", query)
    docs = retrieval_agent.retrieve_documents(query)
    prompt = _compose_prompt(query, docs)
    analysis = llm_agent.ask_llm(prompt)
    logger.info("Analysis complete — %d docs retrieved", len(docs))
    return {"query": query, "documents": docs, "analysis": analysis}
