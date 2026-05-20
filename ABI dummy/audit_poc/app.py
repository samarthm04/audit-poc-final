import streamlit as st
import json
import chromadb
from docx import Document

from agents.supervisor_agent import handle_query
from agents.retrieval_agent import retrieve_documents
from agents.reasoning_agent import analyze_documents


st.set_page_config(
    page_title="AI Audit Assistant",
    layout="wide"
)


@st.cache_resource
def load_chroma_collection():
    client = chromadb.PersistentClient(path="./chroma_db")
    collection = client.get_or_create_collection(name="audit_collection")
    return collection


collection = load_chroma_collection()


def safe_join(items):
    if not items:
        return ""

    return " | ".join(str(x) for x in items)


def get_total_workpapers():
    try:
        return collection.count()
    except Exception:
        return 0


def calculate_completeness_score(text):

    checks = {
        "Control Design": "control design" in text.lower(),
        "Test Steps": "test steps" in text.lower(),
        "Testing Performed": "testing performed" in text.lower(),
        "Actual Evidence": "actual evidence" in text.lower(),
        "Expected Evidence": "expected evidence" in text.lower(),
        "Risk Statement": "risk statement" in text.lower(),
        "Audit Conclusion": "audit conclusion" in text.lower()
    }

    completed = sum(1 for value in checks.values() if value)

    total = len(checks)

    score = int((completed / total) * 100)

    return score, checks


def convert_json_to_text(wp):

    control = wp.get("control", {})
    testing = wp.get("testing", {})
    evidence = wp.get("evidence", {})
    risk = wp.get("risk", {})
    conclusion = wp.get("auditConclusion", {})

    return f"""
    Workpaper ID: {wp.get("workpaperId", wp.get("id", "N/A"))}

    Control Name:
    {control.get("controlName", control.get("type", "N/A"))}

    Objective:
    {control.get("objective", "N/A")}

    Test Steps:
    {safe_join(testing.get("testSteps", []))}

    Testing Performed:
    {testing.get("testingPerformedNarrative", "N/A")}

    Actual Evidence:
    {safe_join(evidence.get("actualEvidenceInspected", []))}

    Expected Evidence:
    {safe_join(evidence.get("expectedEvidence", []))}

    Risk Statement:
    {risk.get("riskStatement", risk.get("statement", "N/A"))}

    Audit Conclusion:
    {conclusion.get("conclusionNarrative", "N/A")}
    """


def store_json_workpaper(wp, index=0):

    workpaper_id = wp.get(
        "workpaperId",
        wp.get("id", f"UPLOADED-JSON-{index}")
    )

    text = convert_json_to_text(wp)

    collection.upsert(
        documents=[text],
        ids=[workpaper_id],
        metadatas=[
            {
                "workpaper_id": workpaper_id,
                "control_name": wp.get("control", {}).get(
                    "controlName",
                    "N/A"
                )
            }
        ]
    )

    return text


def extract_docx_text(uploaded_file):

    doc = Document(uploaded_file)

    paragraphs = []

    for para in doc.paragraphs:
        if para.text.strip():
            paragraphs.append(para.text.strip())

    return "\n".join(paragraphs)


def store_docx_workpaper(uploaded_file):

    text = extract_docx_text(uploaded_file)

    file_name = uploaded_file.name

    workpaper_id = (
        "UPLOADED-DOCX-" +
        file_name.replace(" ", "_")
    )

    collection.upsert(
        documents=[text],
        ids=[workpaper_id],
        metadatas=[
            {
                "workpaper_id": workpaper_id,
                "control_name": "Uploaded Workpaper"
            }
        ]
    )

    return text


def summarize_output(text):

    lines = text.split("\n")

    important_lines = []

    keywords = [
        "Audit Query",
        "Workpaper",
        "Control",
        "Gap",
        "Missing",
        "Recommendation",
        "Complete",
        "Needs Review"
    ]

    for line in lines:
        if any(
            keyword.lower() in line.lower()
            for keyword in keywords
        ):
            important_lines.append(line)

    if not important_lines:
        return text[:1500]

    return "\n".join(important_lines[:100])


