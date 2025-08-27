import os
import json
import re

def split_into_chunks(text, max_words=150):
 
    sentences = re.split(r'(?<=[.?!])\s+', text)
    chunks, current_chunk = [], []

    for sentence in sentences:
        words = sentence.split()
        if len(current_chunk) + len(words) > max_words:
            chunks.append(" ".join(current_chunk))
            current_chunk = words
        else:
            current_chunk.extend(words)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks

def chunk_json_file(input_path, output_path, act_name):
    with open(input_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    chunks = []
    for part, sections in data["Parts"].items():
        for sec_num, sec_data in sections.items():
            content = sec_data.get("Content", "").strip()
            if not content:
                continue

            section_heading = f"{sec_num} – {sec_data.get('Heading','')}".strip()
            section_chunks = split_into_chunks(content)

            for i, chunk in enumerate(section_chunks, start=1):
                chunks.append({
                    "act": act_name,
                    "part": part,
                    "section": section_heading,
                    "chunk_id": i,
                    "content": chunk
                })

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, indent=4, ensure_ascii=False)

    print(f" {act_name} chunked into {len(chunks)} pieces → {output_path}")


if __name__ == "__main__":
    input_dir = "../ActsinJson"
    output_dir = "../ActsinChunks"
    os.makedirs(output_dir, exist_ok=True)

    for filename in os.listdir(input_dir):
        if filename.endswith(".json"):
            act_name = os.path.splitext(filename)[0]
            input_path = os.path.join(input_dir, filename)
            output_path = os.path.join(output_dir, f"{act_name}_Chunks.json")

            chunk_json_file(input_path, output_path, act_name)
