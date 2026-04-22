import React, { useState } from 'react';

function formatDate(value) {
  if (!value) return 'Date unavailable';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
}

function formatDistance(value) {
  if (value == null) return null;
  return Number(value).toFixed(3);
}

function snippetPreview(text, maxLength = 420) {
  if (!text) return 'No passage text available.';
  if (text.length <= maxLength) return text;
  return `${text.slice(0, maxLength).trim()}...`;
}

function renderInlineMarkdown(text) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return <strong key={`${part}-${index}`}>{part.slice(2, -2)}</strong>;
    }
    return <React.Fragment key={`${part}-${index}`}>{part}</React.Fragment>;
  });
}

function formatAnswer(answer) {
  if (!answer) {
    return [];
  }

  const lines = answer
    .split('\n')
    .map((line) => line.trim())
    .filter((line, index, all) => line || all[index - 1] !== '');

  const blocks = [];
  let bulletBuffer = [];

  const flushBullets = () => {
    if (bulletBuffer.length) {
      blocks.push({ type: 'list', items: bulletBuffer });
      bulletBuffer = [];
    }
  };

  lines.forEach((line) => {
    if (!line) {
      flushBullets();
      return;
    }

    if (line.startsWith('- ')) {
      bulletBuffer.push(line.slice(2));
      return;
    }

    flushBullets();

    const headingMatch = line.match(/^\*\*(.+?)\*\*:?\s*(.*)$/);
    if (headingMatch) {
      blocks.push({
        type: 'section',
        title: headingMatch[1],
        content: headingMatch[2]
      });
      return;
    }

    blocks.push({ type: 'paragraph', content: line });
  });

  flushBullets();
  return blocks;
}

