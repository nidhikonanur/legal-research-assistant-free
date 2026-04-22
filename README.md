# Legal Research Assistant

A React + FastAPI legal research app for public-facing case-law search workflows. It combines CourtListener search, local embeddings with Chroma, and optional local answer generation through Ollama.

## Current Status

The app now supports:

1. authenticated CourtListener search with a required API key
2. opinion-text retrieval through the CourtListener opinions API
3. local passage chunking, embedding, and similarity search
4. a redesigned public-facing frontend with structured results
5. answer generation through Ollama, with a clean fallback summary when Ollama is unavailable

## Tech Stack

- Frontend: React + Vite
- Backend: FastAPI
- Retrieval: ChromaDB + sentence-transformers
- Data source: CourtListener REST API
- Optional local LLM: Ollama

## Project Structure

```text
.
├── client/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   └── styles.css
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── server/
│   ├── main.py
│   ├── embeddings.py
│   ├── llm_client.py
│   ├── requirements.txt
│   └── vector_store/
├── .env.example
└── README.md
```

## Requirements

- Python 3.10+
- Node.js 18+
- npm
- CourtListener API key
- Optional: Ollama installed locally

## Environment Variables

Copy the example file first:

```bash
cp .env.example .env
```

Then configure:

- `PORT`: backend port
- `COURTLISTENER_API_KEY`: required for CourtListener search
- `LLM_PROVIDER`: `ollama` or `dummy`
- `OLLAMA_URL`: local Ollama endpoint, usually `http://localhost:11434`
- `OLLAMA_MODEL`: model name to call through Ollama
- `TOP_K`: number of retrieved passages returned to the answer stage

Example:

```env
PORT=3000
COURTLISTENER_API_KEY=your_token_here
LLM_PROVIDER=ollama
OLLAMA_URL=http://localhost:11434
OLLAMA_MODEL=llama2
TOP_K=4
```

## Running the App

### Backend

```bash
cd /Users/nidhikonanur/Documents/Playground/legal-research-assistant-free/server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 127.0.0.1 --port 3000
```

### Frontend

Open a second terminal:

```bash
cd /Users/nidhikonanur/Documents/Playground/legal-research-assistant-free/client
npm install
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173).

## Ollama Setup

If you want real local LLM answers instead of fallback summaries:

1. install Ollama
2. start the Ollama server
3. make sure the configured model exists locally

Typical example:

```bash
ollama serve
```

In another terminal:

```bash
ollama run llama2
```

If Ollama is not available, the backend will still return a clean summary response based on retrieved passages.

## CourtListener Setup

CourtListener now requires authenticated API requests for search. Create an account, generate an API token, and place it in `.env`:

```env
COURTLISTENER_API_KEY=your_token_here
```

Without this key, `/api/search` returns a clear configuration error.

## API

### `POST /api/search`

Example request:

```json
{
  "question": "Can police search my car without a warrant?",
  "reindex": false,
  "page_size": 5
}
```

Example response shape:

```json
{
  "question": "...",
  "answer": "...",
  "top_documents": [],
  "search_results": [],
  "citation_graph": []
}
```

## Implementation Notes

- The backend now uses the CourtListener opinions API for opinion text instead of scraping public HTML pages.
- Chroma integration has been updated for newer client behavior.
- Retrieved passages are embedded locally and persisted in `server/vector_store/`.
- The frontend formats answer text into styled headings and bullet lists.
- If a local LLM call fails, the app falls back to a public-friendly retrieval summary rather than exposing raw placeholder wording.

## Known Limitations

- Retrieval quality depends on the available CourtListener opinion text.
- Repeated searches can add overlapping passages to the local vector store over time.
- Citation graph output is still raw JSON and could be visualized more cleanly.
- Without Ollama, the answer is a retrieval-based fallback summary rather than a model-generated memo.

## Good Next Steps

- add deduplication for repeated indexed passages
- improve citation graph presentation
- support filters for court, jurisdiction, and date
- add tests for indexing and search behavior
- make Ollama model selection configurable through the UI

## Disclaimer

This project is for educational and research use only. It is not legal advice.
