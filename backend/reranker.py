# reranker.py
import os
from typing import List, Dict, Any
import torch
from sentence_transformers import CrossEncoder

LOCAL_PATH = os.getenv("CE_LOCAL_PATH", r"D:\Users\user\github-classroom\is-project-4th-year\GRP-B-ISP-raychelleKalekye\data\models\ms-marco-MiniLM-L-6-v2")
HF_MODEL   = os.getenv("CE_HF_MODEL", "cross-encoder/ms-marco-MiniLM-L-6-v2")
BATCH_SIZE = int(os.getenv("CE_BATCH_SIZE", "32"))
MAX_CHARS  = int(os.getenv("CE_MAX_CHARS", "1200"))
HEAD_CHARS = int(os.getenv("CE_HEAD_CHARS", "900"))
TAIL_CHARS = int(os.getenv("CE_TAIL_CHARS", "300"))
ALPHA      = float(os.getenv("CE_FUSION_ALPHA", "0.7"))

_device = "cuda" if torch.cuda.is_available() else "cpu"
try:
    reranker_model = CrossEncoder(LOCAL_PATH, device=_device, local_files_only=True)
except Exception:
    reranker_model = CrossEncoder(HF_MODEL, device=_device)

def _trim_text(t: str) -> str:
    if not t: return ""
    if len(t) <= MAX_CHARS: return t
    head = t[:HEAD_CHARS]
    tail = t[-TAIL_CHARS:]
    return head + "\n...\n" + tail

def _minmax(xs):
    xs = [0.0 if (x is None) else float(x) for x in xs]
    lo, hi = min(xs), max(xs)
    if hi - lo < 1e-9: return [0.0 for _ in xs]
    return [(x - lo) / (hi - lo) for x in xs]

def rerank_results(query: str, chunks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not chunks: return []
    texts = [ _trim_text(c.get("text","")) for c in chunks ]
    pairs = [(query, t) for t in texts]
    try:
        ce_scores = reranker_model.predict(pairs, batch_size=BATCH_SIZE, show_progress_bar=False)
        ce_scores = [float(s) for s in ce_scores]
    except Exception:
        ce_scores = [0.0 for _ in chunks]

    dense = [c.get("score_before") for c in chunks]
    ce_n = _minmax(ce_scores)
    dn_n = _minmax(dense) if any(d is not None for d in dense) else [0.0]*len(chunks)
    fused = [ALPHA*ce + (1-ALPHA)*dn for ce,dn in zip(ce_n, dn_n)]

    out = []
    for c, ce, fu in zip(chunks, ce_scores, fused):
        d = dict(c)
        d["rerank_score"] = ce
        d["score"] = fu
        out.append(d)

    out.sort(key=lambda x: x.get("score", 0.0), reverse=True)
    return out
