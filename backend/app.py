import os, logging, json, time, uuid
from logging.handlers import RotatingFileHandler
from typing import List, Dict, Any, Optional, Tuple

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer

# =====================
# Config (env overrides)
# =====================
CHROMA_PATH      = os.getenv("CHROMA_PATH", "../data/scripts/chroma")
COLLECTION_NAME  = os.getenv("COLLECTION_NAME", "actSectionsV2")

EMBED_MODEL      = os.getenv("HF_EMBED_MODEL", "intfloat/e5-base-v2")

TOP_K_RETRIEVE   = int(os.getenv("TOP_K_RETRIEVE", "12"))
TOP_K_RETURN     = int(os.getenv("TOP_K_RETURN", "5"))

CSV_LOG          = os.path.abspath(os.getenv("CSV_LOG", "../outputs/newqueryLog.csv"))
LOG_FILE         = os.getenv("APP_LOG_FILE", "app.log")
LOG_LEVEL        = os.getenv("APP_LOG_LEVEL", "DEBUG").upper()

# =====================
# App + Logging
# =====================
app = Flask(__name__)
CORS(app)

os.makedirs(os.path.dirname(CSV_LOG), exist_ok=True)

root_logger = logging.getLogger()
root_logger.setLevel(LOG_LEVEL)

rot = RotatingFileHandler(LOG_FILE, maxBytes=50_000_000, backupCount=5, encoding="utf-8")
rot.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(message)s', datefmt='%Y-%m-%d %H:%M:%S'))
rot.setLevel(LOG_LEVEL)
root_logger.addHandler(rot)

console = logging.StreamHandler()
console.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s %(message)s', datefmt='%H:%M:%S'))
console.setLevel(LOG_LEVEL)
root_logger.addHandler(console)

logging.info("[INIT] Starting service…")

# =====================
# Models & DB
# =====================
embedder = SentenceTransformer(EMBED_MODEL)
embedder.max_seq_length = 512
logging.info(f"[INIT] Embedder ready: {EMBED_MODEL}")

client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = client.get_collection(name=COLLECTION_NAME)
logging.info(f"[INIT] Chroma collection loaded: {COLLECTION_NAME} @ {CHROMA_PATH}")

# Cross-encoder reranker (your module)
try:
    from reranker import rerank_results
    logging.info("[INIT] Reranker loaded.")
except Exception:
    logging.exception("[INIT] Failed to load reranker")
    raise SystemExit(1)

# =====================
# Helpers
# =====================
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

def embed_query_e5(q: str):
    return embedder.encode("query: " + q, normalize_embeddings=True).tolist()

def retrieve_dense(query: str, act: Optional[str], top_k: int) -> Tuple[List[Dict[str, Any]], float, float]:
    """
    Returns: (rows, embed_ms, chroma_ms)
    rows = [{id, text, act, section, metadata, dense_score, rank_before, score_before}, ...]
    dense_score is 1 - distance from Chroma (cosine)
    """
    t0 = time.perf_counter()
    q_emb = embed_query_e5(query)
    t1 = time.perf_counter()

    kwargs = {
        "query_embeddings": [q_emb],
        "n_results": top_k,
        "include": ["documents", "metadatas", "distances"]
    }
    if act:
        kwargs["where"] = {"act": act}

    res = collection.query(**kwargs)
    t2 = time.perf_counter()

    docs  = res.get("documents", [[]])[0]
    metas = [sanitize_meta(m) for m in res.get("metadatas", [[]])[0]]
    dists = res.get("distances", [[]])[0]
    ids   = res.get("ids", [[]])[0]

    out = []
    for i in range(len(docs)):
        dist = dists[i] if i < len(dists) else None
        sim = (1.0 - dist) if (dist is not None) else None
        md  = metas[i] if i < len(metas) else {}
        row = {
            "id": ids[i] if i < len(ids) else None,
            "text": docs[i],
            "act": md.get("act",""),
            "section": md.get("section",""),
            "metadata": md,
            "dense_score": float(sim) if sim is not None else 0.0
        }
        row["rank_before"] = i + 1
        row["score_before"] = round(row["dense_score"], 4)
        out.append(row)

    embed_ms  = round((t1 - t0) * 1000, 2)
    chroma_ms = round((t2 - t1) * 1000, 2)
    return out, embed_ms, chroma_ms

