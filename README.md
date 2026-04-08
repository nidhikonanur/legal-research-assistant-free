# Legal Research Assistant — Free RAG Version (No OpenAI)

This project is a **free** alternative to the previous starter project. It uses:

- **CourtListener** for case law data (free)
- **Chroma (chromadb)** for vector storage (local, free)
- **sentence-transformers** embeddings (local, free)
- **A local LLM endpoint** (recommended: Ollama, Text-Generation-Inference, or local Llama) to produce natural-language summaries — **no OpenAI**
  - The server can call an Ollama HTTP API at `http://localhost:11434` (configurable) or use a "synchronous" dummy generator for offline testing.
- **FastAPI** backend + a small React (Vite) frontend

## Features
- RAG pipeline: search CourtListener, fetch opinions, split into passages, embed and index in Chroma, then retrieve best passages for a query.
- Summarization & doctrinal explanation via a local LLM endpoint (Ollama recommended) — configurable in `.env`.
- Citation graph / precedent-chain: for each result, fetch citations (cases it cites and cases citing it) and present a small graph in the UI.
- Persistent Chroma DB in `vector_store/` so you don't re-embed everything each run (you can re-index on demand).

## Quickstart (Linux / macOS)
1. Install Python 3.10+ and Node 18+.
2. Copy `.env.example` to `.env` and configure:
   - `LLM_PROVIDER` = `ollama` or `dummy`
   - `OLLAMA_URL` = `http://localhost:11434` (if using Ollama)
   - `COURTLISTENER_API_KEY` optional
   - `PORT` server port
3. Create a virtualenv and install Python deps:
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r server/requirements.txt
   ```
4. Install node deps and run client:
   ```bash
   cd client
   npm install
   npm run dev
   ```
5. Run the server:
   ```bash
   cd server
   uvicorn main:app --reload --port 3000
   ```
6. Go to http://localhost:5173

## Notes on local LLMs
- **Ollama** is recommended for ease of use. Run a model like `llama2` or `mistral` locally and enable the Ollama HTTP server.
- If you don't have a local LLM, set `LLM_PROVIDER=dummy` in `.env` to get short heuristic summaries (useful for offline testing).

## Files of interest
- `server/main.py` — FastAPI app implementing RAG index, endpoints for search, index, and citation graph.
- `server/embeddings.py` — embedding creation with sentence-transformers and Chroma helper functions.
- `server/llm_client.py` — wrapper to call local LLM (Ollama) or dummy generator.
- `client/` — React frontend that queries the server and visualizes results and precedent chains.

## Disclaimer
This is an educational tool. Do not rely on it for legal advice.
