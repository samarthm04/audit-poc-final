"""Convert the remote project-ready workpaper dataset into the local schema."""

import argparse
import json
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "remote" / "project_ready_workpaper_dataset.json"
DEFAULT_OUTPUT = ROOT / "data" / "workpapers_remote_converted.json"


def _infer_os(system_context: dict[str, Any], text: str) -> str:
    joined = " ".join(
        [
            str(system_context.get("primarySystem", "")),
            " ".join(system_context.get("supportingSystems", []) or []),
            text,
        ]
    ).lower()
    if "windows" in joined or "active directory" in joined or "microsoft" in joined:
        return "Windows"
    if "linux" in joined:
        return "Linux"
    return "N/A"


def _infer_database(text: str) -> str:
    lower = text.lower()
    if "sql server" in lower or "sql" in lower:
        return "SQL Server"
    if "oracle" in lower:
        return "Oracle"
    return "N/A"


def _infer_control_type(control: dict[str, Any]) -> str:
    domain = f"{control.get('domain', '')} {control.get('controlName', '')}".lower()
    if "change" in domain:
        return "Change Management"
    if "password" in domain:
        return "Password Policy"
    if "access" in domain or "identity" in domain:
        return "Access Management"
    return control.get("domain") or control.get("controlName") or "N/A"


def convert_record(record: dict[str, Any]) -> dict[str, Any]:
    """Map one remote workpaper record into the local canonical shape."""
    control = record.get("control", {})
    system_context = record.get("systemContext", {})
    testing = record.get("testing", {})
    evidence = record.get("evidence", {})
    risk = record.get("risk", {})
    audit_meta = record.get("auditMetadata", {})
    conclusion = record.get("auditConclusion", {})
    design = record.get("controlDesign", {})
    searchable_text = json.dumps(record, ensure_ascii=True)

    return {
        "id": record.get("workpaperId") or record.get("id") or "REMOTE-WP",
        "system": {
            "os": _infer_os(system_context, searchable_text),
            "database": _infer_database(searchable_text),
            "applicationType": system_context.get("applicationType")
            or system_context.get("primarySystem")
            or "N/A",
        },
        "control": {
            "type": _infer_control_type(control),
            "subType": control.get("subDomain") or control.get("controlName") or "N/A",
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
        "qualitySignals": {
            "reviewStatus": conclusion.get("reviewStatus", "N/A"),
            "usageCount": 0,
        },
    }


def convert_file(input_path: Path, output_path: Path) -> int:
    with open(input_path, encoding="utf-8") as f:
        records = json.load(f)

    converted = [convert_record(record) for record in records]
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(converted, f, indent=2)
        f.write("\n")

    return len(converted)


def main() -> None:
    parser = argparse.ArgumentParser(description="Convert remote workpapers into local schema.")
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    count = convert_file(args.input, args.output)
    print(f"Converted {count} workpapers to {args.output}")


if __name__ == "__main__":
    main()
