import argparse
import sys
import time
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chroma_path", type=str, default="./chroma", help="Path to Chroma PersistentClient directory")
    parser.add_argument("--collection", type=str, default="actSectionsV2", help="Chroma collection name")
    parser.add_argument("--model", type=str, default="intfloat/e5-base-v2", help="SentenceTransformer model name")
    parser.add_argument("--top_k", type=int, default=3, help="Number of results to retrieve per question")
    parser.add_argument("--max_answer_chars", type=int, default=900, help="Trim retrieved doc text to this many chars")
    parser.add_argument("--csv_path", type=str, default="../ActsinQuestions/trialQuestions2.csv")
    parser.add_argument("--output_path", type=str, default="./csvResponses2.csv")
    args = parser.parse_args()

    try:
        from sentence_transformers import SentenceTransformer
        import chromadb
    except Exception as e:
        print("[ERROR] You need 'sentence-transformers' and 'chromadb' installed where you RUN this script.")
        print("Install with: pip install sentence-transformers chromadb")
        print("Details:", e)
        sys.exit(1)

    csv_path = Path(args.csv_path)
    if not csv_path.exists():
        print(f"[ERROR] CSV not found at: {csv_path}")
        sys.exit(1)

    # Load input CSV
    df = pd.read_csv(csv_path, encoding="utf-8-sig")

    # Normalize columns
    cols = {c.lower(): c for c in df.columns}
    if "question" not in cols:
        print("[ERROR] Input CSV must have a 'question' column.")
        sys.exit(1)
    qcol = cols["question"]
    acol = cols.get("act", None)

    # Prepare output path
    output_path = Path(args.output_path) if args.output_path else csv_path.with_name(csv_path.stem + "_retrieved.csv")

    print(f"[INFO] Input:  {csv_path}")
    print(f"[INFO] Output: {output_path}")
    print(f"[INFO] Chroma path: {args.chroma_path} | Collection: {args.collection}")
    print(f"[INFO] Model: {args.model} | top_k={args.top_k} | max_answer_chars={args.max_answer_chars}")

    # Load model
    model = SentenceTransformer(args.model)
    model.max_seq_length = 512

    # Connect to Chroma
    client = chromadb.PersistentClient(path=args.chroma_path)
    try:
        collection = client.get_collection(name=args.collection)
    except Exception as e:
        print(f"[ERROR] Could not open collection '{args.collection}' at '{args.chroma_path}'.")
        print("Make sure you've created and populated this collection already.")
        print("Details:", e)
        sys.exit(1)

    # Helper to run a single retrieval
    def retrieve_top(question: str, act_hint: str | None) -> Dict[str, Any]:
        try:
            emb = model.encode("query: " + question, normalize_embeddings=True)

            query_kwargs = {
                "query_embeddings": [emb.tolist()],
                "n_results": args.top_k,
                "include": ["metadatas", "documents", "distances"],  # <-- removed "ids"
            }
            # Optional: narrow by Act if your metadata has 'act'
            if act_hint and act_hint.strip():
                query_kwargs["where"] = {"act": act_hint.strip()}

            results = collection.query(**query_kwargs)

            docs  = results.get("documents", [[]])[0]
            metas = results.get("metadatas", [[]])[0]
            dists = results.get("distances", [[]])[0]
            ids   = results.get("ids", [[]])[0]  # still available even if not requested in include

            if not docs:
                return {"retrieved_act": None, "section": None, "similarity": None, "answer_text": None, "doc_id": None}

            # Take top-1
            doc0  = docs[0] if len(docs)  > 0 else None
            meta0 = metas[0] if len(metas) > 0 else {}
            dist0 = dists[0] if len(dists) > 0 else None
            id0   = ids[0] if len(ids)   > 0 else None

            # Convert cosine distance to similarity (1 - distance)
            similarity = None
            if dist0 is not None:
                try:
                    similarity = 1.0 - float(dist0)
                except Exception:
                    similarity = None

            answer_text = (doc0 or "")
            if len(answer_text) > args.max_answer_chars:
                answer_text = answer_text[:args.max_answer_chars] + "..."

            return {
                "retrieved_act": meta0.get("act"),
                "section": meta0.get("section"),
                "similarity": similarity,
                "answer_text": answer_text,
                "doc_id": id0,
            }
        except Exception as e:
            return {
                "retrieved_act": None,
                "section": None,
                "similarity": None,
                "answer_text": f"[ERROR during retrieval: {e}]",
                "doc_id": None,
            }

    rows_out: List[Dict[str, Any]] = []
    total = len(df)
    start_time = time.time()
    print(f"[INFO] Querying {total} questions...")

    for idx, row in df.iterrows():
        question = str(row[qcol]).strip()
        act_csv  = str(row[acol]).strip() if acol and pd.notna(row[acol]) else None
        if not question:
            continue

        out = retrieve_top(question, act_csv)
        rows_out.append({
            "question": question,
            "act": act_csv,
            "retrieved_act": out["retrieved_act"],
            "section": out["section"],
            "similarity": out["similarity"],
            "answer_text": out["answer_text"],
            "doc_id": out["doc_id"],
        })

        if (idx + 1) % 10 == 0 or (idx + 1) == total:
            elapsed = time.time() - start_time
            print(f"  - Processed {idx + 1}/{total} in {elapsed:.1f}s")

    out_df = pd.DataFrame(rows_out, columns=[
        "question", "act", "retrieved_act", "section", "similarity", "answer_text", "doc_id"
    ])
    out_df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"[DONE] Saved {len(out_df)} rows to: {output_path}")


if __name__ == "__main__":
    main()
