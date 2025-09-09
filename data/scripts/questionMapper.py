import os
import json
import csv
from transformers import pipeline


qa_generator = pipeline("text2text-generation", model="google/flan-t5-small")


input_folder = "../ActsinChunks"
output_folder = "../ActsinQuestions"


os.makedirs(output_folder, exist_ok=True)


for filename in os.listdir(input_folder):
    if not filename.endswith("_Chunks.json"):
        continue

    input_file = os.path.join(input_folder, filename)
    output_file = os.path.join(output_folder, filename.replace("_Chunks.json", "_questions.csv"))

    with open(input_file, "r", encoding="utf-8") as f:
        chunks = json.load(f)

    with open(output_file, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["question", "act"])

        for chunk in chunks:
            text = chunk.get("text", "").strip()
            act = chunk.get("act", filename.replace("_Chunks.json", ""))

            if not text:
                continue

            prompt = f"Turn the following law into a short, everyday legal question:\n\n{text}\n\nQuestion:"

            try:
                question = qa_generator(prompt, max_length=64, num_return_sequences=1)[0]['generated_text']
            except Exception as e:
                print(f"Error processing {filename}: {e}")
                question = ""

            
            if (
                not question 
                or "Generate" in question 
                or "simple user-style" in question 
                or "False" in question 
                or len(question.split()) < 3
            ):
                continue

            if "?" not in question:
                question = question.strip() + "?"

            writer.writerow([question.strip(), act])

    print(f" Cleaned legal questions saved to {output_file}")
