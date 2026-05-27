# audit-PoC — IT Audit Reasoning Assistant

LLM-powered audit workpaper analysis tool using Mistral, ChromaDB, and Streamlit.

## Setup

### 1. Create and activate a virtual environment

```bash
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt
```

### 2. Configure your API key

```bash
cp .env.example .env
# Open .env and replace the placeholder with your real Mistral API key
```

> **Warning:** Never commit `.env` to version control. If you accidentally commit your key, treat it as compromised and rotate it immediately (see Key Rotation below).

### 3. Ingest workpapers into ChromaDB

```bash
python scripts/ingest_workpapers.py
```

To reset and re-ingest:

```bash
python scripts/ingest_workpapers.py --reset
```

## Running the app

```bash
streamlit run app.py
```

## Streamlit Community Cloud deployment

Deploy from:

- Repository: `samarthm04/audit-poc-final`
- Branch: `main`
- Main file path: `app.py`

Add this in Streamlit app secrets:

```toml
MISTRAL_API_KEY = "your-real-mistral-key"

# Optional but recommended for permanent uploaded-workpaper retention.
# Without these, Streamlit Cloud uses local app storage, which can reset.
CHROMA_API_KEY = "your-chroma-cloud-api-key"
CHROMA_TENANT = "your-chroma-tenant"
CHROMA_DATABASE = "your-chroma-database"
# CHROMA_HOST = "europe-west1.gcp.trychroma.com" # Only for non-default region
```

The deployed app seeds ChromaDB from `data/workpapers_remote_converted.json` on first startup, so no checked-in `chroma_db/` folder is required. When Chroma Cloud secrets are configured, uploaded workpapers are retained in Chroma Cloud across app restarts and redeploys.

## Running tests

```bash
pytest
```

## Key rotation — removing a committed secret from git history

If `MISTRAL_API_KEY` was accidentally committed:

1. **Revoke the key immediately** in the Mistral console before anything else.
2. Remove the secret from history using `git filter-repo`:

   ```bash
   pip install git-filter-repo
   git filter-repo --replace-text <(echo "YOUR_LEAKED_KEY==>REDACTED")
   ```

3. Force-push all branches:

   ```bash
   git push origin --force --all
   git push origin --force --tags
   ```

4. Notify all collaborators to re-clone — local clones still contain the old history.
5. Ask GitHub support to purge cached views of the old commits.
6. Generate a fresh key and add it to `.env`.
