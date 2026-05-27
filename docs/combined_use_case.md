# Combined Use Case: Audit Workpaper Intelligence Assistant

## Objective

Build one Streamlit application that combines the strongest local backend components with the strongest remote user-facing and data components.

The final product should let an auditor:

1. Ask an audit question in plain English.
2. Retrieve relevant historical workpapers from ChromaDB.
3. Run the local Mistral-backed LLM reasoning flow.
4. View structured output: present steps, missing steps, evidence gaps, and augmented procedures.
5. Upload new JSON or DOCX workpapers.
6. Diagnose uploaded workpapers for completeness.
7. Compare new workpapers against historical examples and generate remediation recommendations.

## Components To Keep

### Local Components

Use these as the core backend implementation:

- `agents/llm_agent.py`
  - Keep the Mistral integration.
  - Keep the deterministic mock output when `MISTRAL_API_KEY` is missing.
  - Keep request parsing and explicit auth failure handling.

- `agents/reasoning_agent.py`
  - Keep the senior IT auditor prompt.
  - Keep the required four-section output:
    - `PRESENT STEPS`
    - `MISSING STEPS`
    - `EVIDENCE GAPS`
    - `AUGMENTED PROCEDURE`

- `agents/retrieval_agent.py`
  - Keep metadata filter detection for OS, database, control type, and control subtype.
  - Keep ChromaDB collection name `audit_workpapers`.
  - Keep fallback behavior when filters fail or the collection is empty.

- `agents/supervisor_agent.py`
  - Keep query validation and orchestration.

- `config.py`
  - Keep centralized `.env` loading from both root and `audit_poc/.env`.

- `scripts/ingest_workpapers.py`
  - Keep CLI ingestion and `--reset` support.

- `tests/`
  - Keep tests around LLM behavior and retrieval metadata filters.

### Remote Components

Use these as product and data features:

- `audit_poc/app.py` from `origin/main`
  - Keep the richer Streamlit frontend concepts:
    - dashboard metrics
    - previous query history
    - summarized versus full output toggle
    - upload workflow for JSON and DOCX
    - clean response tabs
    - completeness score

- `audit_poc/data/project_ready_workpaper_dataset.json`
  - Keep as the richer historical workpaper dataset.
  - Convert or ingest into the local `audit_workpapers` ChromaDB schema.

- Remote workpaper diagnosis logic
  - Keep keyword-based completeness detection.
  - Keep missing-section checks.
  - Keep recommendation generation as a non-LLM fallback.

## Target User Story

As an IT auditor, I want to ask a question like:

> Review change management controls for Windows SQL Server emergency changes and identify missing evidence.

The application should:

1. Detect metadata filters:
   - `os = Windows`
   - `database = SQL Server`
   - `control_type = Change Management`

2. Retrieve matching workpapers from ChromaDB.

3. Send the query and retrieved excerpts to Mistral through `agents/llm_agent.py`.

4. Return the local structured LLM output:
   - present test steps found in the workpapers
   - missing expected test steps
   - evidence gaps
   - augmented recommended procedure

5. Render the result in the richer remote UI:
   - dashboard metrics at the top
   - retrieved workpapers in an expander
   - tabs for summary, gaps, recommendations, and full output
   - previous queries below the main output

6. Allow the auditor to upload a new workpaper and run a completeness diagnosis against the same control expectations.

## Target Architecture

```text
Streamlit UI
  app.py
    |
    |-- Query workflow
    |     |
    |     |-- agents.supervisor_agent.handle_query(query)
    |           |
    |           |-- agents.retrieval_agent.retrieve_documents(query)
    |           |-- agents.reasoning_agent.analyze_documents(query)
    |                 |
    |                 |-- agents.llm_agent.ask_llm(prompt)
    |
    |-- Upload workflow
    |     |
    |     |-- parse JSON or DOCX
    |     |-- normalize to canonical workpaper schema
    |     |-- upsert into ChromaDB collection audit_workpapers
    |     |-- run completeness diagnosis
    |
    |-- Data ingestion workflow
          |
          |-- scripts/ingest_workpapers.py --reset
          |-- ingest data/workpapers.json or converted remote dataset
```