def apply_rerank(query: str, chunks: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], float]:
    """Calls your cross-encoder; falls back to original order on failure."""
    if not chunks:
        return [], 0.0
    t0 = time.perf_counter()
    logging.debug(f"[RERANK] Calling reranker on {len(chunks)} chunks for query: {query!r}")
    try:
        reranked = rerank_results(query, chunks)
        for idx, ch in enumerate(reranked):
            ch["rank_after"]  = idx + 1
            ch["score_after"] = ch.get("rerank_score", ch.get("score_before"))
    except Exception:
        logging.exception("[RERANK] Cross-encoder failed; falling back to dense order")
        reranked = []
        for idx, ch in enumerate(chunks):
            ch2 = dict(ch)
            ch2["rank_after"]  = idx + 1
            ch2["score_after"] = ch2.get("score_before")
            reranked.append(ch2)
    dt = round((time.perf_counter() - t0) * 1000, 2)
    return reranked, dt

def log_to_csv(row: Dict[str, Any]):
    df = pd.DataFrame([row])
    header = not os.path.exists(CSV_LOG)
    df.to_csv(CSV_LOG, mode="a", index=False, header=header)

# ===============
# Routes
# ===============
@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True})

@app.route("/askQuery", methods=["POST"])
def ask_query():
    req_id = str(uuid.uuid4())[:8]
    t0 = time.perf_counter()

    try:
        data = request.get_json(force=True) or {}
    except Exception:
        logging.exception(f"[{req_id}] Bad JSON payload")
        return jsonify({"error": "Invalid JSON"}), 400

    query = (data.get("query") or "").strip()
    act   = (data.get("act") or "").strip() or None
    top_k_ret = int(data.get("top_k_retrieve", TOP_K_RETRIEVE))
    top_k_out = int(data.get("top_k_return", TOP_K_RETURN))

    if not query:
        return jsonify({"error": "No query provided"}), 400

    logging.info(f"[{req_id}] Query: {query!r} | act_filter={act} | k={top_k_ret}/{top_k_out}")

    # 1) Dense retrieval
    try:
        rows_before, embed_ms, chroma_ms = retrieve_dense(query, act, top_k_ret)
    except Exception:
        logging.exception(f"[{req_id}] Retrieval failed")
        return jsonify({"error": "Retrieval failed"}), 500

    # 2) Rerank
    rows_after, rerank_ms = apply_rerank(query, rows_before)
    logging.info(f"[{req_id}] Rerank ran in {rerank_ms} ms")

    total_ms = round((time.perf_counter() - t0) * 1000, 2)
    top = rows_after[0] if rows_after else {}

    # CSV log (top doc summary)
    log_row = {
        "RequestID": req_id,
        "Query": query,
        "Top_Act": top.get("act", ""),
        "Top_Section": top.get("section", ""),
        "Top_Text": (top.get("text", "") or "")[:500],  # clip to keep CSV lighter
        "Top_Score_Before": top.get("score_before", ""),
        "Top_Score_After": top.get("score_after", ""),
        "Embed_ms": embed_ms,
        "Chroma_ms": chroma_ms,
        "Rerank_ms": rerank_ms,
        "Total_ms": total_ms,
    }
    try:
        log_to_csv(log_row)
    except Exception as e:
        logging.warning(f"[{req_id}] CSV log failed: {e}")

    logging.info(f"[{req_id}] Done in {total_ms} ms | top: {top.get('act','')}, s_after={top.get('score_after','')}")

    # Trim payload for frontend (post-rerank top_k_out)
    def pack_source(r: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": r.get("id"),
            "act": r.get("act"),
            "section": r.get("section"),
            "score_before": r.get("score_before"),
            "score_after": r.get("score_after"),
            "text": r.get("text"),
        }

    return jsonify({
        "request_id": req_id,
        "query": query,
        "timings": {
            "embed_ms": embed_ms,
            "chroma_ms": chroma_ms,
            "rerank_ms": rerank_ms,
            "total_ms": total_ms
        },
        "top_results": [pack_source(r) for r in rows_after[:top_k_out]]
    })

if __name__ == "__main__":
    app.run(debug=True, port=5000)
