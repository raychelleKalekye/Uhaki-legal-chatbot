import os
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
from sentence_transformers import SentenceTransformer
import chromadb
import sys
import pandas as pd

csv_file = os.path.abspath("../outputs/queryLog.csv")
responses_file = os.path.abspath("../outputs/responses.csv")

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../data/scripts")))
from reranker import rerank_results

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

def retrieve_from_chroma(query: str, act: str = None, top_k: int = 3):
    """Query ChromaDB for top matching chunks, optionally filtered by Act."""
    retrieved_chunks = []
    try:
        query_embedding = embedder.encode([query]).tolist()[0]

        search_kwargs = {"n_results": top_k, "query_embeddings": [query_embedding]}
        if act:  # only filter if act is provided
            search_kwargs["where"] = {"act": act}

        search_results = collection.query(**search_kwargs)

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

def build_hybrid_answer(query, retrieved_chunks):
    """Build hybrid legal chatbot response: summarize + reference."""
    if not retrieved_chunks:
        return "Sorry, I couldn’t find any relevant law for your question."

    best_chunk = retrieved_chunks[0]
    text = best_chunk["text"]
    act = best_chunk.get("metadata", {}).get("act", "Unknown Act")
    section = best_chunk.get("metadata", {}).get("section", "")


    summary = text.split(".")[0].strip()

    response = f"{summary}."
    if act != "Unknown Act":
        response += f" This is provided under the {act}"
        if section:
            response += f", Section {section}"
        response += "."

    return response


@app.route('/askQuery', methods=['POST'])
def ask_query():
    data = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({"error": "No query provided"}), 400

    
    result = classifier(query)[0]
    predicted_act = result['label']
    confidence = float(result['score'])

    
    if confidence >= 0.6:
        retrieved_chunks = retrieve_from_chroma(query, predicted_act, top_k=10)
        logging.info(
            f'High confidence ({confidence:.2f}). Restricting retrieval to "{predicted_act}".'
        )
    else:
        retrieved_chunks = retrieve_from_chroma(query, act=None, top_k=10)
        logging.info(
            f'Low confidence ({confidence:.2f}). Expanding retrieval across ALL Acts.'
        )


    reranked_chunks = rerank_results(query, retrieved_chunks)

    logging.info(
        f'Query: "{query}" | Predicted Act: "{predicted_act}" | '
        f'Confidence: {confidence:.2f} | Retrieved {len(reranked_chunks)} chunks'
    )
    for chunk in reranked_chunks:
        logging.info(
            f'[CHUNK] Rerank Score: {chunk.get("rerank_score", 0):.4f} | '
            f'Metadata: {chunk["metadata"]} | '
            f'Text: {chunk["text"][:300]}{"..." if len(chunk["text"]) > 300 else ""}'
        )

    top_chunk_text = reranked_chunks[0]["text"] if reranked_chunks else ""
    top_chunk_section = reranked_chunks[0]["metadata"].get("section", "") if reranked_chunks else ""

    entry = pd.DataFrame({
        "Query": [query],
        "Predicted_Act": [predicted_act],
        "Confidence": [confidence],
        "Top_Chunk_Text": [top_chunk_text],
        "Top_Chunk_Section": [top_chunk_section]
    })

    if os.path.exists(csv_file):
        entry.to_csv(csv_file, mode='a', index=False, header=False)
    else:
        entry.to_csv(csv_file, mode='w', index=False, header=True)

        
    hybrid_answer = build_hybrid_answer(query, reranked_chunks)

    
    logging.info(f'[ANSWER] {hybrid_answer}')

   
    qa_entry = pd.DataFrame({
        "Query": [query],
        "Answer": [hybrid_answer]
    })

    if os.path.exists(responses_file):
        qa_entry.to_csv(responses_file, mode='a', index=False, header=False)
    else:
        qa_entry.to_csv(responses_file, mode='w', index=False, header=True)

    return jsonify({
        "query": query,
        "predicted_act": predicted_act,
        "confidence": round(confidence, 2),
        "answer": hybrid_answer,
        "top_results": reranked_chunks
    })


if __name__ == '__main__':
    app.run(debug=True, port=5000)
