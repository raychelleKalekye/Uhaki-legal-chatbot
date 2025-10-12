import os 
import json
import csv
from transformers import pipeline

qa_generator = pipeline("text2text-generation", model="google/flan-t5-small")

input_folder = "../ActsinChunks"
output_folder = "../ActsinQuestionAnswer"

os.makedirs(output_folder, exist_ok=True)

for filename in os.listdir(input_folder):
    if not filename.endswith("_Chunks.json"):
        continue

    input_file = os.path.join(input_folder, filename)
    output_file = os.path.join(output_folder, filename.replace("_Chunks.json", "_qa.csv"))

    with open(input_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    print(f"\nProcessing file: {filename} with {len(chunks)} chunks...")

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["question", "answer", "act"])

        for i, chunk in enumerate(chunks, start=1):
            text = chunk.get("text", "").strip()
            act = chunk.get("act", filename.replace("_Chunks.json", ""))

            if not text:
                continue

            
            print(f"  ➤ Chunk {i}/{len(chunks)} from {filename}")

            prompt = f"""
Turn the following legal text into up to four clear question-and-answer pairs.
Write each pair on a new line in the format:
Q: ...
A: ...

Text:
{text}
            """

            try:
                response = qa_generator(
                    prompt,
                    max_new_tokens=256,   
                    num_return_sequences=1
                )[0]['generated_text']
            except Exception as e:
                print(f"Error processing chunk {i} in {filename}: {e}")
                continue

            
            lines = response.strip().split("\n")
            q, a = None, None
            pair_count = 0

            for line in lines:
                line = line.strip()
                if line.lower().startswith("q:"):
                    q = line[2:].strip()
                elif line.lower().startswith("a:"):
                    a = line[2:].strip()
                    if q and a:
                        writer.writerow([q, a, act])
                        q, a = None, None
                        pair_count += 1

                        if pair_count >= 4:  
                            break

    print(f" Q&A pairs saved to {output_file}")
