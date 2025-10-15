import os
import json
import re
import glob
from typing import Dict, List, Tuple, Any

# --- Parameters ---
INPUT_FOLDER      = "../ActsinJson"
OUTPUT_FOLDER     = "../ActsinSectionChunks"
MAX_TOKENS        = 220   
OVERLAP_TOKENS    = 80    
MIN_CHUNK_TOKENS  = 60    

os.makedirs(OUTPUT_FOLDER, exist_ok=True)


WS_RE = re.compile(r"\s+")
LIST_BULLET_RE = re.compile(r"^\s*(?:\d+\.|\(\d+\)|[a-z]\)|[A-Z]\)|[-•])\s+")
SUBCLAUSE_RE = re.compile(r"^\s*(?:\(\w{1,3}\))\s+")  # (a) (b) (i) (ii) etc.

def clean_text(text: str) -> str:
    """Collapse whitespace, trim."""
    return WS_RE.sub(" ", text or "").strip()

def tokenize(text: str) -> List[str]:
    return text.split()

def detokenize(tokens: List[str]) -> str:
    return " ".join(tokens)

def soft_paragraph_split(raw: str) -> List[str]:
    """
    Prefer splitting by blank lines; if the text is a dense block,
    split by common list markers to keep clauses together.
    """
    
    parts = re.split(r"\n\s*\n+", raw.strip())
    parts = [p.strip() for p in parts if p.strip()]
    if len(parts) >= 2:
        return parts

    lines = [ln.rstrip() for ln in raw.splitlines()]
    chunks, cur = [], []
    for ln in lines:
        if LIST_BULLET_RE.match(ln) or SUBCLAUSE_RE.match(ln):
            if cur:
                chunks.append("\n".join(cur).strip())
                cur = []
        cur.append(ln)
    if cur:
        chunks.append("\n".join(cur).strip())

 
    return [p for p in chunks if p] or [raw.strip()]

def chunk_with_overlap(text: str, max_tokens: int, overlap: int) -> List[str]:
   
    toks = tokenize(clean_text(text))
    if len(toks) <= max_tokens:
        return [detokenize(toks)]

    out = []
    start = 0
    step = max_tokens - overlap
    while start < len(toks):
        end = min(start + max_tokens, len(toks))
        out.append(detokenize(toks[start:end]))
        if end == len(toks):
            break
        start += step

   
    if len(out) >= 2:
        last = tokenize(out[-1])
        prev = tokenize(out[-2])
        if len(last) < MIN_CHUNK_TOKENS and len(prev) + len(last) <= max_tokens + 10:
            out[-2] = detokenize(prev + last)
            out.pop()

    return out

def extract_all_section_text(section: Dict[str, Any]) -> List[str]:

    acc = []

    def walk(node: Any):
        if isinstance(node, dict):
            for k, v in node.items():
                if isinstance(v, (dict, list)):
                    walk(v)
                elif isinstance(v, str) and k.lower() == "content" and v.strip():
                    acc.append(v.strip())
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(section)
   
    if acc:
        return ["\n\n".join(acc)]
    return []

def normalize_heading(s: str) -> str:
    s = s or ""
    s = s.strip()
    
    s = WS_RE.sub(" ", s)
    return s

def section_identity(sec_num: str, sec_heading: str) -> str:
    head = normalize_heading(sec_heading)
    if head:
        return f"{sec_num} – {head}"
    return str(sec_num)



def make_section_chunks(
    act_name: str,
    part_name: str,
    sec_num: str,
    sec_heading: str,
    section_text: str,
    global_counter_start: int,
    section_path: str,
) -> Tuple[List[Dict[str, Any]], int]:
    
    chunks: List[Dict[str, Any]] = []
    counter = global_counter_start

    canonical_title = section_identity(sec_num, sec_heading)
    raw_blocks = soft_paragraph_split(section_text)

    
    buffer_tokens: List[str] = []
    buffered_blocks: List[str] = []

    def flush_buffer():
        nonlocal counter, chunks, buffer_tokens, buffered_blocks
        if not buffer_tokens:
            return
        text = detokenize(buffer_tokens)
        chunks.append({
            "act": act_name,
            "part": part_name,
            "section": canonical_title,
            "section_number": str(sec_num),
            "section_title": normalize_heading(sec_heading),
            "section_path": section_path,  
            "chunk_index": len(chunks) + 1, 
            "chunk_id": counter,            
            "text": text
        })
        counter += 1
        buffer_tokens = []
        buffered_blocks = []

    for block in raw_blocks:
        block = clean_text(block)
        if not block:
            continue
        toks = tokenize(block)

    
        if len(toks) > MAX_TOKENS:
            flush_buffer()
            for sub in chunk_with_overlap(block, MAX_TOKENS, OVERLAP_TOKENS):
                chunks.append({
                    "act": act_name,
                    "part": part_name,
                    "section": canonical_title,
                    "section_number": str(sec_num),
                    "section_title": normalize_heading(sec_heading),
                    "section_path": section_path,
                    "chunk_index": len(chunks) + 1,
                    "chunk_id": counter,
                    "text": sub
                })
                counter += 1
            continue

    
        if len(buffer_tokens) + len(toks) <= MAX_TOKENS:
            buffer_tokens.extend(toks)
            buffered_blocks.append(block)
        else:
          
            flush_buffer()
            buffer_tokens = toks[:]
            buffered_blocks = [block]

    flush_buffer()

    for i, ch in enumerate(chunks):
        ch["prev_chunk_id"] = chunks[i-1]["chunk_id"] if i > 0 else None
        ch["next_chunk_id"] = chunks[i+1]["chunk_id"] if i < len(chunks)-1 else None

    return chunks, counter

