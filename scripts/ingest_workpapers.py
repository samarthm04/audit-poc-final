"""Ingest workpapers from data/workpapers.json into ChromaDB collection 'audit_workpapers'."""

import argparse
import json
import logging
import os
import sys
from pathlib import Path

import chromadb

logging.basicConfig(level=logging.INFO, format="%(levelname)s  %(message)s")
logger = logging.getLogger(__name__)

_CHROMA_PATH = "./chroma_db"
_COLLECTION_NAME = "audit_workpapers"
_DATA_FILE = Path(__file__).resolve().parent.parent / "data" / "workpapers.json"


def _build_document(wp: dict) -> str:
    """Create the searchable document string from a workpaper record."""
    control = wp.get("control", {})
    design = control.get("controlDesign", {})
    artifact = wp.get("testArtifact", {})
    steps = " ".join(artifact.get("testSteps", []))
    return (
        f"{control.get('type', '')} "
        f"{control.get('subType', '')} "
        f"{design.get('description', '')} "
        f"{steps}"
    )


def _build_metadata(wp: dict) -> dict:
    """Extract flat metadata dict suitable for ChromaDB storage and filtering."""
    system = wp.get("system", {})
    control = wp.get("control", {})
    audit_ctx = wp.get("auditContext", {})
    quality = wp.get("qualitySignals", {})
    frameworks = audit_ctx.get("framework", [])
    return {
        "id": wp["id"],
        "os": system.get("os", ""),
        "database": system.get("database", ""),
        "applicationType": system.get("applicationType", ""),
        "control_type": control.get("type", ""),
        "control_subtype": control.get("subType", ""),
        "industry": audit_ctx.get("industry", ""),
        "framework": ", ".join(frameworks) if isinstance(frameworks, list) else str(frameworks),
        "reviewStatus": quality.get("reviewStatus", ""),
        "usageCount": quality.get("usageCount", 0),
    }


def ingest(reset: bool = False, data_file: Path = _DATA_FILE) -> None:
    """Read workpapers.json and ingest all records into the ChromaDB collection."""
    if not data_file.exists():
        logger.error("Data file not found: %s", data_file)
        sys.exit(1)

    with open(data_file, encoding="utf-8") as f:
        workpapers: list[dict] = json.load(f)
    logger.info("Loaded %d workpapers from %s", len(workpapers), data_file)

    os.makedirs(_CHROMA_PATH, exist_ok=True)
    client = chromadb.PersistentClient(path=_CHROMA_PATH)

    if reset:
        try:
            client.delete_collection(_COLLECTION_NAME)
            logger.info("Deleted existing collection '%s'", _COLLECTION_NAME)
        except Exception:
            pass

    collection = client.get_or_create_collection(_COLLECTION_NAME)

    if not reset and collection.count() > 0:
        print(
            f"Collection already populated ({collection.count()} documents). "
            "Run with --reset to re-ingest."
        )
        return

    ids = [wp["id"] for wp in workpapers]
    documents = [_build_document(wp) for wp in workpapers]
    metadatas = [_build_metadata(wp) for wp in workpapers]

    collection.add(ids=ids, documents=documents, metadatas=metadatas)
    logger.info("Ingested %d workpapers into '%s'", len(workpapers), _COLLECTION_NAME)
    print(f"Done — ingested {len(workpapers)} workpapers into collection '{_COLLECTION_NAME}'.")


def main() -> None:
    """Parse CLI arguments and run the ingestion pipeline."""
    parser = argparse.ArgumentParser(description="Ingest workpapers into ChromaDB.")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete and recreate the collection before ingesting.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=_DATA_FILE,
        help="Path to a workpaper JSON file to ingest.",
    )
    args = parser.parse_args()
    ingest(reset=args.reset, data_file=args.file)


if __name__ == "__main__":
    main()