def show_clean_response(text):

    st.markdown("### Audit Analysis Result")

    score, checks = calculate_completeness_score(text)

    st.metric("Completeness Score", f"{score}%")

    tab1, tab2, tab3, tab4 = st.tabs(
        [
            "Summary",
            "Gaps",
            "Recommendations",
            "Full Output"
        ]
    )

    with tab1:
        st.text(summarize_output(text))

    with tab2:

        gap_lines = []

        for line in text.split("\n"):
            if (
                "gap" in line.lower()
                or "missing" in line.lower()
                or "needs review" in line.lower()
            ):
                gap_lines.append(line)

        if gap_lines:
            st.text("\n".join(gap_lines))

        else:
            st.success("No major gaps detected.")

    with tab3:

        recommendation_lines = []

        capture = False

        for line in text.split("\n"):

            if "Recommended Remediation Steps" in line:
                capture = True

            if capture:
                recommendation_lines.append(line)

        if recommendation_lines:
            st.text("\n".join(recommendation_lines))

        else:
            st.info("No remediation recommendations found.")

    with tab4:
        st.text(text)


if "past_inputs" not in st.session_state:
    st.session_state.past_inputs = []

if "last_response" not in st.session_state:
    st.session_state.last_response = ""

if "uploaded_file_count" not in st.session_state:
    st.session_state.uploaded_file_count = 0

if "last_uploaded_text" not in st.session_state:
    st.session_state.last_uploaded_text = ""


st.title("AI Audit Assistant")

st.caption(
    "Search, diagnose, and review audit workpapers."
)

st.markdown("### Audit Overview")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Queries Run",
        len(st.session_state.past_inputs)
    )

with col2:
    st.metric(
        "Workpapers in ChromaDB",
        get_total_workpapers()
    )

with col3:
    st.metric(
        "Files Uploaded",
        st.session_state.uploaded_file_count
    )

st.divider()

st.markdown("### Ask an Audit Question")

query = st.text_area(
    "Enter your audit query",
    height=100
)

summary_mode = st.toggle(
    "Show summarized response"
)

col_a, col_b = st.columns(2)

with col_a:
    run_button = st.button(
        "Run Analysis",
        use_container_width=True
    )

with col_b:
    clear_button = st.button(
        "Clear Output",
        use_container_width=True
    )

if clear_button:
    st.session_state.last_response = ""

if run_button:

    if query.strip() == "":
        st.warning("Please enter a query.")

    else:

        st.session_state.past_inputs.append(query)

        with st.spinner("Running audit analysis..."):

            result, suggestions = handle_query(query)

            st.session_state.last_response = result

if st.session_state.last_response:

    st.divider()

    if summary_mode:
        st.text(
            summarize_output(
                st.session_state.last_response
            )
        )

    else:
        show_clean_response(
            st.session_state.last_response
        )

st.divider()

st.markdown("### Upload Workpaper or JSON Dataset")

uploaded_file = st.file_uploader(
    "Upload JSON or DOCX",
    type=["json", "docx"]
)

if uploaded_file is not None:

    if st.button(
        "Store Uploaded File",
        use_container_width=True
    ):

        with st.spinner(
            "Storing file into ChromaDB..."
        ):

            if uploaded_file.name.endswith(".json"):

                data = json.load(uploaded_file)

                if isinstance(data, list):

                    uploaded_texts = []

                    for index, wp in enumerate(data):
                        uploaded_texts.append(
                            store_json_workpaper(
                                wp,
                                index
                            )
                        )

                    st.session_state.last_uploaded_text = (
                        "\n\n".join(uploaded_texts)
                    )

                elif isinstance(data, dict):

                    st.session_state.last_uploaded_text = (
                        store_json_workpaper(
                            data,
                            0
                        )
                    )

            elif uploaded_file.name.endswith(".docx"):

                st.session_state.last_uploaded_text = (
                    store_docx_workpaper(
                        uploaded_file
                    )
                )

            st.session_state.uploaded_file_count += 1

            st.success(
                "File stored successfully."
            )

if st.session_state.last_uploaded_text:

    if st.button(
        "Diagnose Uploaded Workpaper",
        use_container_width=True
    ):

        uploaded_score, uploaded_checks = (
            calculate_completeness_score(
                st.session_state.last_uploaded_text
            )
        )

        st.metric(
            "Uploaded Workpaper Completeness",
            f"{uploaded_score}%"
        )

        for section, present in uploaded_checks.items():

            if present:
                st.write(f"✅ {section}")

            else:
                st.write(f"❌ {section}")

st.divider()

st.markdown("### Previous Queries")

if len(st.session_state.past_inputs) == 0:

    st.info("No previous queries yet.")

else:

    for item in reversed(
        st.session_state.past_inputs
    ):
        st.write("- " + item)