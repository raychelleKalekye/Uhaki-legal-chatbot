from sentence_transformers import SentenceTransformer
import chromadb

model = SentenceTransformer("../models/legal-bert-base-uncased")

client = chromadb.PersistentClient(path="chroma_db")
collection = client.get_collection(name="LegalActs")

query = "What does the Constitution say about freedom of expression?"
results = collection.query(
    query_embeddings=[model.encode([query])[0].tolist()],
    n_results=3  
)

print("Query results:")
for doc in results["documents"][0]:
    print(doc, "\n---\n")
