from sentence_transformers import CrossEncoder

LOCAL_PATH = r"D:\Users\user\github-classroom\is-project-4th-year\GRP-B-ISP-raychelleKalekye\data\models\ms-marco-MiniLM-L-6-v2"
try:
    reranker_model = CrossEncoder(LOCAL_PATH, local_files_only=True)
except Exception:
   
    reranker_model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

def rerank_results(query: str, chunks: list):
    """
    chunks: list of dicts with at least {"text": str}
    Adds 'rerank_score' in-place and returns a sorted copy.
    """
    if not chunks:
        return chunks
    pairs = [(query, c["text"]) for c in chunks]
    scores = reranker_model.predict(pairs)
    for c, s in zip(chunks, scores):
        c["rerank_score"] = float(s)
    return sorted(chunks, key=lambda x: x.get("rerank_score", 0.0), reverse=True)
