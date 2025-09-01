import os
from sentence_transformers import SentenceTransformer
import chromadb
from huggingface_hub import snapshot_download

local_model_path = "../models/legal-bert-base-uncased"
if not os.path.exists(local_model_path):
    print("Downloading LegalBERT model into:", local_model_path)
    snapshot_download(
        repo_id="nlpaueb/legal-bert-base-uncased",
        local_dir=local_model_path,
        local_dir_use_symlinks=False
    )

model = SentenceTransformer(local_model_path)
print(" Loaded LegalBERT from:", local_model_path)


client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection(name="LegalActs")
print(" ChromaDB is ready")
