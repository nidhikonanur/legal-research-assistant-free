import os
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from dotenv import load_dotenv
import httpx
from urllib.parse import quote
from embeddings import EmbeddingIndex, chunk_text, DEFAULT_CHUNK_SIZE
from llm_client import generate_summary
import uvicorn

load_dotenv()
PORT = int(os.getenv('PORT', '3000'))
COURTLISTENER_API_KEY = os.getenv('COURTLISTENER_API_KEY', '').strip()
TOP_K = int(os.getenv('TOP_K', '4'))
COURTLISTENER_BASE_URL = 'https://www.courtlistener.com'

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
    question = q.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail='question required')
    if not COURTLISTENER_API_KEY:
        raise HTTPException(
            status_code=503,
            detail='COURTLISTENER_API_KEY is required to search CourtListener. Add it to your .env file.',
        )

    # 1) Use CourtListener search endpoint to find relevant opinions
    search_url = f'{COURTLISTENER_BASE_URL}/api/rest/v3/search/?q={quote(question)}&type=o&page_size={q.page_size}'
    headers = {}
    if COURTLISTENER_API_KEY:
        headers['Authorization'] = f'token {COURTLISTENER_API_KEY}'
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            resp = await client.get(search_url, headers=headers)
            resp.raise_for_status()
        except httpx.HTTPError as exc:
            raise HTTPException(status_code=502, detail=f'CourtListener search failed: {exc}') from exc

        data = resp.json()

        results = []
        # 2) For each hit, fetch the opinion text (opinion endpoint is better but we try absolute_url)
        for hit in data.get('results', [])[: q.page_size]:
            case_id = hit.get('id')
            case_name = hit.get('caseName') or hit.get('name') or hit.get('title') or ''
            absolute_url = normalize_courtlistener_url(hit.get('absolute_url') or hit.get('html_url') or '')
            date_filed = hit.get('date_filed') or hit.get('date') or ''
            snippet = hit.get('excerpt') or hit.get('snippet') or ''

            opinion_text = await fetch_opinion_text(client, case_id, snippet)

            passages = chunk_text(opinion_text, chunk_size=DEFAULT_CHUNK_SIZE)
            meta = {'id': case_id, 'case_name': case_name, 'url': absolute_url, 'date': date_filed}
            index.add_documents(passages, metadatas=[meta] * len(passages), ids_prefix=f'case_{case_id}')

            results.append({'id': case_id, 'case_name': case_name, 'url': absolute_url, 'date': date_filed})

    # 3) Retrieve top passages from the vector store for the question
    docs = index.similarity_search(question, k=TOP_K)

    # 4) Produce an answer using local LLM (or dummy)
    context = '\n\n---\n\n'.join([d['text'] for d in docs])
    summary = await generate_summary(question=question, context=context, top_docs=docs)

    # 5) Build citation graph for the top results (best-effort)
    citation_info = []
    for r in results:
        try:
            opinion_meta = await fetch_citation_graph(r['id'])
            citation_info.append({'case_id': r['id'], 'case_name': r['case_name'], 'citations': opinion_meta})
        except Exception as e:
            citation_info.append({'case_id': r['id'], 'case_name': r['case_name'], 'citations': [], 'error': str(e)})

    return {'question': question, 'answer': summary, 'top_documents': docs, 'search_results': results, 'citation_graph': citation_info}

def normalize_courtlistener_url(url: str) -> str:
    if not url:
        return ''
    if url.startswith('http://') or url.startswith('https://'):
        return url
    return f'{COURTLISTENER_BASE_URL}{url}'

def html_to_text(value: str) -> str:
    if not value:
        return ''
    clean = re.sub(r'<script[\s\S]*?<\/script>', ' ', value)
    clean = re.sub(r'<style[\s\S]*?<\/style>', ' ', clean)
    clean = re.sub(r'<[^>]+>', ' ', clean)
    clean = re.sub(r'\s+', ' ', clean)
    return clean.strip()

async def fetch_opinion_text(client: httpx.AsyncClient, case_id: int, fallback_snippet: str = '') -> str:
    if not case_id:
        return fallback_snippet or ''

    url = f'{COURTLISTENER_BASE_URL}/api/rest/v3/opinions/{case_id}/'
    headers = {}
    if COURTLISTENER_API_KEY:
        headers['Authorization'] = f'token {COURTLISTENER_API_KEY}'

    try:
        response = await client.get(url, headers=headers, timeout=20.0)
        response.raise_for_status()
    except Exception:
        return fallback_snippet or ''

    payload = response.json()
    candidates = [
        payload.get('plain_text'),
        payload.get('html_with_citations'),
        payload.get('html_lawbox'),
        payload.get('html'),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        if '<' in candidate and '>' in candidate:
            text = html_to_text(candidate)
        else:
            text = candidate.strip()
        if text:
            return text

    return fallback_snippet or ''

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
