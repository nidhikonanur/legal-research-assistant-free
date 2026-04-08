import React, { useState } from 'react';

export default function App() {
  const [question, setQuestion] = useState('Can police search my car without a warrant?');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  async function submit(e) {
    e && e.preventDefault();
    setLoading(true);
    setError(null);
    setData(null);
    try {
      const resp = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question, reindex: false, page_size: 5 })
      });
      if (!resp.ok) {
        const err = await resp.json();
        throw new Error(err.detail || resp.statusText);
      }
      const json = await resp.json();
      setData(json);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="container">
      <h1>Legal Research Assistant — Free RAG</h1>
      <p>Uses CourtListener + local embeddings + local LLM (optional).</p>
      <form onSubmit={submit}>
        <label>
          Question
          <textarea value={question} onChange={(e)=>setQuestion(e.target.value)} />
        </label>
        <div>
          <button type="submit" disabled={loading}>{loading ? 'Searching...' : 'Search'}</button>
        </div>
      </form>

      {error && <div style={{color:'red'}}>{error}</div>}

      {data && (
        <div>
          <h2>Answer</h2>
          <div className="summary"><div dangerouslySetInnerHTML={{__html: data.answer.replace(/\n/g,'<br/>')}}/></div>
          <h3>Top documents</h3>
          {data.top_documents.map((d, i) => (
            <div key={i} className="result">
              <div><strong>Snippet:</strong></div>
              <pre style={{whiteSpace:'pre-wrap'}}>{d.text}</pre>
              <div className="citation"><strong>Meta:</strong> {d.metadata && d.metadata.get('case_name') ? d.metadata.get('case_name') : JSON.stringify(d.metadata)}</div>
            </div>
          ))}
          <h3>Search results</h3>
          {data.search_results.map(r=> (
            <div key={r.id} className="result">
              <div><strong>{r.case_name}</strong> — {r.date}</div>
              {r.url && <div><a href={r.url} target="_blank" rel="noreferrer">View opinion</a></div>}
            </div>
          ))}
          <h3>Citation graph (excerpt)</h3>
          {data.citation_graph.map(c=> (
            <div key={c.case_id} className="result">
              <div><strong>{c.case_name}</strong></div>
              <div><em>citations:</em></div>
              <pre style={{whiteSpace:'pre-wrap'}}>{JSON.stringify(c.citations, null, 2)}</pre>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
