import React from 'react';
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
  onImageClick 
}) {
  const [copiedId, setCopiedId] = React.useState(null);

  const handleCopy = (id, text) => {
    navigator.clipboard.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  return (
    <div className="messages-scroll-area">
      {messages.map((msg, index) => {
        const isUser = msg.sender === 'user';
        return (
          <div key={msg.id || index} className={`message-row ${isUser ? 'user' : 'assistant'}`}>
            {!isUser && (
              <div className="message-avatar assistant">
                <img src="/ait-logo.webp" alt="AIT" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
              </div>
            )}

            <div className="message-content-box">
              <div className="message-bubble">
                {/* Text Content */}
                <div style={{ whiteSpace: 'pre-wrap' }}>
                  {msg.content}
                </div>

                {/* Structured Blocks (Images, Citations, Provenance, Suggestions) */}
                {msg.blocks && msg.blocks.length > 0 && (
                  <MessageBlocks 
                    blocks={msg.blocks} 
                    onImageClick={onImageClick}
                    onSelectSuggestion={onSelectSuggestion}
                  />
                )}
              </div>

              {/* Message Actions for Assistant */}
              {!isUser && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '2px 4px' }}>
                  <button 
                    className="item-action-icon" 
                    onClick={() => handleCopy(msg.id, msg.content)}
                    title="Copy message"
                  >
                    {copiedId === msg.id ? <Check size={14} color="var(--ait-emerald)" /> : <Copy size={14} />}
                  </button>
                  <button className="item-action-icon" title="Helpful">
                    <ThumbsUp size={14} />
                  </button>
                  <button className="item-action-icon" title="Not helpful">
                    <ThumbsDown size={14} />
                  </button>
                  {msg.grounding_status === 'verified' && (
                    <span style={{ fontSize: '0.72rem', color: 'var(--ait-emerald)', display: 'flex', alignItems: 'center', gap: '4px', marginLeft: 'auto' }}>
                      <ShieldCheck size={13} /> Verified AIT Institutional Fact
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
            <img src="/ait-logo.webp" alt="AIT" style={{ width: '100%', height: '100%', objectFit: 'contain' }} />
          </div>
          <div className="message-content-box">
            <div className="message-bubble">
              <div style={{ whiteSpace: 'pre-wrap' }}>
                {streamingDelta || 'Thinking...'}
              </div>
              {streamingBlocks && streamingBlocks.length > 0 && (
                <MessageBlocks 
                  blocks={streamingBlocks} 
                  onImageClick={onImageClick}
                  onSelectSuggestion={onSelectSuggestion}
                />
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

function MessageBlocks({ blocks, onImageClick, onSelectSuggestion }) {
  // Extract images
  const images = blocks.filter(b => b.type === 'image');
  const citations = blocks.filter(b => b.type === 'citation');
  const provenance = blocks.find(b => b.type === 'provenance');
  const suggestions = blocks.find(b => b.type === 'suggested_action');

  return (
    <div style={{ marginTop: '10px', display: 'flex', flexDirection: 'column', gap: '10px' }}>
      {/* P0 Verified Image Gallery */}
      {images.length > 0 && (
        <div className="image-gallery-grid">
          {images.map((img, i) => (
            <div key={i} className="verified-image-card" onClick={() => onImageClick(img)}>
              <img src={img.url} alt={img.alt || img.title} loading="lazy" />
              <div className="verified-badge">
                <CheckCircle2 size={11} /> Verified AIT
              </div>
              <div className="image-overlay">
                <div className="image-title">{img.title}</div>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Citations */}
      {citations.map((c, i) => (
        <div key={i} style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {c.items && c.items.map((item, idx) => (
            <a 
              key={idx} 
              href={item.source_url} 
              target="_blank" 
              rel="noreferrer" 
              className="provenance-bar"
              style={{ textDecoration: 'none' }}
            >
              <ExternalLink size={12} />
              <span>{item.title}</span>
            </a>
          ))}
        </div>
      ))}

      {/* Provenance attribution */}
      {provenance && (
        <div className="provenance-bar">
          <ShieldCheck size={13} color="var(--ait-emerald)" />
          <span>Source: <strong>{provenance.authority}</strong> ({provenance.source_domain})</span>
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
