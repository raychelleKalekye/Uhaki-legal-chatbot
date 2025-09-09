import os
import glob
import uuid
import json
from sentence_transformers import SentenceTransformer
import chromadb

# Load model
model = SentenceTransformer("../models/legal-bert-base-uncased")

# Connect to Chroma
client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection(name="LegalActs")

# Folder containing chunked JSON files
chunk_folder = "../ActsinChunks"
chunk_files = glob.glob(os.path.join(chunk_folder, "*.json"))

# Batch size for embedding
BATCH_SIZE = 16  

for file_idx, file_path in enumerate(chunk_files, start=1):
    act_name = os.path.splitext(os.path.basename(file_path))[0]
    print(f"Embedding chunks from [{file_idx}/{len(chunk_files)}] {act_name}...")

    # Load chunks
    with open(file_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    # Process in batches
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        texts = [chunk["text"] for chunk in batch]

        # Generate embeddings
        embeddings = model.encode(texts).tolist()

        # Prepare metadata and IDs
        metadatas = [
            {
                "act": chunk.get("act", ""),
                "section": chunk.get("section", "")
            }
            for chunk in batch
        ]
        ids = [str(uuid.uuid4()) for _ in batch]

        # Add to Chroma
        collection.add(
            documents=texts,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )

    print(f" → Completed embedding {len(chunks)} chunks for {act_name}.")

print(" All chunks embedded into ChromaDB.")
