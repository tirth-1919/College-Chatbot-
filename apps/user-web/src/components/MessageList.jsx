import React from 'react';
import logoIcon from '../../public/ai-faq-college-chat-bot-icon.svg';
import {
  CheckCircle2, ExternalLink, ShieldCheck, Copy,
  ThumbsUp, ThumbsDown, Check, Sparkles
} from 'lucide-react';

export function MessageList({
  messages,
  streamingDelta,
  streamingBlocks,
  isStreaming,
  onSelectSuggestion,
  onImageClick,
  onSendMessage,
  onCollegeSwitch
}) {
  const [copiedId, setCopiedId] = React.useState(null);
  const [feedbackMap, setFeedbackMap] = React.useState({});
  const [reasonFor, setReasonFor] = React.useState(null); // message id with open 👎 popover
  const [reportedMap, setReportedMap] = React.useState({});

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const submitFeedback = async (messageId, payload) => {
    const { apiClient } = await import('../services/api.js');
    return apiClient.authFetch('/api/v1/chat/feedback', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message_id: messageId, ...payload })
    });
  };

  const handleFeedback = async (messageId, rating) => {
    // Allow changing 👍 → 👎: submit always, only guard repeated identical clicks.
    if (!messageId || feedbackMap[messageId] === rating) return;
    setFeedbackMap(prev => ({ ...prev, [messageId]: rating }));
    try {
      await submitFeedback(messageId, { rating });
    } catch (err) {
      console.error('Feedback error:', err);
    }
  };

  const handleNegativeWithReason = async (messageId, reason, details) => {
    setReasonFor(null);
    setFeedbackMap(prev => ({ ...prev, [messageId]: -1 }));
    try {
      await submitFeedback(messageId, { feedback_type: 'NEGATIVE', reason, details });
    } catch (err) {
      console.error('Feedback error:', err);
    }
  };

  const handleReport = async (messageId, reason, details) => {
    setReasonFor(null);
    setReportedMap(prev => ({ ...prev, [messageId]: true }));
    try {
      await submitFeedback(messageId, { feedback_type: 'REPORT', reason, details });
    } catch (err) {
      console.error('Report error:', err);
    }
  };

  return (
    <div className="messages-scroll-area">
      {messages.map((msg, index) => {
        const isUser = msg.sender === 'user';
        return (
          <div key={msg.id || index} className={`message-row ${isUser ? 'user' : 'assistant'}`}>
            {!isUser && (
              <div className="message-avatar assistant">
                <img src={logoIcon} alt="AI FAQ College Chat Bot logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              </div>
            )}

            <div className="message-content-box">
              <div className="message-bubble">
                {/* Text Content: source metadata is rendered below through MessageBlocks only. */}
                <div style={{ whiteSpace: 'pre-wrap' }}>
                  {msg.content}
                </div>

                {/* Structured Blocks (Images, Citations, Provenance, Suggestions) */}
                {msg.blocks && msg.blocks.length > 0 && (
                  <MessageBlocks
                    blocks={mergeMessageMetadata(msg)}
                    query={messages.slice(0, index).reverse().find(item => item.sender === 'user')?.content || ''}
                    onImageClick={onImageClick}
                    onSelectSuggestion={onSelectSuggestion}
                    onCollegeSwitch={onCollegeSwitch}
                  />
                )}
              </div>

              {/* Message Actions for Assistant */}
              {!isUser && (
                <div style={{ position: 'relative', display: 'flex', alignItems: 'center', gap: '8px', padding: '2px 4px' }}>
                  <button
                    className="item-action-icon"
                    onClick={() => handleCopy(msg.id, msg.content)}
                    title="Copy message"
                  >
                    {copiedId === msg.id ? <Check size={14} color="var(--ait-emerald)" /> : <Copy size={14} />}
                  </button>
                  <button
                    className={`item-action-icon ${feedbackMap[msg.id] === 1 ? 'active-thumbs-up' : ''}`}
                    title="Helpful"
                    onClick={() => handleFeedback(msg.id, 1)}
                    style={{ color: feedbackMap[msg.id] === 1 ? '#10b981' : undefined }}
                  >
                    <ThumbsUp size={14} />
                  </button>
                  <button
                    className={`item-action-icon ${feedbackMap[msg.id] === -1 ? 'active-thumbs-down' : ''}`}
                    title="Not helpful"
                    onClick={() => setReasonFor(reasonFor === msg.id ? null : msg.id)}
                    style={{ color: feedbackMap[msg.id] === -1 ? '#ef4444' : undefined }}
                  >
                    <ThumbsDown size={14} />
                  </button>
                  {!reportedMap[msg.id] && (
                    <button
                      className="item-action-icon"
                      title="Report information"
                      style={{ fontSize: '0.72rem', padding: '2px 6px' }}
                      onClick={() => setReasonFor(reasonFor === msg.id ? null : `report:${msg.id}`)}
                    >
                      Report
                    </button>
                  )}
                  {reportedMap[msg.id] && (
                    <span style={{ fontSize: '0.72rem', color: '#f59e0b' }}>Reported ✓</span>
                  )}
                  {feedbackMap[msg.id] && (
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: 4 }}>
                      ✓ Thanks. Your feedback has been recorded.
                    </span>
                  )}

                  {/* 👎 / Report reason popover (§3/§4) */}
                  {reasonFor && (reasonFor === msg.id || reasonFor === `report:${msg.id}`) && (
                    <FeedbackReasonPopover
                      mode={reasonFor === msg.id ? 'negative' : 'report'}
                      onSubmit={(reason, details) => {
                        if (reasonFor === msg.id) handleNegativeWithReason(msg.id, reason, details);
                        else handleReport(msg.id, reason, details);
                      }}
                      onClose={() => setReasonFor(null)}
                    />
                  )}

                  {/* P1-15: Dynamic Authority / Grounding Badges */}
                  {msg.grounding_status === 'verified' && (
                    <span style={{ fontSize: '0.72rem', color: 'var(--ait-emerald, #10b981)', display: 'flex', alignItems: 'center', gap: '4px', marginLeft: 'auto' }}>
                      <ShieldCheck size={13} /> {/WEBSITE/.test(msg.provenance?.source_type || '') ? 'Official College Website' : msg.provenance?.source_type === 'DATABASE' ? 'Verified College Database' : 'Verified College Fact'}
                    </span>
                  )}
                  {msg.grounding_status === 'unverified' && (
                    <span style={{ fontSize: '0.72rem', color: '#f59e0b', display: 'flex', alignItems: 'center', gap: '4px', marginLeft: 'auto' }}>
                      <Sparkles size={13} /> ⚠ Gemini-generated — not verified by the college
                    </span>
                  )}
                  {msg.grounding_status === 'user_context' && (
                    <span style={{ fontSize: '0.72rem', color: '#6366f1', display: 'flex', alignItems: 'center', gap: '4px', marginLeft: 'auto' }}>
                      <ShieldCheck size={13} /> User Document Context
                    </span>
                  )}
                </div>
              )}
            </div>

            {isUser && (
              <div className="message-avatar user">
                U
              </div>
            )}
          </div>
        );
      })}

      {/* Real-time Streaming Message */}
      {isStreaming && (
        <div className="message-row assistant">
          <div className="message-avatar assistant">
            <img src={logoIcon} alt="AI FAQ College Chat Bot logo" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
          </div>
          <div className="message-content-box">
            <div className="message-bubble">
              <div style={{ whiteSpace: 'pre-wrap' }}>
                {streamingDelta || 'Thinking...'}
              </div>
              {streamingBlocks && streamingBlocks.length > 0 && (
                <MessageBlocks
                  blocks={streamingBlocks}
                  query={messages.filter(item => item.sender === 'user').at(-1)?.content || ''}
                  onImageClick={onImageClick}
                  onSelectSuggestion={onSelectSuggestion}
                  onCollegeSwitch={onCollegeSwitch}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function mergeMessageMetadata(message) {
  const blocks = [...(message.blocks || [])];
  if (message.citations?.length && !blocks.some(block => block.type === 'citation')) {
    blocks.push({ type: 'citation', items: message.citations });
  }
  if (message.provenance && !blocks.some(block => block.type === 'provenance')) {
    blocks.push({ type: 'provenance', ...message.provenance });
  }
  return blocks;
}

function MessageBlocks({ blocks, query = '', onImageClick, onSelectSuggestion, onCollegeSwitch }) {
  // Retrieval metadata is never rendered as answer text. Only citation records that
  // are relevant to this answer are exposed as source cards.
  const images = blocks.filter(b => b.type === 'image');
  const citations = dedupeRelevantCitations(
    blocks.filter(b => b.type === 'citation').flatMap(b => b.items || []),
    `${query} ${blocks.find(b => b.type === 'text')?.content || ''}`
  );
  const provenance = blocks.find(b => b.type === 'provenance');
  const suggestions = blocks.find(b => b.type === 'suggested_action');
  const switchPrompt = blocks.find(b => b.type === 'college_switch_prompt');

  return (
    <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {/* College switch confirmation (§22/§61): explicit [Switch] / [Stay] actions.
          The backend /college-context/switch endpoint does the authoritative
          persistence — this only triggers the call. */}
      {switchPrompt && onCollegeSwitch && (
        <CollegeSwitchPromptButtons
          prompt={switchPrompt}
          onCollegeSwitch={onCollegeSwitch}
        />
      )}
      {/* P0 Verified Image Gallery */}
      {images.length > 0 && (
        <div className="image-gallery-grid">
          {images.map((img, i) => (
            <div key={i} className="verified-image-card" onClick={() => onImageClick(img)}>
              <img src={img.url} alt={img.alt || img.title} loading="lazy" />
              <div className="verified-badge">
                <CheckCircle2 size={11} /> Verified
              </div>
              <div className="image-overlay">
                <div className="image-title">{img.title}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Relevant citations only: never leak the raw retrieved-source list. */}
      {citations.length > 0 && (
        <div className="citation-list" aria-label="Sources">
          {citations.map((item, idx) => (
            <a
              key={`${canonicalUrl(item.source_url)}-${idx}`}
              href={item.source_url}
              target="_blank"
              rel="noreferrer"
              className="provenance-bar citation-card"
              style={{ textDecoration: 'none' }}
            >
              <ExternalLink size={12} aria-hidden="true" />
              <span>
                <strong>Source:</strong> {item.authority || 'Official College Website'}
                {item.section && <><br /><span className="citation-section">{item.section}</span></>}
              </span>
            </a>
          ))}
        </div>
      )}

      {/* Trust attribution: source details are shown by the citation card above. */}
      {provenance && !/unverified|fallback|gemini/i.test(provenance.authority || '') && (
        <div className="provenance-bar" aria-label="Answer verification">
          <ShieldCheck size={13} color="var(--ait-emerald)" />
          <span><strong>Verified College Fact</strong></span>
          {(() => {
            // §30: show verification date ONLY when a real timestamp exists.
            const va = provenance?.verified_at || provenance?.message?.provenance?.verified_at;
            if (!va || typeof va !== 'string' || /unverified|fallback/i.test(va)) return null;
            const d = new Date(va);
            if (isNaN(d.getTime())) return null;
            return (
              <span style={{ opacity: 0.75 }}>
                · Verified: {d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}
              </span>
            );
          })()}
        </div>
      )}

      {/* Follow-up suggestion chips */}
      {suggestions && suggestions.items && suggestions.items.length > 0 && (
        <div className="followup-chips">
          {suggestions.items.map((sug, idx) => (
            <button
              key={idx}
              className="followup-chip"
              onClick={() => onSelectSuggestion(sug)}
            >
              <Sparkles size={11} style={{ display: 'inline', marginRight: '4px' }} />
              {sug}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

const GENERIC_SOURCE_TERMS = new Set(['ahmedabad', 'institute', 'technology', 'official', 'website', 'ait', 'group', 'the', 'and', 'of', 'at']);

function canonicalUrl(value) {
  if (!value) return '';
  try {
    const url = new URL(value, window.location.origin);
    url.hash = '';
    url.pathname = url.pathname.replace(/\/+$/, '') || '/';
    return url.toString().toLowerCase();
  } catch {
    return String(value).split('#')[0].replace(/\/+$/, '').toLowerCase();
  }
}

function sourceTokens(value) {
  return String(value || '').toLowerCase().match(/[a-z0-9]+/g) || [];
}

function citationRelevance(item, queryText) {
  const queryTokens = new Set(sourceTokens(queryText).filter(token => !GENERIC_SOURCE_TERMS.has(token) && token.length > 2));
  const sourceText = [item.title, item.section, item.source_url, item.authority].join(' ');
  const sourceTokenSet = new Set(sourceTokens(sourceText));
  const matches = [...queryTokens].filter(token => sourceTokenSet.has(token)).length;
  const official = /aitindia\.in/i.test(item.source_url || '') || /official/i.test(item.authority || '') ? 1 : 0;
  return matches + official;
}

function dedupeRelevantCitations(items, queryText) {
  const ranked = items
    .filter(item => item && item.source_url)
    .map((item, index) => ({ item, index, score: citationRelevance(item, queryText) }))
    .sort((a, b) => b.score - a.score || a.index - b.index);
  const seen = new Set();
  const relevant = ranked.filter(({ item, score }) => {
    const key = canonicalUrl(item.source_url) || `${item.authority || ''}|${item.section || item.title || ''}`.toLowerCase();
    if (seen.has(key)) return false;
    seen.add(key);
    // With a query, show only citations having a topical match plus provenance.
    // Without one, preserve the full multi-source fallback behavior.
    return !queryText.trim() || score > 1;
  }).map(({ item }) => item);
  return relevant.length > 0 || queryText.trim() ? relevant : ranked.map(({ item }) => item);
}

// ── College switch confirmation buttons (§22/§61) ─────────
// Real, keyboard-accessible buttons (native <button>). The target college id
// always comes from the backend-issued prompt block — the client never picks a
// tenant itself. Switch calls the existing /college-context/switch API (via
// onCollegeSwitch); Stay only dismisses the prompt locally and never touches
// conversation.college_id or the user's default college.
function CollegeSwitchPromptButtons({ prompt, onCollegeSwitch }) {
  const [switching, setSwitching] = React.useState(false);
  const [error, setError] = React.useState(null);
  const [dismissed, setDismissed] = React.useState(false);

  if (dismissed) return null;

  const currentName = prompt.current_college_name || 'your current college';

  const handleSwitch = async () => {
    if (switching || !prompt.target_college_id) return; // no double-click
    setSwitching(true);
    setError(null);
    try {
      const ok = await onCollegeSwitch(prompt.target_college_id);
      if (ok) {
        setDismissed(true); // prompt handled; backend owns the new college
      } else {
        setError('Unable to switch college. Please try again.');
        setSwitching(false);
      }
    } catch (e) {
      console.error('College switch failed:', e);
      setError('Unable to switch college. Please try again.');
      setSwitching(false);
    }
  };

  return (
    <div role="group" aria-label="College switch confirmation" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
      <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
        <button
          type="button"
          className="btn-primary"
          style={{ padding: '6px 14px', fontSize: '0.82rem' }}
          disabled={switching}
          aria-busy={switching}
          onClick={handleSwitch}
        >
          {switching ? 'Switching...' : 'Switch'}
        </button>
        <button
          type="button"
          className="composer-tool-btn"
          style={{ padding: '6px 14px', fontSize: '0.82rem' }}
          disabled={switching}
          onClick={() => setDismissed(true)}
        >
          Stay with {currentName}
        </button>
      </div>
      {error && (
        <div role="alert" style={{ fontSize: '0.78rem', color: '#ef4444' }}>
          {error}
        </div>
      )}
    </div>
  );
}

// ── Feedback reason popover (§3/§4/§31) ─────────
const NEGATIVE_REASONS = [
  { value: 'incorrect', label: 'Incorrect information' },
  { value: 'outdated', label: 'Outdated information' },
  { value: 'wrong_college', label: 'Wrong college' },
  { value: 'missing_details', label: 'Missing details' },
  { value: 'not_relevant', label: 'Not relevant' },
  { value: 'could_not_answer', label: 'Could not answer my question' },
  { value: 'other', label: 'Other' },
];
const REPORT_REASONS = [
  { value: 'incorrect', label: 'Incorrect' },
  { value: 'outdated', label: 'Outdated' },
  { value: 'wrong_college', label: 'Wrong College' },
  { value: 'missing_source', label: 'Missing Source' },
  { value: 'contradicts_official', label: 'Contradicts Official Website' },
  { value: 'other', label: 'Other' },
];

function FeedbackReasonPopover({ mode, onSubmit, onClose }) {
  const options = mode === 'report' ? REPORT_REASONS : NEGATIVE_REASONS;
  const [reason, setReason] = React.useState(null);
  const [details, setDetails] = React.useState('');

  return (
    <div style={{ position: 'absolute', top: '100%', left: 0, zIndex: 50, marginTop: 6 }}>
      <div className="glass-card" style={{ width: 300, padding: 16, boxShadow: '0 8px 30px rgba(0,0,0,0.5)' }}>
        <div style={{ fontWeight: 700, fontSize: '0.85rem', marginBottom: 10 }}>
          {mode === 'report' ? 'Report information' : 'What was wrong?'}
        </div>
        {options.map(opt => (
          <label key={opt.value} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.8rem', padding: '3px 0', cursor: 'pointer' }}>
            <input type="radio" name="fb-reason" checked={reason === opt.value} onChange={() => setReason(opt.value)} />
            {opt.label}
          </label>
        ))}
        <textarea
          className="input-field"
          placeholder="Additional details (optional)"
          value={details}
          onChange={e => setDetails(e.target.value)}
          rows={2}
          style={{ width: '100%', fontSize: '0.8rem', marginTop: 8, resize: 'vertical' }}
        />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 8, marginTop: 10 }}>
          <button className="btn-secondary" style={{ fontSize: '0.78rem', padding: '5px 12px' }} onClick={onClose}>Cancel</button>
          <button
            className="btn-primary"
            style={{ fontSize: '0.78rem', padding: '5px 12px' }}
            disabled={!reason}
            onClick={() => onSubmit(reason, details)}
          >
            Submit Feedback
          </button>
        </div>
      </div>
    </div>
  );
}
