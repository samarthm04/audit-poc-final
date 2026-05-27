"""Combined Streamlit frontend for the Audit Workpaper Intelligence Assistant."""

from __future__ import annotations

import json
import logging
from io import BytesIO
from pathlib import Path
from typing import Any

import streamlit as st
from dotenv import load_dotenv

load_dotenv()

from agents import llm_agent, supervisor_agent  # noqa: E402
from chroma_client import get_chroma_client  # noqa: E402

try:
    from docx import Document
except ImportError:  # pragma: no cover - optional dependency guard
    Document = None


logging.basicConfig(level=logging.INFO)

CHROMA_PATH = "./chroma_db"
COLLECTION_NAME = "audit_workpapers"
SEED_DATA_FILE = Path(__file__).resolve().parent / "data" / "workpapers_remote_converted.json"
SECTION_LABELS = ("PRESENT STEPS", "MISSING STEPS", "EVIDENCE GAPS", "AUGMENTED PROCEDURE")
REQUIRED_COMPLETENESS_TERMS = {
    "Control Design": ("control design", "design", "control objective"),
    "Test Steps": ("test steps", "procedure", "testing"),
    "Testing Performed": ("testing performed", "performed", "sample"),
    "Actual Evidence": ("actual evidence", "evidence inspected", "reviewed"),
    "Expected Evidence": ("expected evidence", "evidence required", "required evidence"),
    "Risk Statement": ("risk statement", "risk"),
    "Audit Conclusion": ("audit conclusion", "conclusion", "operating effectively"),
}


st.set_page_config(page_title="Audit Workpaper Intelligence Assistant", layout="wide")


@st.cache_resource
def get_collection():
    client = get_chroma_client()
    collection = client.get_or_create_collection(COLLECTION_NAME)
    seed_collection_if_empty(collection)
    return collection


def build_seed_document(wp: dict[str, Any]) -> str:
    control = wp.get("control", {})
    design = control.get("controlDesign", {})
    artifact = wp.get("testArtifact", {})
    steps = " ".join(artifact.get("testSteps", []))
    evidence = " ".join(artifact.get("evidenceRequired", []))
    risk = wp.get("risk", {})
    return " ".join(
        [
            str(control.get("type", "")),
            str(control.get("subType", "")),
            str(control.get("objective", "")),
            str(design.get("description", "")),
            steps,
            evidence,
            str(risk.get("statement", "")),
        ]
    )


def seed_collection_if_empty(collection) -> None:
    try:
        if collection.count() > 0 or not SEED_DATA_FILE.exists():
            return
        with open(SEED_DATA_FILE, encoding="utf-8") as f:
            workpapers = json.load(f)
        collection.add(
            ids=[wp["id"] for wp in workpapers],
            documents=[build_seed_document(wp) for wp in workpapers],
            metadatas=[metadata_for_workpaper(wp) for wp in workpapers],
        )
        logging.info("Seeded %d workpapers into ChromaDB", len(workpapers))
    except Exception as exc:  # noqa: BLE001
        logging.warning("Could not seed ChromaDB collection: %s", exc)


def init_state() -> None:
    defaults = {
        "query_count": 0,
        "uploaded_file_count": 0,
        "previous_queries": [],
        "last_result": None,
        "last_uploaded_text": "",
        "last_uploaded_score": None,
        "last_uploaded_checks": {},
        "refinement_messages": [],
        "refined_documents": None,
        "refinement_summary": "",
    }
    for key, value in defaults.items():
        st.session_state.setdefault(key, value)


def collection_count() -> int:
    try:
        return get_collection().count()
    except Exception:
        return 0