## Canonical Data Schema

Use the local `data/workpapers.json` shape as the canonical schema because it matches the local ingestion and retrieval agents.

Required fields:

- `id`
- `system.os`
- `system.database`
- `system.applicationType`
- `control.type`
- `control.subType`
- `control.objective`
- `control.controlDesign.description`
- `testArtifact.testSteps`
- `testArtifact.evidenceRequired`
- `risk.statement`
- `risk.category`
- `auditContext.framework`
- `qualitySignals.reviewStatus`

Remote dataset fields should be mapped into this schema before ingestion.

Example mapping:

```text
remote.workpaperId -> local.id
remote.systemContext.primarySystem -> local.system.applicationType
remote.control.controlName/domain -> local.control.type
remote.control.subDomain -> local.control.subType
remote.control.objective -> local.control.objective
remote.controlDesign.designUnderstanding -> local.control.controlDesign.description
remote.testing.testSteps -> local.testArtifact.testSteps
remote.evidence.expectedEvidence -> local.testArtifact.evidenceRequired
remote.risk.riskStatement -> local.risk.statement
remote.risk.riskCategory -> local.risk.category
remote.auditMetadata.frameworks -> local.auditContext.framework
remote.auditConclusion.reviewStatus -> local.qualitySignals.reviewStatus
```

## Output Contract

The backend should always return a dictionary:

```python
{
    "query": str,
    "documents": list[dict],
    "analysis": str,
    "error": str | None,
}
```

The `analysis` field should preserve the local four-section LLM format. The UI can parse it into tabs, but the raw output should remain available.

## Combined UI Design

Use one root-level `app.py`.

Main sections:

1. **Audit Overview**
   - Queries run
   - Workpapers in ChromaDB
   - Uploaded files
   - Last retrieved count

2. **Ask an Audit Question**
   - Text area
   - Run Analysis button
   - Summarized response toggle
   - Detected metadata filters in sidebar

3. **Retrieved Workpapers**
   - Workpaper ID
   - OS, database, control type, control subtype
   - Short excerpt
   - Distance score where available

4. **LLM Audit Analysis**
   - Summary tab
   - Present Steps tab
   - Missing Steps tab
   - Evidence Gaps tab
   - Augmented Procedure tab
   - Raw Output tab

5. **Upload Workpaper**
   - JSON upload
   - DOCX upload
   - Store in ChromaDB
   - Completeness score
   - Missing fields
   - Recommended remediation

6. **Previous Queries**
   - Most recent query first

## Implementation Plan

1. Keep the root-level project layout as the final application layout.

2. Move useful frontend functions from remote `audit_poc/app.py` into root `app.py`:
   - upload parsing
   - completeness scoring
   - response tabs
   - previous query state
   - dashboard metrics

3. Do not use the remote backend as the main backend.
   - Replace remote `handle_query(query)` tuple expectations with local `handle_query(query)` dictionary output.
   - Replace remote `audit_collection` collection name with local `audit_workpapers`.

4. Add a conversion script:
   - `scripts/convert_remote_workpapers.py`
   - Input: `audit_poc/data/project_ready_workpaper_dataset.json`
   - Output: `data/workpapers_remote_converted.json` or merge into `data/workpapers.json`.

5. Update `scripts/ingest_workpapers.py` to optionally accept a file path:
   - default remains `data/workpapers.json`
   - optional `--file data/workpapers_remote_converted.json`

6. Add tests for:
   - remote-to-local dataset conversion
   - four-section output parsing
   - upload JSON normalization
   - completeness scoring

## Definition Of Done

The combined application is ready when:

- `streamlit run app.py` starts from the repo root.
- `python scripts/ingest_workpapers.py --reset` loads workpapers into `audit_workpapers`.
- Query results use the local Mistral implementation.
- The UI displays remote-style metrics, tabs, upload, and history.
- Uploaded JSON/DOCX workpapers can be diagnosed and stored.
- Tests pass with `pytest`.

