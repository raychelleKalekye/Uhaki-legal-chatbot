import os
import json
import re
import glob

# --- Parameters ---
input_folder = "../ActsinJson"
output_folder = "../ActsinChunks"
chunk_size = 150       # words per chunk
overlap_size = 20      # words to overlap

os.makedirs(output_folder, exist_ok=True)

def clean_text(text):
    """Remove extra whitespace and line breaks."""
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
    """Recursively extract all content strings from nested dicts."""
    contents = []
    if isinstance(section, dict):
        for k, v in section.items():
            if k.lower() == "content" and v.strip():
                contents.append(v.strip())
            elif isinstance(v, dict):
                contents.extend(extract_contents(v))
    return contents

# --- Process each JSON file
input_files = glob.glob(os.path.join(input_folder, "*.json"))

for file_path in input_files:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    act_name = data.get("Act", os.path.splitext(os.path.basename(file_path))[0])
    all_chunks = []
    chunk_counter = 1

    for part_name, sections in data.get("Parts", {}).items():
        for sec_num, sec_data in sections.items():
            # Extract all nested content
            contents = extract_contents(sec_data)
            for content in contents:
                text = clean_text(content)
                chunks = chunk_text(text, chunk_size, overlap_size)

                for chunk in chunks:
                    all_chunks.append({
                        "act": act_name,
                        "part": part_name,
                        "section": f"{sec_num} – {sec_data.get('Heading','')}",
                        "chunk_id": chunk_counter,
                        "text": chunk
                    })
                    chunk_counter += 1

    # Save chunks as JSON
    base_name = os.path.splitext(os.path.basename(file_path))[0]
    output_file = os.path.join(output_folder, f"{base_name}_Chunks.json")
    with open(output_file, "w", encoding="utf-8") as out_f:
        json.dump(all_chunks, out_f, ensure_ascii=False, indent=2)

    print(f" {act_name} chunked into {len(all_chunks)} pieces → {output_file}")
