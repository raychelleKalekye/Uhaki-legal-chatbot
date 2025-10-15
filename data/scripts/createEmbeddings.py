import os, glob, json, hashlib
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from chromaInit import get_chroma_collection  
from tqdm import tqdm


CHUNKS_DIR          = os.getenv("CHUNKS_DIR", "../ActsinSectionChunks")
BATCH_SIZE          = int(os.getenv("BATCH_SIZE", "64"))
HF_MODEL            = os.getenv("HF_MODEL", "intfloat/e5-base-v2")
NEW_COLLECTION_NAME = os.getenv("NEW_COLLECTION", "actSectionsV2")
ADD_E5_PREFIX       = os.getenv("ADD_E5_PREFIX", "1") == "1"


model = SentenceTransformer(HF_MODEL)
model.max_seq_length = 512

collection = None
try:
    collection = get_chroma_collection(NEW_COLLECTION_NAME)
except TypeError:
    try:
        import chromadb
        from chromadb.config import Settings
        client = chromadb.PersistentClient(
            path=os.getenv("CHROMA_PATH", "./chroma"),
            settings=Settings(allow_reset=True)
        )
        collection = client.get_or_create_collection(
            NEW_COLLECTION_NAME,
            metadata={"model": HF_MODEL, "source": "ActsinSectionChunks"}
        )
        print(f"[info] Using direct Chroma client. Created/loaded collection: {NEW_COLLECTION_NAME}")
    except Exception as e:
        print(f"[warn] Named collection not supported and direct client failed ({e}). "
              f"Falling back to default get_chroma_collection(). This may MIX embeddings with the old table.")
        collection = get_chroma_collection()


def deterministic_id(act: str, section: str, chunk_id: int, model_tag: str) -> str:
    raw = f"{act}::{section}::{chunk_id}::{model_tag}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def maybe_prefix_e5(texts: List[str], is_query: bool = False) -> List[str]:
    if not ADD_E5_PREFIX:
        return texts
    prefix = "query: " if is_query else "passage: "
    return [prefix + (t or "") for t in texts]

def sanitize_metadata(meta: Dict) -> Dict:
  
    return {k: v for k, v in meta.items() if v is not None}

chunk_files = glob.glob(os.path.join(CHUNKS_DIR, "*.json"))
print(f"Found {len(chunk_files)} chunk files in {CHUNKS_DIR}")

for file_idx, file_path in enumerate(sorted(chunk_files), start=1):
    act_name = os.path.splitext(os.path.basename(file_path))[0].replace("_Chunks", "")
    print(f"\n[{file_idx}/{len(chunk_files)}] Embedding: {act_name}")

    with open(file_path, "r", encoding="utf-8") as f:
        chunks: List[Dict] = json.load(f)

    total_batches = (len(chunks) + BATCH_SIZE - 1) // BATCH_SIZE
    for i in tqdm(range(0, len(chunks), BATCH_SIZE), total=total_batches, desc=act_name):
        batch = chunks[i:i+BATCH_SIZE]

        texts = [c.get("text", "") for c in batch]
        metadatas = [sanitize_metadata({
            "act":            c.get("act", act_name),
            "part":           c.get("part"),
            "section":        c.get("section"),
            "section_number": c.get("section_number"),
            "section_title":  c.get("section_title"),
            "section_path":   c.get("section_path"),
            "chunk_index":    c.get("chunk_index"),
            "chunk_id":       c.get("chunk_id"),
            "prev_chunk_id":  c.get("prev_chunk_id"),
            "next_chunk_id":  c.get("next_chunk_id"),
            "model":          HF_MODEL,
            "embedding_type": "section_passage",
        }) for c in batch]

        texts_for_embed = maybe_prefix_e5(texts, is_query=False)

        embeddings = model.encode(
            texts_for_embed,
            batch_size=BATCH_SIZE,
            convert_to_numpy=True,
            normalize_embeddings=True
        ).tolist()

        ids = [
            deterministic_id(m["act"], m["section"], int(m.get("chunk_id") or 0), HF_MODEL)
            for m in metadatas
        ]

        collection.add(documents=texts, embeddings=embeddings, metadatas=metadatas, ids=ids)

    print(f" → Completed embedding {len(chunks)} chunks for {act_name} into collection '{NEW_COLLECTION_NAME}'")

print("\n All section chunks embedded into the NEW Chroma collection .")
