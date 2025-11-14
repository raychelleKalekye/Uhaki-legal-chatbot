import os, logging, time, uuid
from logging.handlers import RotatingFileHandler
from typing import List, Dict, Any, Optional, Tuple

from flask import Flask, request, jsonify
from flask_cors import CORS
import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
import requests

# ============================
# Config
# ============================
CHROMA_PATH     = os.getenv("CHROMA_PATH", "../data/scripts/chroma")
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "actSectionsV2")
EMBED_MODEL     = os.getenv("HF_EMBED_MODEL", "intfloat/e5-base-v2")

TOP_K_RETRIEVE  = int(os.getenv("TOP_K_RETRIEVE", "12"))
TOP_K_RETURN    = int(os.getenv("TOP_K_RETURN", "5"))

CSV_LOG         = os.path.abspath(os.getenv("CSV_LOG", "../outputs/queryLog.csv"))
LOG_LEVEL       = os.getenv("APP_LOG_LEVEL", "DEBUG").upper()
GENERATOR_URL   = os.getenv("GENERATOR_URL", "").strip()
NOTEBOOK_API_KEY = os.getenv("NOTEBOOK_API_KEY", "")
GENERATOR_TIMEOUT_S = int(os.getenv("GENERATOR_TIMEOUT_S", "120"))
BACKEND_MODE    = "proxy" if GENERATOR_URL else "retrieval-only"
LOG_COLUMNS     = [
    "Query",
    "Retrieved_Act",
    "Top Chunk Section",
    "Top Chunk Text",
    "Model Answer",
    "Runtime"
]
MAX_TOP_TEXT_CHARS = 500

# ============================
# App + Logging
# ============================
app = Flask(__name__)
CORS(app)

os.makedirs(os.path.dirname(CSV_LOG), exist_ok=True)
formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s")

log_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, "server.log")

rot = RotatingFileHandler(log_file, maxBytes=5*1024*1024, backupCount=3)
rot.setFormatter(formatter)
console = logging.StreamHandler()
console.setFormatter(formatter)

root_logger = logging.getLogger()
root_logger.setLevel(getattr(logging, LOG_LEVEL, logging.DEBUG))
root_logger.addHandler(rot)
root_logger.addHandler(console)

logging.info(f"[INIT] Starting Uhaki API ({BACKEND_MODE})")

# ============================
# Embeddings + Vector DB
# ============================
embedder = SentenceTransformer(EMBED_MODEL)
embedder.max_seq_length = 512
logging.info(f"[INIT] Embedder ready: {EMBED_MODEL}")

chroma_client = chromadb.PersistentClient(path=CHROMA_PATH)
collection = chroma_client.get_collection(name=COLLECTION_NAME)
logging.info(f"[INIT] Chroma collection loaded: {COLLECTION_NAME} @ {CHROMA_PATH}")

# ============================
# Optional: Cross-encoder reranker (fallback to no-op)
# ============================
try:
    from reranker import rerank_results  # should accept (query, List[chunk]) -> List[chunk with 'rerank_score']
    logging.info("[INIT] Reranker loaded.")
