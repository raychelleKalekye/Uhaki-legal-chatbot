import os, logging, json, time
from typing import List, Dict, Any, Optional
from flask import Flask, request, jsonify
from flask_cors import CORS
from sentence_transformers import SentenceTransformer
import chromadb
import pandas as pd

CHROMA_PATH      = os.getenv("CHROMA_PATH", "../data/scripts/chroma")
COLLECTION_NAME  = os.getenv("COLLECTION_NAME", "actSectionsV2")
MODEL_NAME       = os.getenv("HF_MODEL", "intfloat/e5-base-v2")
TOP_K_RETRIEVE   = int(os.getenv("TOP_K_RETRIEVE", "12"))
TOP_K_RETURN     = int(os.getenv("TOP_K_RETURN", "5"))
USE_RERANKER     = os.getenv("USE_RERANKER", "1") == "1"
CSV_LOG          = os.path.abspath(os.getenv("CSV_LOG", "../outputs/newqueryLog.csv"))

app = Flask(__name__)
CORS(app)

logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

embedder = SentenceTransformer(MODEL_NAME)
embedder.max_seq_length = 512

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(name=COLLECTION_NAME)

reranker = None
if USE_RERANKER:
    try:
        from reranker import rerank_results  # must accept (query, chunks) and return same shape
        reranker = rerank_results
        logging.info("[INIT] Reranker loaded.")
    except Exception as e:
        logging.warning(f"[INIT] Reranker not available: {e}. Continuing without rerank.")
        reranker = None

def embed_query_e5(q: str):
    """E5 requires 'query: ' prefix + normalized embedding."""
    return embedder.encode("query: " + q, normalize_embeddings=True).tolist()

def sanitize_meta(m: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for k, v in (m or {}).items():
        if v is None:
            continue
        if isinstance(v, (bool, int, float, str)):
            out[k] = v
        else:
            out[k] = str(v)
    return out

def retrieve(query: str, act: Optional[str], top_k: int) -> Dict[str, Any]:
    """Returns dict: {'chunks': [...], 'timings': {...}}"""
    t0 = time.perf_counter()

    # Embed
    t1 = time.perf_counter()
    q_emb = embed_query_e5(query)
    t2 = time.perf_counter()

    # Chroma query (remove invalid include 'ids')
    kwargs = {
        "query_embeddings": [q_emb],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"],  # valid include keys
    }
    if act:
        kwargs["where"] = {"act": act}

    try:
        res = collection.query(**kwargs)
    except Exception as e:
        logging.error(f"[RETRIEVE] collection.query failed: {e}")
        raise

    # Extract
    docs  = res.get("documents", [[]])[0]
    metas = [sanitize_meta(m) for m in res.get("metadatas", [[]])[0]]
    dists = res.get("distances", [[]])[0]
    ids   = res.get("ids", [[]])[0]  # IDs are returned automatically; no need to include

    chunks = []
    for i in range(len(docs)):
        dist = dists[i] if i < len(dists) else None
        sim = (1.0 - dist) if (dist is not None) else None
        chunks.append({
            "rank": i + 1,
            "score": round(sim, 4) if sim is not None else None,
            "id": ids[i] if i < len(ids) else None,
            "text": docs[i],
            "metadata": metas[i] if i < len(metas) else {},
        })
    t3 = time.perf_counter()

    timings = {
        "embed_ms": round((t2 - t1) * 1000, 2),
        "query_ms": round((t3 - t2) * 1000, 2),
        "total_ms": round((t3 - t0) * 1000, 2),
        "rerank_ms": 0.0,  # filled later if rerank runs
    }
    return {"chunks": chunks, "timings": timings}

def maybe_rerank(query: str, chunks: List[Dict[str, Any]]) -> (List[Dict[str, Any]], float):
    if reranker and chunks:
        t0 = time.perf_counter()
        try:
            out = reranker(query, chunks)  # should return same item schema
        except Exception as e:
            logging.warning(f"[RERANK] Failed, returning retriever results: {e}")
            return chunks, 0.0
        t1 = time.perf_counter()
        return out, round((t1 - t0) * 1000, 2)
    return chunks, 0.0

def log_to_csv(row: Dict[str, Any]):
    df = pd.DataFrame([row])
    if os.path.exists(CSV_LOG):
        df.to_csv(CSV_LOG, mode="a", index=False, header=False)
    else:
        os.makedirs(os.path.dirname(CSV_LOG), exist_ok=True)
        df.to_csv(CSV_LOG, mode="w", index=False, header=True)

@app.route("/askQuery", methods=["POST"])
def ask_query():
    data = request.get_json(force=True) or {}
    query = (data.get("query") or "").strip()
    act   = (data.get("act") or "").strip() or None

    if not query:
        return jsonify({"error": "No query provided"}), 400

    # Retrieve
    try:
        ret = retrieve(query, act, TOP_K_RETRIEVE)
        retrieved = ret["chunks"]
        timings = ret["timings"]
    except Exception as e:
        return jsonify({"error": f"Retrieval failed: {str(e)}"}), 500

    # (Optional) Rerank
    final, rerank_ms = maybe_rerank(query, retrieved)
    timings["rerank_ms"] = rerank_ms
    timings["total_ms"] = round(timings["total_ms"] + rerank_ms, 2)

    # Prepare top result summary for logs
    top = final[0] if final else {}
    top_meta = top.get("metadata", {}) if top else {}
    log_row = {
        "Query": query,
        "Act_Filter": act or "",
        "Top_Act": top_meta.get("act", ""),
        "Top_Section": top_meta.get("section", ""),
        "Top_Score": top.get("score", ""),
        "Embed_ms": timings["embed_ms"],
        "Query_ms": timings["query_ms"],
        "Rerank_ms": timings["rerank_ms"],
        "Total_ms": timings["total_ms"],
    }
    try:
        log_to_csv(log_row)
    except Exception as e:
        logging.warning(f"[CSV] Failed to log: {e}")

    return jsonify({
        "query": query,
        "act_filter": act,
        "timings": timings,                
        "top_results": final[:TOP_K_RETURN]
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
