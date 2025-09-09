import os
from sentence_transformers import SentenceTransformer
import chromadb
from huggingface_hub import snapshot_download

local_model_path = "../models/legal-bert-base-uncased"

# Download LegalBERT if it doesn't exist or force re-download if corrupted
if not os.path.exists(local_model_path) or not os.listdir(local_model_path):
    print("Downloading LegalBERT model into:", local_model_path)
    snapshot_download(
        repo_id="nlpaueb/legal-bert-base-uncased",
        local_dir=local_model_path,
        local_dir_use_symlinks=False,
        force_download=True
    )

# Load the model
try:
    model = SentenceTransformer(local_model_path)
    print("Loaded LegalBERT from:", local_model_path)
except Exception as e:
    print("Error loading model:", e)
    raise

# Initialize ChromaDB
# client = chromadb.PersistentClient(path="chroma_db")
# collection = client.get_or_create_collection(name="LegalActs")
# print("ChromaDB is ready")