def process_file(file_path: str) -> List[Dict[str, Any]]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    act_name = data.get("Act", os.path.splitext(os.path.basename(file_path))[0])
    act_year = data.get("Year") or data.get("year")  # if present in your JSON

    parts: Dict[str, Any] = data.get("Parts", {}) or {}
    schedules = data.get("Schedules") or data.get("schedules")
    preamble  = data.get("Preamble") or data.get("preamble")

    all_chunks: List[Dict[str, Any]] = []
    gid = 1

  
    if isinstance(preamble, str) and preamble.strip():
        preamble_text = clean_text(preamble)
        pre_chunks = chunk_with_overlap(preamble_text, MAX_TOKENS, OVERLAP_TOKENS)
        for i, txt in enumerate(pre_chunks, 1):
            all_chunks.append({
                "act": act_name,
                "act_year": act_year,
                "part": "Preamble",
                "section": "Preamble",
                "section_number": "Preamble",
                "section_title": "Preamble",
                "section_path": "Preamble",
                "chunk_index": i,
                "chunk_id": gid,
                "text": txt,
                "prev_chunk_id": all_chunks[-1]["chunk_id"] if all_chunks else None,
                "next_chunk_id": None
            })
            if len(all_chunks) >= 2:
                all_chunks[-2]["next_chunk_id"] = gid
            gid += 1

  
    for part_name, sections in parts.items():

        if not isinstance(sections, dict):
            continue

        for sec_num, sec_data in sections.items():
            sec_title = (sec_data.get("Heading") or sec_data.get("heading") or "").strip()
            contents = extract_all_section_text(sec_data)  

            if not contents:
                continue

            
            full_text = "\n\n".join([c for c in contents if c.strip()])
            full_text = full_text.strip()
            if not full_text:
                continue

            section_path = f"{part_name} > {sec_num}"
            section_chunks, gid = make_section_chunks(
                act_name=act_name,
                part_name=part_name,
                sec_num=str(sec_num),
                sec_heading=sec_title,
                section_text=full_text,
                global_counter_start=gid,
                section_path=section_path
            )

            for ch in section_chunks:
                ch["act_year"] = act_year
                if all_chunks:
                    ch["prev_chunk_id"] = all_chunks[-1]["chunk_id"]
                    all_chunks[-1]["next_chunk_id"] = ch["chunk_id"]
                all_chunks.append(ch)


    if schedules:
        sch_text = json.dumps(schedules, ensure_ascii=False, indent=2)
        for i, txt in enumerate(chunk_with_overlap(sch_text, MAX_TOKENS, OVERLAP_TOKENS), 1):
            all_chunks.append({
                "act": act_name,
                "act_year": act_year,
                "part": "Schedules",
                "section": "Schedules",
                "section_number": "Schedules",
                "section_title": "Schedules",
                "section_path": "Schedules",
                "chunk_index": i,
                "chunk_id": gid,
                "text": txt,
                "prev_chunk_id": all_chunks[-1]["chunk_id"] if all_chunks else None,
                "next_chunk_id": None
            })
            if len(all_chunks) >= 2:
                all_chunks[-2]["next_chunk_id"] = gid
            gid += 1

    return all_chunks

def main():
    input_files = glob.glob(os.path.join(INPUT_FOLDER, "*.json"))
    for fp in input_files:
        chunks = process_file(fp)
        base = os.path.splitext(os.path.basename(fp))[0]
        out_path = os.path.join(OUTPUT_FOLDER, f"{base}_Chunks.json")
        with open(out_path, "w", encoding="utf-8") as out_f:
            json.dump(chunks, out_f, ensure_ascii=False, indent=2)
        act_name = chunks[0]["act"] if chunks else base
        print(f" {act_name} chunked into {len(chunks)} pieces → {out_path}")

if __name__ == "__main__":
    main()
