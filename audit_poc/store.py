import chromadb
from sentence_transformers import SentenceTransformer
import json
import os

# Connect to ChromaDB
client = chromadb.PersistentClient(path="./chroma_db")

# Create/Get collection
collection = client.get_or_create_collection(
    name="audit_collection"
)

# Embedding model
model = SentenceTransformer("all-MiniLM-L6-v2")

# Folder containing JSON files
DATA_FOLDER = "./data"

# Read all JSON files
for file in os.listdir(DATA_FOLDER):

    if file.endswith(".json"):

        filepath = os.path.join(DATA_FOLDER, file)

        with open(filepath, "r") as f:
            data = json.load(f)

        # Convert JSON into AI-readable text
        text = f"""
        System Information:
        OS: {data['system'].get('os', 'N/A')}
        Database: {data['system'].get('database', 'N/A')}
        Application Type: {data['system'].get('applicationType', 'N/A')}

        Control Information:
        Control Type: {data['control'].get('type', 'N/A')}
        Sub Type: {data['control'].get('subType', 'N/A')}
        Objective: {data['control'].get('objective', 'N/A')}

        Control Design:
        Description: {data['controlDesign'].get('description', 'N/A')}
        Frequency: {data['controlDesign'].get('frequency', 'N/A')}
        Owner: {data['controlDesign'].get('owner', 'N/A')}

        Test Steps:
        {' '.join(data['testArtifact'].get('testSteps', []))}

        Evidence Required:
        {' '.join(data['testArtifact'].get('evidenceRequired', []))}

        Evidence Tested:
        {' '.join(data['evidenceTested'].get('testingPerformed', []))}

        Result:
        {data['evidenceTested'].get('result', 'N/A')}

        Risk:
        Statement: {data['risk'].get('statement', 'N/A')}
        Category: {data['risk'].get('category', 'N/A')}

        Audit Context:
        Industry: {data['auditContext'].get('industry', 'N/A')}
        Framework: {' '.join(data['auditContext'].get('framework', []))}
        Year: {data['auditContext'].get('year', 'N/A')}

        Quality Signals:
        Review Status: {data['qualitySignals'].get('reviewStatus', 'N/A')}
        Usage Count: {data['qualitySignals'].get('usageCount', 'N/A')}
        """

        # Generate embedding
        embedding = model.encode(text).tolist()

        # Store in ChromaDB
        collection.add(
            documents=[text],
            embeddings=[embedding],
            ids=[data["id"]],
            metadatas=[{
                "control_type": data["control"].get("type", "N/A"),
                "framework": str(data["auditContext"].get("framework", [])),
                "year": data["auditContext"].get("year", "N/A")
            }]
        )

print("All workpapers stored successfully!")