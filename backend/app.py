import os
from flask import Flask, request, jsonify
from transformers import AutoTokenizer, AutoModelForSequenceClassification, pipeline
import logging
from flask_cors import CORS

app = Flask(__name__)
CORS(app) 



logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='[%(asctime)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

model_path = os.path.abspath(r"../data/models/roberta_classifier_retrained")

tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
model = AutoModelForSequenceClassification.from_pretrained(model_path, local_files_only=True)

classifier = pipeline("text-classification", model=model, tokenizer=tokenizer)

@app.route('/')
def home():
    return "Uhaki backend is running!"

@app.route('/askQuery', methods=['POST'])
def ask_query():
    data = request.get_json()
    query = data.get('query', '').strip()
    if not query:
        return jsonify({"error": "No query provided"}), 400

    result = classifier(query)[0]
    predicted_act = result['label']
    confidence = float(result['score'])

    logging.info(f'Query: "{query}" | Predicted Act: "{predicted_act}" | Confidence: {confidence:.2f}')

    return jsonify({
        "predicted_act": predicted_act,
        "confidence": round(confidence, 2)
    })

if __name__ == '__main__':
    app.run(debug=True, port=5000)
