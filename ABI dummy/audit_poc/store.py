import chromadb
import json
import os
import shutil
from sentence_transformers import SentenceTransformer

CHROMA_PATH = "./chroma_db"
DATA_FILE = "./data/project_ready_workpaper_dataset.json"

if os.path.exists(CHROMA_PATH):
    shutil.rmtree(CHROMA_PATH)

client = chromadb.PersistentClient(path=CHROMA_PATH)

collection = client.get_or_create_collection(
    name="audit_collection"
)

model = SentenceTransformer("all-MiniLM-L6-v2")


def safe_join(items):
    if not items:
        return ""
    return " | ".join(str(x) for x in items)


with open(DATA_FILE, "r", encoding="utf-8") as file:
    workpapers = json.load(file)

for wp in workpapers:
    control = wp.get("control", {})
    system = wp.get("systemContext", {})
    audit = wp.get("auditMetadata", {})
    design = wp.get("controlDesign", {})
    testing = wp.get("testing", {})
    evidence = wp.get("evidence", {})
    risk = wp.get("risk", {})
    gaps = wp.get("gapAnalysisFields", {})
    retrieval = wp.get("retrieval", {})
    conclusion = wp.get("auditConclusion", {})

    text = f"""
    Workpaper ID: {wp.get("workpaperId", "N/A")}
    Source Document: {wp.get("sourceDocument", "N/A")}
    Document Title: {wp.get("documentTitle", "N/A")}

    Control ID: {control.get("controlId", "N/A")}
    Control Name: {control.get("controlName", "N/A")}
    Domain: {control.get("domain", "N/A")}
    Sub Domain: {control.get("subDomain", "N/A")}
    Objective: {control.get("objective", "N/A")}
    Frequency: {control.get("frequency", "N/A")}
    Key Control: {control.get("keyControl", "N/A")}

    Primary System: {system.get("primarySystem", "N/A")}
    Application Type: {system.get("applicationType", "N/A")}
    Environment: {system.get("environment", "N/A")}
    Supporting Systems: {safe_join(system.get("supportingSystems", []))}

    Frameworks: {safe_join(audit.get("frameworks", []))}
    Audit Year: {audit.get("auditYear", "N/A")}
    Audit Period: {audit.get("auditPeriod", "N/A")}
    Source Type: {audit.get("sourceType", "N/A")}

    Control Design:
    {design.get("designUnderstanding", "N/A")}

    Design Attributes:
    {safe_join(design.get("designAttributes", []))}

    Test Steps:
    {safe_join(testing.get("testSteps", []))}

    Testing Performed:
    {testing.get("testingPerformedNarrative", "N/A")}

    Sampled Items:
    {safe_join(testing.get("sampledItems", []))}

    Actual Evidence:
    {safe_join(evidence.get("actualEvidenceInspected", []))}

    Expected Evidence:
    {safe_join(evidence.get("expectedEvidence", []))}

    Risk Statement:
    {risk.get("riskStatement", "N/A")}

    Risk Category:
    {risk.get("riskCategory", "N/A")}

    Inherent Risk Rating:
    {risk.get("inherentRiskRating", "N/A")}

    Potential Missing Evidence:
    {safe_join(gaps.get("potentialMissingEvidence", []))}

    Control Gaps:
    {safe_join(gaps.get("controlGaps", []))}

    Recommended Remediation:
    {safe_join(gaps.get("recommendedRemediation", []))}

    Completeness Assessment:
    {gaps.get("completenessAssessment", "N/A")}

    Retrieval Tags:
    {safe_join(retrieval.get("retrievalTags", []))}

    Search Keywords:
    {safe_join(retrieval.get("searchKeywords", []))}

    Audit Conclusion:
    {conclusion.get("conclusionNarrative", "N/A")}

    Operating Effectively:
    {conclusion.get("operatingEffectively", "N/A")}
    """

    embedding = model.encode(text).tolist()

    collection.add(
        documents=[text],
        embeddings=[embedding],
        ids=[wp.get("workpaperId")],
        metadatas=[{
            "workpaper_id": wp.get("workpaperId", "N/A"),
            "control_id": control.get("controlId", "N/A"),
            "control_name": control.get("controlName", "N/A"),
            "domain": control.get("domain", "N/A"),
            "sub_domain": control.get("subDomain", "N/A"),
            "risk_rating": risk.get("inherentRiskRating", "N/A"),
            "risk_category": risk.get("riskCategory", "N/A"),
            "audit_year": audit.get("auditYear", "N/A"),
            "frameworks": safe_join(audit.get("frameworks", [])),
            "operating_effectively": str(conclusion.get("operatingEffectively", "N/A")),
            "source_document": wp.get("sourceDocument", "N/A")
        }]
    )

print(f"Stored {len(workpapers)} workpapers successfully.")