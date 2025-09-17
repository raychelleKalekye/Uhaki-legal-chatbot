import os
import glob
import uuid
import json
from sentence_transformers import SentenceTransformer
from chromaInit import get_chroma_collection  


model = SentenceTransformer("../models/legal-bert-base-uncased")


collection = get_chroma_collection()


chunk_folder = "../ActsinChunks"
chunk_files = glob.glob(os.path.join(chunk_folder, "*.json"))


BATCH_SIZE = 16  

for file_idx, file_path in enumerate(chunk_files, start=1):
    act_name = os.path.splitext(os.path.basename(file_path))[0]
    print(f"Embedding chunks from [{file_idx}/{len(chunk_files)}] {act_name}...")

  
    with open(file_path, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        texts = [chunk["text"] for chunk in batch]

      
        embeddings = model.encode(texts).tolist()

        
        metadatas = [
            {
                "act": chunk.get("act", ""),
                "section": chunk.get("section", "")
            }
            for chunk in batch
        ]
        ids = [str(uuid.uuid4()) for _ in batch]

        collection.add(
            documents=texts,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )

    print(f" → Completed embedding {len(chunks)} chunks for {act_name}.")

print(" All chunks embedded into ChromaDB.")
