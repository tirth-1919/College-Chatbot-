import React from 'react';
import { X, ExternalLink, ShieldCheck } from 'lucide-react';

export function ImageViewerModal({ image, onClose }) {
  if (!image) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content image-modal-content" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '12px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ color: 'var(--ait-emerald)', display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.8rem', fontWeight: 600 }}>
              <ShieldCheck size={16} /> Verified Official AIT Photo
            </span>
            <span style={{ color: 'var(--text-dim)', fontSize: '0.8rem' }}>• {image.category}</span>
          </div>
          <button className="item-action-icon" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        <img src={image.url} alt={image.title} />

        <div style={{ marginTop: '12px', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h3 style={{ fontSize: '1rem', color: 'white', fontWeight: 600 }}>{image.title}</h3>
            <p style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>{image.description || 'Official campus asset'}</p>
          </div>
          {image.source_url && (
            <a 
              href={image.source_url} 
              target="_blank" 
              rel="noreferrer" 
              className="provenance-bar"
              style={{ textDecoration: 'none' }}
            >
              <ExternalLink size={14} />
              <span>Source URL</span>
            </a>
          )}
        </div>
      </div>
    </div>
  );
}
