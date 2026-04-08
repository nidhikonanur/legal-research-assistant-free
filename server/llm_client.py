import os, asyncio
import httpx

LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'ollama')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')

async def generate_summary(question: str, context: str, top_docs: list):
    """Generate a concise answer and explanation using the local LLM provider."""
    prompt = build_prompt_answer(question, context, top_docs)
    if LLM_PROVIDER == 'ollama':
        return await call_ollama(prompt)
    else:
        return dummy_generate(prompt)

async def generate_precise_answer(question: str, context: str):
    prompt = build_prompt_answer(question, context, [])
    if LLM_PROVIDER == 'ollama':
        return await call_ollama(prompt)
    else:
        return dummy_generate(prompt)

def build_prompt_answer(question, context, top_docs):
    # Build a template instructing the local LLM to produce structured output
    return f"""You are a legal research assistant. Use the provided case excerpts and produce:
1) A concise answer to the user's question (2-4 sentences).
2) Key legal rule(s) and holdings extracted from the excerpts (bullet list).
3) A short precedent chain / how the cited cases relate (2-4 sentences).
4) For transparency, include which passages (by case name and short id) you relied on.

User question: {question}

Context excerpts:
{context}

Provide the answer in markdown. """

async def call_ollama(prompt: str):
    # Ollama's text-generation endpoint (assumes /api/generate or similar)
    # This function is intentionally general; please adjust for your local Ollama setup.
    url = OLLAMA_URL.rstrip('/') + '/api/generate'
    payload = {
        'model': 'llama2',  # user can change model locally
        'prompt': prompt,
        'max_tokens': 800
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        r = await client.post(url, json=payload)
        r.raise_for_status()
        data = r.json()
        # adapt depending on provider response shape
        # Ollama/other servers may return 'content' or 'response'
        text = ''
        if isinstance(data, dict):
            text = data.get('text') or data.get('response') or data.get('content') or str(data)
        else:
            text = str(data)
        return text

def dummy_generate(prompt: str):
    # Short heuristic summary used for offline testing
    return """**Answer (dummy):** Based on the retrieved cases, in general police need a warrant to search a car unless exigent circumstances or consent are present.\n\n**Key rules:**\n- Warrant required absent exigent circumstances.\n- Consent exceptions; probable cause exceptions.\n\n**Precedent chain:**\n- Case A applied the warrant rule; Case B carved out exigent circumstances.\n\n**Cited passages:**\n- case_12345_0, case_67890_2"""