except Exception:
    logging.exception("[INIT] Failed to load reranker; using no-op fallback.")
    def rerank_results(query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        out = []
        for ch in chunks:
            ch2 = dict(ch)
            ch2["rerank_score"] = ch2.get("dense_score", 0.0)
            out.append(ch2)
        return out

# ============================
# Helpers
# ============================
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

def build_context(top_chunks: List[Dict[str, Any]]) -> str:
    parts = []
    for i, c in enumerate(top_chunks, start=1):
        section_title = c.get("section", "")
        act_name = c.get("act", "")
        text = (c.get("text", "") or "").strip()
        parts.append(f"[{i}] {act_name} - {section_title}\n{text}\n")
    return "\n".join(parts)

def build_query_log_row(query: str,
                        top_chunk: Optional[Dict[str, Any]],
                        model_answer: Optional[str],
                        runtime_ms: Optional[float]) -> Dict[str, Any]:
    chunk = top_chunk or {}
    text = (chunk.get("text", "") or "")[:MAX_TOP_TEXT_CHARS]
    runtime_val = round(runtime_ms, 2) if runtime_ms is not None else ""
    return {
        "Query": query,
        "Retrieved_Act": chunk.get("act", ""),
        "Top Chunk Section": chunk.get("section", ""),
        "Top Chunk Text": text,
        "Model Answer": model_answer or "",
        "Runtime": runtime_val
    }

def embed_query_e5(q: str):
 
    return embedder.encode("query: " + q, normalize_embeddings=True).tolist()

def retrieve_dense(query: str, act: Optional[str], top_k: int) -> Tuple[List[Dict[str, Any]], float, float]:
    """
    Returns: (rows, embed_ms, chroma_ms)
    rows = [{id, text, act, section, metadata, dense_score, rank_before, score_before}, ...]
    dense_score = 1 - cosine_distance from Chroma
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
            "act": md.get("act", ""),
            "section": md.get("section", ""),
            "metadata": md,
            "dense_score": float(sim) if sim is not None else 0.0
        }
        row["rank_before"]  = i + 1
        row["score_before"] = round(row["dense_score"], 4)
        out.append(row)

    embed_ms  = round((t1 - t0) * 1000, 2)
    chroma_ms = round((t2 - t1) * 1000, 2)
    return out, embed_ms, chroma_ms

def apply_rerank(query: str, chunks: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], float]:
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
    sanitized = {col: row.get(col, "") for col in LOG_COLUMNS}
    df = pd.DataFrame([sanitized], columns=LOG_COLUMNS)
    header_needed = True
    if os.path.exists(CSV_LOG):
        try:
            header_needed = os.path.getsize(CSV_LOG) == 0
        except OSError:
            header_needed = False
    df.to_csv(CSV_LOG, mode="a", index=False, header=header_needed)


def call_generator_api(query: str, act: Optional[str], top_k_retrieve: int,
                       top_k_return: int, include_context: bool) -> Dict[str, Any]:
    if not GENERATOR_URL:
        raise RuntimeError("GENERATOR_URL is not configured.")

    payload: Dict[str, Any] = {
        "query": query,
        "top_k_return": top_k_return,
        "top_k_retrieve": top_k_retrieve
    }
    if act:
        payload["act"] = act
    payload["include_context"] = bool(include_context)

    headers = {"Content-Type": "application/json"}
    if NOTEBOOK_API_KEY:
        headers["X-API-Key"] = NOTEBOOK_API_KEY

    logging.debug(f"[PROXY] Forwarding query to generator @ {GENERATOR_URL}")
    resp = requests.post(
        GENERATOR_URL,
        json=payload,
        headers=headers,
        timeout=GENERATOR_TIMEOUT_S
    )
    resp.raise_for_status()
    return resp.json()


def fetch_docs_by_ids(ids: List[str]) -> Dict[str, Dict[str, Any]]:
    unique_ids: List[str] = []
    seen = set()
    for doc_id in ids:
        if not doc_id or doc_id in seen:
            continue
        seen.add(doc_id)
        unique_ids.append(doc_id)
    if not unique_ids:
        return {}

    try:
        batch = collection.get(ids=unique_ids, include=["documents", "metadatas"])
    except Exception:
        logging.exception("[PROXY] Failed to hydrate docs from Chroma via ids.")
        return {}

    docs = batch.get("documents", [])
    metas = [sanitize_meta(m) for m in batch.get("metadatas", [{}])]
    found_ids = batch.get("ids", [])
    hydrated: Dict[str, Dict[str, Any]] = {}
    for idx, doc_id in enumerate(found_ids):
        meta = metas[idx] if idx < len(metas) else {}
        text_val = (docs[idx] or "") if idx < len(docs) else ""
        hydrated[doc_id] = {
            "id": doc_id,
            "text": text_val,
            "act": meta.get("act") or meta.get("Act") or "",
            "section": meta.get("section") or meta.get("section_title") or meta.get("heading") or "",
        }
    return hydrated


def hydrate_generator_sources(gen_payload: Dict[str, Any], limit: int) -> List[Dict[str, Any]]:
    raw = gen_payload.get("raw") or {}
    ids = raw.get("ids") or []
    limit = max(0, min(limit, len(ids)))
    if limit == 0:
        return []

    doc_map = fetch_docs_by_ids(ids[:limit])
    top6 = gen_payload.get("top6") or []
    hydrated = []
    for idx in range(limit):
        doc_id = ids[idx]
        fallback = top6[idx] if idx < len(top6) else {}
        doc = doc_map.get(doc_id) or {}
        hydrated.append({
            "id": doc_id,
            "act": fallback.get("act") or doc.get("act"),
            "section": fallback.get("section") or doc.get("section"),
            "text": doc.get("text"),
            "score_before": None,
            "score_after": None,
        })
    return hydrated

# ============================
# Routes
# ============================
@app.route("/health", methods=["GET"])
def health():
    return jsonify({
        "ok": True,
        "backend": BACKEND_MODE,
        "collection": COLLECTION_NAME,
        "embed_model": EMBED_MODEL,
        "generator_url": GENERATOR_URL if GENERATOR_URL else None
    })

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
    include_context = bool(data.get("include_context", True))

    if not query:
        return jsonify({"error": "No query provided"}), 400

    logging.info(
        f"[{req_id}] Query: {query!r} | act_filter={act} | k={top_k_ret}/{top_k_out} | mode={BACKEND_MODE}"
    )

    if GENERATOR_URL:
        try:
            generator_payload = call_generator_api(query, act, top_k_ret, top_k_out, include_context)
        except requests.Timeout:
            logging.exception(f"[{req_id}] Generator timed out")
            return jsonify({"error": "Generator timeout"}), 504
        except requests.RequestException:
            logging.exception(f"[{req_id}] Generator request failed")
            return jsonify({"error": "Generator request failed"}), 502

        total_ms = round((time.perf_counter() - t0) * 1000, 2)
        top_results = hydrate_generator_sources(generator_payload, top_k_out)
        model_answer = generator_payload.get("answer")
        resp = {
            "request_id": req_id,
            "query": query,
            "answer": model_answer,
            "top_results": top_results,
            "timings": generator_payload.get("timings") or {"total_ms": total_ms},
            "proxy": True
        }
        if include_context and top_results:
            resp["context"] = build_context(top_results)

        top = top_results[0] if top_results else {}
        log_row = build_query_log_row(query, top, model_answer, total_ms)
        try:
            log_to_csv(log_row)
        except Exception as e:
            logging.warning(f"[{req_id}] CSV log failed: {e}")

        logging.info(f"[{req_id}] Proxy completed in {total_ms} ms | top_act={top.get('act','')}")
        return jsonify(resp)

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

    log_row = build_query_log_row(query, top, None, total_ms)
    try:
        log_to_csv(log_row)
    except Exception as e:
        logging.warning(f"[{req_id}] CSV log failed: {e}")

    logging.info(f"[{req_id}] Done in {total_ms} ms | top: {top.get('act','')}, s_after={top.get('score_after','')}")

    def pack_source(r: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "id": r.get("id"),
            "act": r.get("act"),
            "section": r.get("section"),
            "score_before": r.get("score_before"),
            "score_after": r.get("score_after"),
            "text": r.get("text"),
        }

    resp = {
        "request_id": req_id,
        "query": query,
        "timings": {
            "embed_ms": embed_ms,
            "chroma_ms": chroma_ms,
            "rerank_ms": rerank_ms,
            "total_ms": total_ms
        },
        "top_results": [pack_source(r) for r in rows_after[:top_k_out]],
        "proxy": False
    }
    if include_context:
        resp["context"] = build_context(rows_after[:top_k_out])

    return jsonify(resp)

# ============================
# Main
# ============================
if __name__ == "__main__":
    print(" Starting Flask server on http://127.0.0.1:5000 ...")
    app.run(debug=True, port=5000)
