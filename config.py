"""Central configuration: loads .env and exposes typed constants.

This module explicitly searches for a .env file in the repository root and in
the `audit_poc/` subdirectory so environment loading works regardless of the
current working directory used when launching Streamlit.
"""

import logging
import os
from pathlib import Path

from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Candidate locations to look for a .env file (repo root, audit_poc/.env)
_HERE = Path(__file__).resolve().parent
_CANDIDATES = [_HERE / ".env", _HERE / "audit_poc" / ".env"]

loaded = False
for _p in _CANDIDATES:
    if _p.exists():
        load_dotenv(dotenv_path=str(_p))
        logger.debug("Loaded environment from %s", _p)
        loaded = True
        break

# Fallback to default behaviour (searching parent dirs / cwd)
if not loaded:
    load_dotenv()

def _get_streamlit_secret(name: str) -> str | None:
    try:
        import streamlit as st  # noqa: PLC0415

        return st.secrets.get(name)
    except Exception:
        return None


MISTRAL_API_KEY: str | None = os.getenv("MISTRAL_API_KEY") or _get_streamlit_secret("MISTRAL_API_KEY")
CHROMA_API_KEY: str | None = os.getenv("CHROMA_API_KEY") or _get_streamlit_secret("CHROMA_API_KEY")
CHROMA_TENANT: str | None = os.getenv("CHROMA_TENANT") or _get_streamlit_secret("CHROMA_TENANT")
CHROMA_DATABASE: str | None = os.getenv("CHROMA_DATABASE") or _get_streamlit_secret("CHROMA_DATABASE")
CHROMA_HOST: str | None = os.getenv("CHROMA_HOST") or _get_streamlit_secret("CHROMA_HOST")

if MISTRAL_API_KEY is None:
    logger.warning("MISTRAL_API_KEY is not set — LLM calls will use mock responses")

USE_CHROMA_CLOUD = bool(CHROMA_API_KEY and CHROMA_TENANT and CHROMA_DATABASE)

if not USE_CHROMA_CLOUD:
    logger.warning("Chroma Cloud secrets are not set — using local Chroma persistence")
