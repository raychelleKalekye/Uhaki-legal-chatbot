import os
import glob
import uuid
import json
import re
from sentence_transformers import SentenceTransformer
import chromadb

model = SentenceTransformer("../models/legal-bert-base-uncased")

client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_or_create_collection(name="LegalActs")

chunk_folder = "../ActsinChunks"
chunk_files = glob.glob(os.path.join(chunk_folder, "*.json"))

def split_into_sentences(text, max_sentences=3):
    sentences = re.split(r'(?<=[.!?])\s+', text)
    chunks = []
    for i in range(0, len(sentences), max_sentences):
        chunk_text = ' '.join(sentences[i:i+max_sentences])
        chunks.append(chunk_text)
    return chunks


for file_path in chunk_files:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for chunk in data:
        content = chunk["content"].strip()
        if not content:
            continue

        
        small_chunks = split_into_sentences(content, max_sentences=3)

        for small_chunk in small_chunks:
            embedding = model.encode([small_chunk])[0].tolist()
            chunk_id = str(uuid.uuid4())

            collection.add(
                documents=[small_chunk],
                embeddings=[embedding],
                ids=[chunk_id],
                metadatas=[{
                    "act": chunk.get("act"),
                    "part": chunk.get("part"),
                    "section": chunk.get("section"),
                    "source_file": os.path.basename(file_path)
                }]
            )

            
            print("Embedded chunk preview:", small_chunk[:100])

print("All chunks embedded into ChromaDB")