def parse_analysis_sections(analysis: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current: str | None = None

    for line in analysis.splitlines():
        stripped = line.strip().upper()
        if stripped in SECTION_LABELS:
            current = stripped
            sections[current] = []
            continue
        if current is not None:
            sections[current].append(line)

    return {label: "\n".join(lines).strip() for label, lines in sections.items()}


def calculate_completeness_score(text: str) -> tuple[int, dict[str, bool]]:
    lower = text.lower()
    checks = {
        section: any(term in lower for term in terms)
        for section, terms in REQUIRED_COMPLETENESS_TERMS.items()
    }
    score = int((sum(checks.values()) / len(checks)) * 100)
    return score, checks


def summarize_analysis(analysis: str) -> str:
    sections = parse_analysis_sections(analysis)
    parts = []
    for label in ("MISSING STEPS", "EVIDENCE GAPS", "AUGMENTED PROCEDURE"):
        content = sections.get(label)
        if content:
            parts.append(f"{label}\n{content}")
    return "\n\n".join(parts) if parts else analysis[:1800]


def reset_refinement_state() -> None:
    st.session_state.refinement_messages = []
    st.session_state.refined_documents = None
    st.session_state.refinement_summary = ""


def docs_for_refinement(result: dict[str, Any]) -> list[dict[str, Any]]:
    if st.session_state.refined_documents is not None:
        return st.session_state.refined_documents
    return result.get("documents", [])


def doc_label(doc: dict[str, Any]) -> str:
    meta = doc.get("metadata", {})
    return (
        f"{doc.get('id', 'N/A')} | {meta.get('control_type', 'N/A')} | "
        f"{meta.get('control_subtype', 'N/A')} | OS: {meta.get('os', 'N/A')} | "
        f"DB: {meta.get('database', 'N/A')}"
    )


def compact_doc_for_prompt(doc: dict[str, Any]) -> str:
    meta = doc.get("metadata", {})
    excerpt = str(doc.get("document", ""))[:900]
    return (
        f"ID: {doc.get('id', 'N/A')}\n"
        f"Metadata: {json.dumps(meta, ensure_ascii=True)}\n"
        f"Excerpt: {excerpt}"
    )


def extract_json_object(text: str) -> dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        chunks = cleaned.split("```")
        cleaned = chunks[1] if len(chunks) > 1 else cleaned
        if cleaned.lstrip().startswith("json"):
            cleaned = cleaned.lstrip()[4:]

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise ValueError("No JSON object found in refinement response")
    return json.loads(cleaned[start : end + 1])


def refine_workpapers_with_llm(
    original_query: str,
    candidate_docs: list[dict[str, Any]],
    user_message: str,
    chat_history: list[dict[str, str]],
) -> tuple[list[dict[str, Any]], str]:
    """Use Mistral to narrow the current candidate workpapers."""
    if not candidate_docs:
        return [], "There are no candidate workpapers to narrow."

    candidates = "\n\n---\n\n".join(compact_doc_for_prompt(doc) for doc in candidate_docs)
    recent_history = "\n".join(
        f"{item['role']}: {item['content']}"
        for item in chat_history[-6:]
    )
    valid_ids = [str(doc.get("id", "")) for doc in candidate_docs]

    prompt = f"""
You are helping an auditor narrow a retrieved set of audit workpapers.

Original audit query:
{original_query}

Current candidate workpapers:
{candidates}

Recent refinement chat:
{recent_history or "No prior refinement chat."}

New auditor message:
{user_message}

Task:
1. Select only the workpaper IDs from the current candidates that still match the auditor's new narrowing instruction.
2. If the message is a clarification question rather than a filter, keep the most relevant current candidates and answer the question.
3. Do not invent IDs. Select IDs only from this allowed list: {valid_ids}
4. Keep at least one ID if any candidate is plausibly relevant.

Return ONLY valid JSON with this exact schema:
{{
  "selected_ids": ["WP-001"],
  "answer": "Briefly explain why these workpapers remain relevant and what was filtered out."
}}
""".strip()

    raw = llm_agent.ask_llm(prompt)
    parsed = extract_json_object(raw)
    selected_ids = {str(item) for item in parsed.get("selected_ids", [])}
    selected_docs = [doc for doc in candidate_docs if str(doc.get("id", "")) in selected_ids]

    if not selected_docs:
        selected_docs = candidate_docs[:1]

    answer = str(parsed.get("answer") or "I narrowed the workpaper set based on your message.")
    return selected_docs, answer


def safe_join(items: Any) -> str:
    if not items:
        return ""
    if isinstance(items, list):
        return " | ".join(str(item) for item in items)
    return str(items)


def localize_workpaper(record: dict[str, Any], fallback_id: str) -> dict[str, Any]:
    """Normalize uploaded JSON into the canonical local workpaper schema."""
    if "system" in record and "testArtifact" in record:
        return record

    control = record.get("control", {})
    testing = record.get("testing", {})
    evidence = record.get("evidence", {})
    risk = record.get("risk", {})
    audit_meta = record.get("auditMetadata", {})
    design = record.get("controlDesign", {})

    return {
        "id": record.get("workpaperId") or record.get("id") or fallback_id,
        "system": {
            "os": "N/A",
            "database": "N/A",
            "applicationType": record.get("systemContext", {}).get("primarySystem", "Uploaded"),
        },
        "control": {
            "type": control.get("domain") or control.get("controlName") or "Uploaded Control",
            "subType": control.get("subDomain") or "N/A",
            "objective": control.get("objective", "N/A"),
            "controlDesign": {
                "description": design.get("designUnderstanding", "N/A"),
                "frequency": control.get("frequency", "N/A"),
                "owner": design.get("processOwnerInterviewed", "N/A"),
            },
        },
        "testArtifact": {
            "testSteps": testing.get("testSteps", []) or [],
            "evidenceRequired": evidence.get("expectedEvidence", []) or [],
        },
        "risk": {
            "statement": risk.get("riskStatement", "N/A"),
            "category": risk.get("riskCategory", "N/A"),
        },
        "auditContext": {
            "industry": "N/A",
            "framework": audit_meta.get("frameworks", []) or [],
            "year": audit_meta.get("auditYear", "N/A"),
        },
        "qualitySignals": {"reviewStatus": "Uploaded", "usageCount": 0},
    }


def workpaper_to_text(wp: dict[str, Any]) -> str:
    control = wp.get("control", {})
    design = control.get("controlDesign", {})
    artifact = wp.get("testArtifact", {})
    risk = wp.get("risk", {})
    return "\n".join(
        [
            f"Workpaper ID: {wp.get('id', 'N/A')}",
            f"Control Type: {control.get('type', 'N/A')}",
            f"Control Subtype: {control.get('subType', 'N/A')}",
            f"Objective: {control.get('objective', 'N/A')}",
            f"Control Design: {design.get('description', 'N/A')}",
            f"Test Steps: {safe_join(artifact.get('testSteps', []))}",
            f"Expected Evidence: {safe_join(artifact.get('evidenceRequired', []))}",
            f"Risk Statement: {risk.get('statement', 'N/A')}",
        ]
    )


def metadata_for_workpaper(wp: dict[str, Any]) -> dict[str, Any]:
    system = wp.get("system", {})
    control = wp.get("control", {})
    ctx = wp.get("auditContext", {})
    quality = wp.get("qualitySignals", {})
    frameworks = ctx.get("framework", [])
    return {
        "id": wp.get("id", ""),
        "os": system.get("os", ""),
        "database": system.get("database", ""),
        "applicationType": system.get("applicationType", ""),
        "control_type": control.get("type", ""),
        "control_subtype": control.get("subType", ""),
        "industry": ctx.get("industry", ""),
        "framework": ", ".join(frameworks) if isinstance(frameworks, list) else str(frameworks),
        "reviewStatus": quality.get("reviewStatus", ""),
        "usageCount": quality.get("usageCount", 0),
    }


def store_workpaper(wp: dict[str, Any]) -> str:
    collection = get_collection()
    text = workpaper_to_text(wp)
    wp_id = wp.get("id", "UPLOADED-WP")
    collection.upsert(ids=[wp_id], documents=[text], metadatas=[metadata_for_workpaper(wp)])
    return text


def extract_docx_text(uploaded_file) -> str:
    if Document is None:
        raise RuntimeError("python-docx is not installed. Run pip install -r requirements.txt.")
    doc = Document(BytesIO(uploaded_file.getvalue()))
    return "\n".join(p.text.strip() for p in doc.paragraphs if p.text.strip())


def render_result(result: dict[str, Any]) -> None:
    docs = result.get("documents", [])
    analysis = result.get("analysis", "")

    st.subheader("Retrieved Workpapers")
    with st.expander(f"{len(docs)} workpapers retrieved", expanded=True):
        if not docs:
            st.info("No workpapers retrieved. Run the ingestion script or upload workpapers.")
        for doc in docs:
            meta = doc.get("metadata", {})
            st.markdown(
                f"**{doc.get('id', 'N/A')}** | "
                f"{meta.get('control_type', 'N/A')} | "
                f"{meta.get('control_subtype', 'N/A')} | "
                f"OS: {meta.get('os', 'N/A')} | DB: {meta.get('database', 'N/A')}"
            )
            if doc.get("distance") is not None:
                st.caption(f"Distance: {doc['distance']:.4f}")
            excerpt = doc.get("document", "")
            st.write(excerpt[:500] + ("..." if len(excerpt) > 500 else ""))
            st.divider()

    st.subheader("LLM Audit Analysis")
    sections = parse_analysis_sections(analysis)
    tabs = st.tabs(["Summary", "Present Steps", "Missing Steps", "Evidence Gaps", "Augmented Procedure", "Raw Output"])
    with tabs[0]:
        st.code(summarize_analysis(analysis), language=None)
    with tabs[1]:
        st.code(sections.get("PRESENT STEPS", "No present-steps section found."), language=None)
    with tabs[2]:
        st.code(sections.get("MISSING STEPS", "No missing-steps section found."), language=None)
    with tabs[3]:
        st.code(sections.get("EVIDENCE GAPS", "No evidence-gaps section found."), language=None)
    with tabs[4]:
        st.code(sections.get("AUGMENTED PROCEDURE", "No augmented-procedure section found."), language=None)
    with tabs[5]:
        st.code(analysis, language=None)


def render_refinement_chat(result: dict[str, Any]) -> None:
    original_docs = result.get("documents", [])
    if not original_docs:
        return

    st.subheader("Narrow Workpapers")
    current_docs = docs_for_refinement(result)
    st.caption(f"Current narrowed set: {len(current_docs)} of {len(original_docs)} workpapers")

    if current_docs:
        with st.expander("Current narrowed workpapers", expanded=True):
            for doc in current_docs:
                st.write("- " + doc_label(doc))

    for message in st.session_state.refinement_messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    prompt = st.chat_input(
        "Ask a follow-up to narrow the workpapers, e.g. only emergency changes with missing approval evidence"
    )
    if not prompt:
        return

    st.session_state.refinement_messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Narrowing workpapers..."):
            try:
                narrowed_docs, answer = refine_workpapers_with_llm(
                    result.get("query", ""),
                    current_docs,
                    prompt,
                    st.session_state.refinement_messages,
                )
                st.session_state.refined_documents = narrowed_docs
                st.session_state.refinement_summary = answer
            except Exception as exc:  # noqa: BLE001
                answer = f"I could not narrow the workpapers: {exc}"
            st.write(answer)

    st.session_state.refinement_messages.append({"role": "assistant", "content": answer})
    st.rerun()


def render_upload_workflow() -> None:
    st.subheader("Upload Workpaper")
    uploaded_file = st.file_uploader("Upload JSON or DOCX", type=["json", "docx"])

    if uploaded_file is None:
        return

    if st.button("Store Uploaded File", use_container_width=True):
        try:
            if uploaded_file.name.endswith(".json"):
                raw = json.load(uploaded_file)
                records = raw if isinstance(raw, list) else [raw]
                texts = []
                for index, record in enumerate(records, start=1):
                    wp = localize_workpaper(record, f"UPLOADED-JSON-{index}")
                    texts.append(store_workpaper(wp))
                combined_text = "\n\n".join(texts)
            else:
                combined_text = extract_docx_text(uploaded_file)
                wp = {
                    "id": "UPLOADED-DOCX-" + uploaded_file.name.replace(" ", "_"),
                    "system": {"os": "N/A", "database": "N/A", "applicationType": "Uploaded DOCX"},
                    "control": {
                        "type": "Uploaded Control",
                        "subType": "N/A",
                        "objective": "N/A",
                        "controlDesign": {"description": combined_text[:1200], "frequency": "N/A", "owner": "N/A"},
                    },
                    "testArtifact": {"testSteps": [], "evidenceRequired": []},
                    "risk": {"statement": "N/A", "category": "N/A"},
                    "auditContext": {"industry": "N/A", "framework": [], "year": "N/A"},
                    "qualitySignals": {"reviewStatus": "Uploaded", "usageCount": 0},
                }
                store_workpaper(wp)

            score, checks = calculate_completeness_score(combined_text)
            st.session_state.uploaded_file_count += 1
            st.session_state.last_uploaded_text = combined_text
            st.session_state.last_uploaded_score = score
            st.session_state.last_uploaded_checks = checks
            st.success("File stored in ChromaDB.")
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not store uploaded file: {exc}")

    if st.session_state.last_uploaded_text:
        st.metric("Uploaded Workpaper Completeness", f"{st.session_state.last_uploaded_score}%")
        missing = [name for name, present in st.session_state.last_uploaded_checks.items() if not present]
        if missing:
            st.warning("Missing or weak sections: " + ", ".join(missing))
        else:
            st.success("All expected completeness sections were detected.")


def main() -> None:
    init_state()

    st.title("Audit Workpaper Intelligence Assistant")
    st.caption("Search, reason over, upload, and diagnose audit workpapers.")

    last_result = st.session_state.last_result or {}
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Queries Run", st.session_state.query_count)
    col2.metric("Workpapers in ChromaDB", collection_count())
    col3.metric("Files Uploaded", st.session_state.uploaded_file_count)
    col4.metric("Last Retrieved", len(last_result.get("documents", [])))

    st.divider()

    query = st.text_area(
        "Ask an audit question",
        height=120,
        placeholder="Review change management controls for Windows SQL Server emergency changes and identify missing evidence.",
    )

    run_col, clear_col = st.columns(2)
    run_clicked = run_col.button("Run Analysis", type="primary", use_container_width=True)
    clear_clicked = clear_col.button("Clear Output", use_container_width=True)

    if clear_clicked:
        st.session_state.last_result = None
        reset_refinement_state()

    if run_clicked:
        if not query.strip():
            st.warning("Please enter an audit query.")
        else:
            with st.spinner("Running audit analysis..."):
                result = supervisor_agent.handle_query(query)
            if result.get("error"):
                st.error(result["error"])
            else:
                st.session_state.query_count += 1
                st.session_state.previous_queries.append(query)
                st.session_state.last_result = result
                reset_refinement_state()

    if st.session_state.last_result:
        render_result(st.session_state.last_result)
        render_refinement_chat(st.session_state.last_result)

    st.divider()
    render_upload_workflow()

    st.divider()
    st.subheader("Previous Queries")
    if not st.session_state.previous_queries:
        st.info("No previous queries yet.")
    else:
        for item in reversed(st.session_state.previous_queries[-10:]):
            st.write("- " + item)


if __name__ == "__main__":
    main()
