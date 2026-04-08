import os
import asyncio
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
from embeddings import EmbeddingIndex, chunk_text, DEFAULT_CHUNK_SIZE
from llm_client import generate_summary, generate_precise_answer
import uvicorn

load_dotenv()
PORT = int(os.getenv('PORT', '3000'))
COURTLISTENER_API_KEY = os.getenv('COURTLISTENER_API_KEY', '').strip()
TOP_K = int(os.getenv('TOP_K', '4'))

app = FastAPI(title='Legal Research Assistant - Free RAG')

index = EmbeddingIndex(persist_directory='vector_store')

class Query(BaseModel):
    question: str
    reindex: bool = False
    page_size: int = 5

@app.on_event('startup')
async def startup_event():
    # ensure index is ready (loads persisted DB if present)
    index.load_if_exists()

@app.post('/api/search')
async def search(q: Query):
    if not q.question:
        raise HTTPException(status_code=400, detail='question required')

    # 1) Use CourtListener search endpoint to find relevant opinions
    search_url = f'https://www.courtlistener.com/api/rest/v3/search/?q={httpx.utils.quote(q.question)}&type=o&page_size={q.page_size}'
    headers = {}
    if COURTLISTENER_API_KEY:
        headers['Authorization'] = f'token {COURTLISTENER_API_KEY}'
    async with httpx.AsyncClient(timeout=30.0) as client:
        resp = await client.get(search_url, headers=headers)
        resp.raise_for_status()
        data = resp.json()

    results = []
    # 2) For each hit, fetch the opinion text (opinion endpoint is better but we try absolute_url)
    for hit in data.get('results', []):
        case_id = hit.get('id')
        case_name = hit.get('caseName') or hit.get('name') or hit.get('title') or ''
        absolute_url = hit.get('absolute_url') or hit.get('html_url') or ''
        date_filed = hit.get('date_filed') or hit.get('date') or ''
        snippet = hit.get('excerpt') or hit.get('snippet') or ''

        opinion_text = snippet
        if absolute_url:
            try:
                r = await client.get(absolute_url, timeout=20.0)
                text = r.text
                # crude HTML -> text remove tags
                import re
                clean = re.sub(r'<script[\s\S]*?<\/script>', ' ', text)
                clean = re.sub(r'<[^>]+>', ' ', clean)
                opinion_text = clean.strip()
            except Exception:
                pass

        # split into passages and add to index (only if not already present)
        passages = chunk_text(opinion_text, chunk_size=DEFAULT_CHUNK_SIZE)
        meta = {'id': case_id, 'case_name': case_name, 'url': absolute_url, 'date': date_filed}
        index.add_documents(passages, metadatas=[meta]*len(passages), ids_prefix=f'case_{case_id}')

        results.append({'id': case_id, 'case_name': case_name, 'url': absolute_url, 'date': date_filed})

    # 3) Retrieve top passages from the vector store for the question
    docs = index.similarity_search(q.question, k=TOP_K)

    # 4) Produce an answer using local LLM (or dummy)
    context = '\n\n---\n\n'.join([d['text'] for d in docs])
    summary = await generate_summary(question=q.question, context=context, top_docs=docs)

    # 5) Build citation graph for the top results (best-effort)
    citation_info = []
    for r in results:
        try:
            opinion_meta = await fetch_citation_graph(r['id'])
            citation_info.append({'case_id': r['id'], 'case_name': r['case_name'], 'citations': opinion_meta})
        except Exception as e:
            citation_info.append({'case_id': r['id'], 'case_name': r['case_name'], 'citations': [], 'error': str(e)})

    return {'question': q.question, 'answer': summary, 'top_documents': docs, 'search_results': results, 'citation_graph': citation_info}

async def fetch_citation_graph(case_id: int):
    # CourtListener opinions/{id}/citations/ endpoint (best-effort)
    url = f'https://www.courtlistener.com/api/rest/v3/opinions/{case_id}/citations/'
    headers = {}
    if COURTLISTENER_API_KEY:
        headers['Authorization'] = f'token {COURTLISTENER_API_KEY}'
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url, headers=headers)
        if r.status_code != 200:
            return []
        j = r.json()
        # extract minimal citation info
        entries = []
        for item in j.get('results', []):
            entries.append({'cites_to': item.get('cited'), 'cites_from': item.get('citing'), 'raw': item})
        return entries

if __name__ == '__main__':
    uvicorn.run('main:app', host='0.0.0.0', port=PORT, reload=True)
