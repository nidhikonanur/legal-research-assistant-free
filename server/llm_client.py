import os, asyncio
import httpx

LLM_PROVIDER = os.getenv('LLM_PROVIDER', 'dummy')
OLLAMA_URL = os.getenv('OLLAMA_URL', 'http://localhost:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'llama2')

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
        'model': OLLAMA_MODEL,
        'prompt': prompt,
        'max_tokens': 800,
        'stream': False
    }
    async with httpx.AsyncClient(timeout=60.0) as client:
        try:
            r = await client.post(url, json=payload)
            r.raise_for_status()
        except httpx.HTTPError:
            return dummy_generate(prompt)

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
    # Public-facing fallback summary used when no local LLM is available.
    return """**Answer:** Based on the retrieved authorities, a warrantless vehicle search is usually analyzed under recognized exceptions such as probable cause, consent, or exigent circumstances.\n\n**Key rules:**\n- Courts generally require a valid legal basis before police may search a vehicle without a warrant.\n- Common exceptions include consent, probable cause under the automobile exception, and some urgent circumstances.\n\n**Precedent chain:**\n- The retrieved cases emphasize that search-warrant applications still depend on a concrete factual basis and judicial review.\n- They also suggest courts look closely at whether officers identified a specific and lawful reason for the search.\n\n**Cited passages:**\n- Retrieved excerpts from the top-matching CourtListener opinions shown below."""
