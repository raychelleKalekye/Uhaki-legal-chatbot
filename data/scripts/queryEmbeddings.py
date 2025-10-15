from sentence_transformers import SentenceTransformer
import chromadb
import numpy as np

MODEL_NAME = "intfloat/e5-base-v2"
COLLECTION_NAME = "actSectionsV2"

model = SentenceTransformer(MODEL_NAME)
model.max_seq_length = 512

client = chromadb.PersistentClient(path="./chroma")   
collection = client.get_collection(name=COLLECTION_NAME)

query_text = "What are the rules on termination of employment under the Employment Act of Kenya?"

query_emb = model.encode("query: " + query_text, normalize_embeddings=True)

results = collection.query(
    query_embeddings=[query_emb.tolist()],
    n_results=3
)

print("\n Query Results:")
for i, (doc, meta) in enumerate(zip(results["documents"][0], results["metadatas"][0]), start=1):
    print(f"\nResult {i}:")
    print(f"Act: {meta.get('act')}")
    print(f"Section: {meta.get('section')}")
    print(f"Text:\n{doc[:500]}...")  
    print("-" * 80)