export default function App() {
  const [question, setQuestion] = useState('Can police search my car without a warrant?');
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const answerBlocks = formatAnswer(data?.answer || '');

  const stats = !data
    ? [
        { label: 'Retrieved Passages', value: '0' },
        { label: 'Cases Found', value: '0' },
        { label: 'Citation Links', value: '0' }
      ]
    : [
        { label: 'Retrieved Passages', value: String((data.top_documents || []).length) },
        { label: 'Cases Found', value: String((data.search_results || []).length) },
        { label: 'Citation Links', value: String((data.citation_graph || []).length) }
      ];

  async function submit(e) {
    e && e.preventDefault();
    const trimmedQuestion = question.trim();
    if (!trimmedQuestion) {
      setError('Please enter a legal research question.');
      return;
    }

    setLoading(true);
    setError(null);
    setData(null);

    try {
      const resp = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ question: trimmedQuestion, reindex: false, page_size: 5 })
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
    <div className="appShell">
      <div className="backgroundGlow glowLeft" />
      <div className="backgroundGlow glowRight" />

      <main className="page">
        <section className="hero">
          <div className="heroCopy">
            <div className="eyebrow">CourtListener-powered legal research</div>
            <h1>Legal Research Assistant</h1>
            <p className="heroText">
              Search live case law, extract relevant passages, and generate a concise legal research
              memo from the strongest sources.
            </p>
          </div>

          <div className="heroStats">
            {stats.map((item) => (
              <div key={item.label} className="statCard">
                <div className="statValue">{item.value}</div>
                <div className="statLabel">{item.label}</div>
              </div>
            ))}
          </div>
        </section>

        <section className="panel searchPanel">
          <div className="panelHeader">
            <div>
              <div className="panelEyebrow">Research Query</div>
              <h2>Ask a legal question</h2>
            </div>
            <div className="statusPill">{loading ? 'Searching now' : 'Ready'}</div>
          </div>

          <form onSubmit={submit} className="searchForm">
            <label className="fieldLabel" htmlFor="legal-question">
              Enter the issue, doctrine, or fact pattern you want to investigate.
            </label>
            <textarea
              id="legal-question"
              className="questionInput"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Example: When can police search a vehicle without a warrant under the automobile exception?"
            />
            <div className="actionRow">
              <button className="primaryButton" type="submit" disabled={loading}>
                {loading ? 'Searching...' : 'Search Case Law'}
              </button>
              <span className="helperText">CourtListener search + local retrieval + Ollama answer generation</span>
            </div>
          </form>

          {error && <div className="errorBanner">{error}</div>}
        </section>

        {data && (
          <section className="resultsLayout">
            <article className="panel answerPanel">
              <div className="panelHeader">
                <div>
                  <div className="panelEyebrow">Answer</div>
                  <h2>Research summary</h2>
                </div>
                <div className="statusPill subdued">Question analyzed</div>
              </div>
              <div className="answerText">
                {answerBlocks.length ? (
                  answerBlocks.map((block, index) => {
                    if (block.type === 'section') {
                      return (
                        <div key={`section-${index}`} className="answerBlock">
                          <div className="answerLabel">{block.title}</div>
                          {block.content ? (
                            <p className="answerParagraph">{renderInlineMarkdown(block.content)}</p>
                          ) : null}
                        </div>
                      );
                    }

                    if (block.type === 'list') {
                      return (
                        <ul key={`list-${index}`} className="answerList">
                          {block.items.map((item, itemIndex) => (
                            <li key={`item-${itemIndex}`}>{renderInlineMarkdown(item)}</li>
                          ))}
                        </ul>
                      );
                    }

                    return (
                      <p key={`paragraph-${index}`} className="answerParagraph">
                        {renderInlineMarkdown(block.content)}
                      </p>
                    );
                  })
                ) : (
                  <p className="answerParagraph">No answer was returned.</p>
                )}
              </div>
            </article>

            <section className="panel">
              <div className="panelHeader">
                <div>
                  <div className="panelEyebrow">Retrieved Passages</div>
                  <h2>Most relevant excerpts</h2>
                </div>
              </div>
              <div className="stack">
                {(data.top_documents || []).map((doc, index) => (
                  <article key={`${doc.id || 'doc'}-${index}`} className="infoCard">
                    <div className="cardMetaRow">
                      <span className="cardTag">Passage {index + 1}</span>
                      {formatDistance(doc.distance) && (
                        <span className="metricPill">Distance {formatDistance(doc.distance)}</span>
                      )}
                    </div>
                    <h3>{doc.metadata?.case_name || 'Unnamed case'}</h3>
                    <p className="snippetText">{snippetPreview(doc.text)}</p>
                    <div className="metaLine">
                      {doc.metadata?.date ? formatDate(doc.metadata.date) : 'Date unavailable'}
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="panel">
              <div className="panelHeader">
                <div>
                  <div className="panelEyebrow">Cases</div>
                  <h2>Search results</h2>
                </div>
              </div>
              <div className="stack">
                {(data.search_results || []).map((result) => (
                  <article key={result.id} className="infoCard resultCard">
                    <div className="cardMetaRow">
                      <span className="cardTag">Case</span>
                      <span className="metaLine">{formatDate(result.date)}</span>
                    </div>
                    <h3>{result.case_name}</h3>
                    {result.url && (
                      <a className="textLink" href={result.url} target="_blank" rel="noreferrer">
                        Open opinion
                      </a>
                    )}
                  </article>
                ))}
              </div>
            </section>

            <section className="panel">
              <div className="panelHeader">
                <div>
                  <div className="panelEyebrow">Citations</div>
                  <h2>Citation graph</h2>
                </div>
              </div>
              <div className="stack">
                {(data.citation_graph || []).map((item) => (
                  <article key={item.case_id} className="infoCard citationCard">
                    <div className="cardMetaRow">
                      <span className="cardTag">Case ID {item.case_id}</span>
                      <span className="metricPill">{(item.citations || []).length} citations</span>
                    </div>
                    <h3>{item.case_name}</h3>
                    <pre className="citationText">
                      {JSON.stringify(item.citations || [], null, 2)}
                    </pre>
                  </article>
                ))}
              </div>
            </section>
          </section>
        )}
      </main>
    </div>
  );
}
