import os
import re
import json
import uuid
from sentence_transformers import SentenceTransformer
from chromaInit import get_chroma_collection

def preprocess_law(text, act_name="Unknown Act"):
    structured_data = {"Act": act_name, "Parts": {}}
    current_part = "General"
    current_section = None

    part_pattern = re.compile(r'Part\s+([IVXLC]+)\s*[-–]?\s*(.*)', re.IGNORECASE)
    section_pattern = re.compile(r'^\s*(\d+)\.\s*(.*)', re.MULTILINE)
    definition_pattern = re.compile(r'"([^"]+)"\s+means\s+(.*?)(?=(;|$))', re.IGNORECASE)

    lines = text.splitlines()
    for line in lines:
        line = line.strip()
        if not line:
            continue

        part_match = part_pattern.match(line)
        if part_match:
            roman, heading = part_match.groups()
            current_part = f"Part {roman} – {heading.strip()}"
            structured_data["Parts"].setdefault(current_part, {})
            current_section = None
            continue

        section_match = section_pattern.match(line)
        if section_match:
            section_num, heading = section_match.groups()
            current_section = section_num
            structured_data["Parts"].setdefault(current_part, {})
            structured_data["Parts"][current_part][section_num] = {
                "Heading": heading.strip(),
                "Content": ""
            }
            continue

        if current_section:
            structured_data["Parts"][current_part][current_section]["Content"] += " " + line
        else:
            structured_data["Parts"].setdefault(current_part, {})
            structured_data["Parts"][current_part].setdefault("Preamble", {"Heading": "Preamble", "Content": ""})
            structured_data["Parts"][current_part]["Preamble"]["Content"] += " " + line

    # Extract definitions
    for part, sections in structured_data["Parts"].items():
        for sec_num, sec_data in sections.items():
            if "interpretation" in sec_data["Heading"].lower():
                definitions = {}
                for match in definition_pattern.finditer(sec_data["Content"]):
                    term, meaning, _ = match.groups()
                    definitions[term.strip()] = meaning.strip()
                if definitions:
                    sec_data["Definitions"] = definitions
    return structured_data


def clean_text(text):
    return re.sub(r'\s+', ' ', text).strip()

def chunk_text(text, chunk_size=150, overlap_size=20):
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk_words = words[start:end]
        if chunk_words:
            chunks.append(" ".join(chunk_words))
        start += chunk_size - overlap_size
    return chunks

def extract_contents(section):
    contents = []
    if isinstance(section, dict):
        for k, v in section.items():
            if k.lower() == "content" and v.strip():
                contents.append(v.strip())
            elif isinstance(v, dict):
                contents.extend(extract_contents(v))
    return contents

def embed_chunks(chunks, act_name, collection, model):
    BATCH_SIZE = 16
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        texts = [chunk["text"] for chunk in batch]
        embeddings = model.encode(texts).tolist()

        metadatas = [{"act": chunk.get("act", ""), "section": chunk.get("section", "")} for chunk in batch]
        ids = [str(uuid.uuid4()) for _ in batch]

        collection.add(
            documents=texts,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas
        )
    print(f" → Embedded {len(chunks)} chunks for {act_name}")

if __name__ == "__main__":
    input_dir = "../Cleaned Acts"
    json_dir = "../ActsinJson"
    chunk_dir = "../ActsinChunks"

    os.makedirs(json_dir, exist_ok=True)
    os.makedirs(chunk_dir, exist_ok=True)

    model = SentenceTransformer("../models/legal-bert-base-uncased")
    collection = get_chroma_collection()

    #  Only process these Acts
    target_files = [
        "Children Act.txt",
        "Criminal Procedure Code.txt"
    ]

    for filename in target_files:
        input_path = os.path.join(input_dir, filename)
        if not os.path.exists(input_path):
            print(f"File not found: {input_path}")
            continue

        act_name = os.path.splitext(filename)[0]

        # --- Step 1: Preprocess to JSON ---
        with open(input_path, "r", encoding="utf-8") as f:
            text = f.read()
        structured = preprocess_law(text, act_name)
        json_path = os.path.join(json_dir, f"{act_name}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(structured, f, indent=4, ensure_ascii=False)
        print(f"{filename} → JSON created")

        # --- Step 2: Chunk JSON ---
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        all_chunks = []
        chunk_counter = 1
        for part_name, sections in data.get("Parts", {}).items():
            for sec_num, sec_data in sections.items():
                contents = extract_contents(sec_data)
                for content in contents:
                    text = clean_text(content)
                    chunks = chunk_text(text)
                    for chunk in chunks:
                        all_chunks.append({
                            "act": act_name,
                            "part": part_name,
                            "section": f"{sec_num} – {sec_data.get('Heading','')}",
                            "chunk_id": chunk_counter,
                            "text": chunk
                        })
                        chunk_counter += 1

        chunk_path = os.path.join(chunk_dir, f"{act_name}_Chunks.json")
        with open(chunk_path, "w", encoding="utf-8") as f:
            json.dump(all_chunks, f, indent=2, ensure_ascii=False)
        print(f"{act_name} → {len(all_chunks)} chunks created")

        # --- Step 3: Embed into Chroma ---
        embed_chunks(all_chunks, act_name, collection, model)

    print(" Pipeline complete: Children’s Act & Criminal Procedure Code processed into Chroma")
