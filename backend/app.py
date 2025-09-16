import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from sentence_transformers import SentenceTransformer
import chromadb

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

model_path = os.path.abspath(r"../data/models/roberta_classifier_retrained")
tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
model = AutoModelForSequenceClassification.from_pretrained(model_path, local_files_only=True)
classifier = pipeline("text-classification", model=model, tokenizer=tokenizer)

embedder = SentenceTransformer(r"../data/models/legal-bert-base-uncased")

client = chromadb.PersistentClient(path="../data/scripts/chroma_db")
collection = client.get_collection(name="LegalActs")

def retrieve_from_chroma(query: str, act: str, top_k: int = 3):
    """Query ChromaDB for top matching chunks."""
    retrieved_chunks = []
    try:
        query_embedding = embedder.encode([query]).tolist()[0]

        search_results = collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where={"act": act}
        )

        if search_results and "documents" in search_results:
            for i, doc in enumerate(search_results["documents"][0]):
                chunk = {
                    "rank": i + 1,
                    "text": doc,
                    "metadata": search_results["metadatas"][0][i]
                }
                retrieved_chunks.append(chunk)

    except Exception as e:
        logging.error(f"[RETRIEVE-FUNC] ChromaDB error: {e}")

    return retrieved_chunks

@app.route('/')
def home():
    return "Uhaki backend is running!"

@app.route('/askQuery', methods=['POST'])
def ask_query():
    data = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({"error": "No query provided"}), 400

    result = classifier(query)[0]
    predicted_act = result['label']
    confidence = float(result['score'])

    retrieved_chunks = retrieve_from_chroma(query, predicted_act, top_k=3)

    # Log everything including full chunks
    logging.info(
        f'Query: "{query}" | Predicted Act: "{predicted_act}" | '
        f'Confidence: {confidence:.2f} | Retrieved {len(retrieved_chunks)} chunks'
    )
    for chunk in retrieved_chunks:
        logging.info(
            f'[CHUNK] Rank: {chunk["rank"]} | Metadata: {chunk["metadata"]} | '
            f'Text: {chunk["text"][:300]}{"..." if len(chunk["text"]) > 300 else ""}'
        )

    return jsonify({
        "query": query,
        "predicted_act": predicted_act,
        "confidence": round(confidence, 2),
        "top_results": retrieved_chunks
    })

@app.route('/retrieve', methods=['POST'])
def retrieve_texts():
    data = request.get_json()
    query = data.get('query', '').strip()
    act = data.get('act', '').strip()
    if not query or not act:
        return jsonify({"error": "Both query and act are required"}), 400

    retrieved_chunks = retrieve_from_chroma(query, act, top_k=3)

    # Log everything including full chunks
    logging.info(
        f'[RETRIEVE] Query: "{query}" | Act: "{act}" | Retrieved {len(retrieved_chunks)} chunks'
    )
    for chunk in retrieved_chunks:
        logging.info(
            f'[CHUNK] Rank: {chunk["rank"]} | Metadata: {chunk["metadata"]} | '
            f'Text: {chunk["text"][:300]}{"..." if len(chunk["text"]) > 300 else ""}'
        )

    return jsonify({
        "query": query,
        "act": act,
        "top_results": retrieved_chunks
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
