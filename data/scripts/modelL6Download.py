import os
from sentence_transformers import CrossEncoder
from huggingface_hub import snapshot_download

local_model_path = os.path.abspath(r"../models/ms-marco-MiniLM-L-6-v2")

if not os.path.exists(local_model_path) or not os.listdir(local_model_path):
    print("Downloading MS MARCO MiniLM model into:", local_model_path)
    snapshot_download(
        repo_id="cross-encoder/ms-marco-MiniLM-L-6-v2",
        local_dir=local_model_path,
        local_dir_use_symlinks=False,
        force_download=True
    )


try:
    reranker = CrossEncoder(local_model_path)
    print("Loaded MS MARCO MiniLM reranker from:", local_model_path)
except Exception as e:
    print("Error loading model:", e)
    raise
