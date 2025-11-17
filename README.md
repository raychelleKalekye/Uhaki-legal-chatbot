# Uhaki Legal Assistant System

Uhaki is a retrieval-augmented legal assistant focused on accelerating access to Kenyan Acts of Parliament. The project combines a rigorously curated legal corpus, dense vector search, an optional large-language-model generator, and a conversational React front end so that domain experts and citizens can explore statutes in natural language.

## Table of contents
- [Overview](#overview)
- [Project flow](#project-flow)
- [Technology stack](#technology-stack)
- [Key features](#key-features)
- [Repository layout](#repository-layout)
- [Data & knowledge pipeline](#data--knowledge-pipeline)
- [Backend retrieval API](#backend-retrieval-api)
- [Frontend web app](#frontend-web-app)
- [Evaluation & quality assurance](#evaluation--quality-assurance)
- [Quickstart](#quickstart)
- [Configuration reference](#configuration-reference)
- [API reference](#api-reference)
- [Monitoring & analytics](#monitoring--analytics)
- [Testing](#testing)
- [Deployment checklist](#deployment-checklist)
- [Roadmap](#roadmap)
- [Resources & acknowledgements](#resources--acknowledgements)

## Overview
Kenyan statutes are lengthy, updated frequently, and distributed as PDFs that are difficult to search. Uhaki transforms these materials into structured chunks, indexes them inside a local Chroma vector store, and exposes a conversational interface that can surface relevant sections together with citations. A retrieval-only flow is always available, while a proxy mode can forward curated context to an external LLM endpoint for abstractive answers. Evaluation notebooks, logging, and visualization assets are bundled in the repository to keep research, engineering, and reporting in one place.

## Project flow
1. **Collect & clean Acts** - Raw gazette PDFs are normalized into JSON and CSV artifacts under `data/`.
2. **Segment & embed** - Scripts in `data/scripts/` split sections into overlapping context windows and encode them with `intfloat/e5-base-v2`.
3. **Persist vectors** - Embeddings and metadata land inside a persistent ChromaDB collection.
4. **Server retrieval** - `backend/app.py` exposes and `/askQuery`, optionally fusing results with a cross-encoder reranker.
5. **Conversational UI** - The React client in `frontend/` renders chat history, sources, and disclaimers, persisting sessions in `localStorage`.
6. **Evaluate & iterate** - Jupyter notebooks and CSV logs in `testing/` and `outputs/` capture retrieval metrics, QA quality, and temporal usage for continuous improvement.

## Technology stack
| Layer | Technologies | Notes |
| --- | --- | --- |
| Data preparation | Python, pandas, regex, custom scripts (`actPreprocessing.py`, `splitChunks.py`) | Handles PDF to JSON/CSV parsing, cleaning, and chunking. |
| Vector store | [ChromaDB](https://docs.trychroma.com/), `intfloat/e5-base-v2` embeddings | Persistent client living under `data/scripts/chroma` (configurable via `CHROMA_PATH`). |
| Retrieval & API | Flask, Flask-CORS, SentenceTransformers, pandas, rotating log handlers | `/askQuery` returns ranked sections and optional LLM answers; reranking uses `cross-encoder/ms-marco-MiniLM-L-6-v2`. |
| Generator (optional) | Hugging Face Inference API or notebook tunnel | When `GENERATOR_URL` is set, backend proxies to the remote LLM with retrieved context. |
| Frontend | React 19, React Router, React Markdown, plain CSS modules | Chat UI, landing page, responsive layout, clipboard helpers, modal for sources. |
| Evaluation | Jupyter, NumPy/pandas, custom notebooks (`EVALUATION.ipynb`, `backendProcess.ipynb`) | Aggregates retrieval precision/recall, QA accuracy, and NLI-style agreement plots (`testing/evaluationPlots/`). |

## Key features
- **Retrieval-first answers** - Dense search over Kenyan Acts with optional act filters, reranking, and deterministic logging per query ID.
- **Generator proxy mode** - Seamlessly forward user prompts plus hydrated top-K sources to a hosted notebook or HF endpoint for abstractive reasoning.
- **Evidence transparency** - UI surfaces per-answer sources, lets users expand snippets, and stores all answers with metadata in `outputs/queryLog.csv`.
- **Stateful chat UX** - Sessions persist in `localStorage`, include copy-to-clipboard, typing indicators, disclaimers, and a header action to clear history.
- **Observability baked in** - Rotating backend logs, CSV audit trails, and evaluation plots (e.g., `testing/evaluationPlots/dist_NLI_QA.png`) simplify research reviews.

## Repository layout
```
.
|-- backend/                # Flask API, Chroma client helpers, reranker, logging
|-- frontend/               # React SPA with landing + chat pages
|-- data/                   # Raw and processed Acts, embeddings, scripts for ingestion
|-- notebooks/              # Experiment notebooks (e.g., backendProcess.ipynb)
|-- outputs/                # Runtime artifacts such as queryLog.csv
|-- testing/                # Evaluation datasets, notebooks, and plots
|-- .github/, .vscode/      # CI/prettier configs & IDE settings
`-- README.md               # You are here
```

## Data & knowledge pipeline
- **Raw corpora** - Gazette PDFs and DOC files live under `data/Original laws and acts/` and are progressively cleaned into machine-friendly JSON in `data/Cleaned acts/` and `data/ActsinJson/`.
- **Section chunking** - `data/scripts/actPreprocessing.py` and `splitChunks.py` detect parts, sections, and interpretations, then create overlapping windows (`chunk_size=150`, `overlap=20`) to preserve context while adhering to transformer limits.
- **Embeddings** - `data/scripts/createEmbeddings.py` encodes each chunk with `SentenceTransformer(intfloat/e5-base-v2)` (prefix-aware for query/passage format) and writes deterministic IDs so collections can be rebuilt or merged safely.
- **Vector persistence** - `data/scripts/chromaInit.py` and `createEmbeddings.py` connect to a persistent client (default `../data/scripts/chroma`) to create or update the `actSectionsV2` collection, ensuring reproducibility across machines.
- **Utility scripts** - `csvQuery.py`, `queryEmbeddings.py`, `singularQuestions.py`, and `modeBERTlDownload.py` support experimentation, bulk evaluation, and offline benchmarking.
- **Documentation notebooks** - `notebooks/backendProcess.ipynb` walks through ingestion/reranking experiments, complementing `testing/EVALUATION.ipynb` for QA scoring.

## Backend retrieval API
`backend/app.py` owns the Flask service that powers both the retrieval-only and proxy flows.

### Runtime profile
- Loads an embedding model once per process, pins `max_seq_length=512`, and keeps a persistent Chroma client open for low-latency queries.
- Applies optional cross-encoder fusion (`backend/reranker.py`) with configurable mixing factor (`CE_FUSION_ALPHA`).
- Writes every query to both rotating disk logs (`backend/logs/server.log`) and a CSV ledger (`outputs/queryLog.csv`) capped at 500 characters per top chunk.

### Running locally
```bash
cd backend
python -m venv .venv && .venv\Scripts\activate  # Windows PowerShell
pip install flask flask-cors pandas chromadb sentence-transformers requests
python app.py
```
The server prints `Starting Flask server on http://127.0.0.1:5000 ...` by default.

### Modes
- **Retrieval-only (default)** - When `GENERATOR_URL` is blank, `/askQuery` returns scored passages and optional concatenated context.
- **Proxy mode** - If `GENERATOR_URL` is set, the backend bundles retrieved IDs and metadata, forwards them to the remote generator, hydrates source snippets locally, and returns both the generator answer and retrieved context.

### Additional scripts
- `backend/embeddingTesting.py` - Sanity-check embeddings or run ad-hoc experiments.
- `backend/testFlask.py` - Minimal health-check app to debug networking or CORS settings.

## Frontend web app
- **Entry points** - `src/Pages/LandinPage.js` introduces the assistant, while `src/Pages/ChatPage.js` renders the full chat surface with disclaimer and composer anchored to the viewport.
- **Components** - `MessageList` renders markdown answers, supports clipboard operations, a "Sources used" modal, and a typing indicator; `MessageInput` autosizes and handles `Shift+Enter` for multi-line drafting; `Header` exposes a "Clear chat" trigger wired into a ref.
- **State & persistence** - Chat history is saved under the `uhaki_chat_history` key in `localStorage`, ensuring continuity across refreshes until manually cleared.
- **Styling** - CSS modules under `src/Styles/` provide responsive layout, theming, and animations without pulling in a heavyweight design system.

### Running the client
```bash
cd frontend
npm install
npm start          # defaults to http://localhost:3000 (override via PORT in frontend/.env)
```
During development, the app issues `fetch('http://localhost:5000/askQuery', ...)`; update this URL if the backend is hosted elsewhere.

## Evaluation & quality assurance
- **Datasets** - Curated QA and retrieval benchmarks (`uhakiRetrievalResults*.csv`, `uhakiEvaluationData*.csv`) are versioned under `testing/` for reproducible scoring.
- **Notebooks** - `testing/EVALUATION.ipynb` covers retrieval metrics, QA scoring, and error analysis pipelines; notebooks log decisions and hyperparameters side-by-side with outputs.
- **Plots & diagnostics** - Figures such as `testing/evaluationPlots/dist_NLI_QA.png` visualize distribution shifts in NLI-style QA grading, helping stakeholders gauge calibration.
- **Production telemetry** - `outputs/queryLog.csv` mirrors live usage, enabling comparison between offline evaluation and real-world queries.

## Quickstart
1. **Clone & install tooling** - Ensure Python 3.10+ and Node 18+ are installed.
2. **Prepare data** - Run the scripts in `data/scripts/` (see comments inside each script) to rebuild the Chroma collection or refresh embeddings when Acts are updated.
3. **Configure environment** - Copy `backend/.env` as needed, set `CHROMA_PATH`, `COLLECTION_NAME`, and (optionally) generator credentials; set `frontend/.env` `PORT` if you need a non-default dev server.
4. **Start backend** - `python backend/app.py` (or `flask run` if you prefer), verify `/health`.
5. **Start frontend** - `npm start` inside `frontend/` and navigate to `/ChatPage` to begin chatting.

## Configuration reference
| Variable | Default | Description |
| --- | --- | --- |
| `CHROMA_PATH` | `../data/scripts/chroma` | Path to persistent Chroma storage. |
| `COLLECTION_NAME` | `actSectionsV2` | Target vector collection name. |
| `HF_EMBED_MODEL` / `HF_MODEL` | `intfloat/e5-base-v2` | SentenceTransformer checkpoint for retrieval. |
| `TOP_K_RETRIEVE` / `TOP_K_RETURN` | `12 / 5` | How many results to fetch from Chroma vs. return to the caller. |
| `CSV_LOG` | `../outputs/queryLog.csv` | Where per-query audit rows are appended. |
| `GENERATOR_URL` | empty | Remote notebook or HF endpoint that receives proxy requests. |
| `NOTEBOOK_API_KEY` | empty | Shared secret sent as `X-API-Key` when proxying. |
| `HF_ENDPOINT_URL`, `HF_MODEL_ID`, `HF_TOKEN`, `HF_TEMPERATURE`, `HF_MAX_NEW_TOKENS`, `HF_TIMEOUT_S` | n/a | Used by generator notebooks or other downstream services. Do **not** commit live credentials. |
| `CE_*` (see `backend/reranker.py`) | n/a | Control local cross-encoder (paths, batch sizes, fusion weight). |
| `frontend/.env: PORT` | `4700` | Overrides CRA dev server port (default CRA is 3000 if unset). |

## API reference
- `GET /health` - Returns service mode, collection metadata, and embed model for monitoring.
- `POST /askQuery`
  - Body: `{"query": "...", "act": "optional filter", "top_k_retrieve": 12, "top_k_return": 5, "include_context": true}`
  - Response (retrieval mode):
    ```json
    {
      "request_id": "2a4ff25b",
      "query": "What does the Companies Act say about dividends?",
      "top_results": [
        {"id": "...", "act": "Companies Act", "section": "53", "score_after": 0.84, "text": "..."}
      ],
      "timings": {"embed_ms": 38.2, "chroma_ms": 22.4, "rerank_ms": 15.7, "total_ms": 79.1},
      "context": "[1] Companies Act - Section 53 ...",
      "proxy": false
    }
    ```
  - Response (proxy mode) additionally includes `answer`, upstream `timings`, and hydrated `top_results` from generator metadata.

### Curl example
```bash
curl -X POST http://localhost:5000/askQuery ^
  -H "Content-Type: application/json" ^
  -d "{\"query\":\"Explain maternity leave rights under the Employment Act\"}"
```

## Monitoring & analytics
- **Structured logs** - Rotate to `backend/logs/server.log` (5 MB x 3 files) with timestamps and request IDs; tail these files during debugging.
- **Query ledger** - `outputs/queryLog.csv` mirrors the latest query, top chunk metadata, and runtime for auditing or BI ingestion.
- **Evaluation plots** - `testing/evaluationPlots/` hosts static PNGs for quick communication with stakeholders; regenerate from the accompanying notebooks after each experiment.

## Testing
- **Backend** - Exercise `/health` and `/askQuery` manually or via integration tests (e.g., `pytest` + Flask test client) before releasing. Lightweight `backend/testFlask.py` helps isolate CORS issues.
- **Frontend** - Use Create React App's suites: `npm test` runs `@testing-library` specs; extend `src/App.test.js` or create additional component tests as the UI grows.
- **Evaluation harness** - The CSV datasets in `testing/` pair with notebooks to compute retrieval recall, QA exact match, and NLI-style agreement; re-run them whenever embeddings, reranker weights, or generator prompts change.

## Deployment checklist
- [ ] Refresh embeddings & Chroma collection when Acts are updated.
- [ ] Populate production-safe `.env` values (rotate secrets, set `LOG_LEVEL=INFO`).
- [ ] Enable HTTPS/CORS settings in `app.py` (Flask behind nginx or Gunicorn).
- [ ] Point the frontend to the deployed backend URL and rebuild (`npm run build`).
- [ ] Archive the latest `outputs/queryLog.csv` and evaluation plots for governance.

## Roadmap
- Replace manual act filter with a searchable dropdown powered by metadata facets.
- Add streaming responses and progressive rendering in the chat interface.
- Introduce user feedback capture (thumbs up/down) and surface it inside evaluation notebooks.
- Automate nightly regression tests that replay `testing/uhakiTestQuestions.csv` against the live stack.
- Package ingestion scripts as a CLI so new Acts can be onboarded with a single command.

## Resources & acknowledgements
- Kenyan legal documents courtesy of the participating research group and open government sources stored under `data/`.
- SentenceTransformer checkpoints (`intfloat/e5-base-v2`, `cross-encoder/ms-marco-MiniLM-L-6-v2`) via Hugging Face.
- Evaluation annotations powered by the CSV suites in `testing/` plus visualizations inside `testing/evaluationPlots/`.

## License
Specify the project license or add a `LICENSE` file to formalize usage rights.
