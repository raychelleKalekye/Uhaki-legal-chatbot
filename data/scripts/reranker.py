from sentence_transformers import CrossEncoder
from pathlib import Path

local_model_path = Path(r"D:\Users\user\github-classroom\is-project-4th-year\GRP-B-ISP-raychelleKalekye\data\models\ms-marco-MiniLM-L-6-v2")

reranker = CrossEncoder(str(local_model_path), local_files_only=True)

def rerank_results(query: str, chunks: list):
    """
    Rerank retrieved chunks using a cross-encoder.
    Each chunk should be a dict with a "text" field.
    """
    if not chunks:
        return chunks

    pairs = [(query, chunk["text"]) for chunk in chunks]
    scores = reranker.predict(pairs)

    for i, score in enumerate(scores):
        chunks[i]["rerank_score"] = float(score)

    reranked = sorted(chunks, key=lambda x: x["rerank_score"], reverse=True)
    return reranked