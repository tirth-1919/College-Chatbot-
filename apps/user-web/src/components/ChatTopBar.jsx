import React, { useEffect, useState } from 'react';
import { Menu, ShieldCheck, Plus } from 'lucide-react';
import { apiClient } from '../services/api';

/**
 * Minimal college-context indicator (Part I §65): shows the currently active
 * college resolved by the backend. NOT a selector — deliberate change/switch
 * and forget actions re-use the existing college-context APIs (§23/§25/§26);
 * forgetting re-triggers the in-chat onboarding question.
 */
export function ChatTopBar({ onToggleSidebar, activeTitle, onNewChat, conversation }) {
  const [ctx, setCtx] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);

  const load = () => {
    if (!apiClient.getToken()) return;
    apiClient.authFetch(`/api/v1/college-context/me${conversation ? `?conversation_id=${conversation.id}` : ''}`, {
      headers: apiClient.getHeaders()
    }).then(r => r.ok ? r.json() : null).then(setCtx).catch(() => {});
  };

  useEffect(load, [conversation?.id]);

  // §27/§67: display the CONVERSATION's college (server-derived). The default
  // preference must never make a new chat LOOK like it is already connected
  // to a college — the in-chat onboarding question owns that decision.
  const college = ctx?.conversation_college;

  const switchCollege = async (collegeName) => {
    await apiClient.authFetch('/api/v1/college-context/switch', {
      method: 'POST',
      headers: apiClient.getHeaders(),
      body: JSON.stringify({ conversation_id: conversation?.id, college_name: collegeName })
    });
    setMenuOpen(false);
    load();
  };

  const changeDefault = async (collegeName) => {
    const name = collegeName || window.prompt('Enter the full college name (e.g. RC Technical):');
    if (!name) return;
    await apiClient.authFetch('/api/v1/college-context/default/change', {
      method: 'POST',
      headers: apiClient.getHeaders(),
      body: JSON.stringify({ college_name: name })
    });
    setMenuOpen(false);
    load();
  };

  const forgetDefault = async () => {
    await apiClient.authFetch('/api/v1/college-context/default/forget', {
      method: 'POST',
      headers: apiClient.getHeaders()
    });
    setMenuOpen(false);
    load();
  };

  return (
    <header className="chat-topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button className="mobile-menu-btn" onClick={onToggleSidebar} title="Open sidebar menu">
          <Menu size={22} />
        </button>
        <span style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-main)' }}>
          {activeTitle || 'AI FAQ College Chat Bot'}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', position: 'relative' }}>
        <div className="authority-indicator" style={{ cursor: 'pointer' }} onClick={() => setMenuOpen(o => !o)}>
          <span className="authority-dot"></span>
          <span>{college ? `🏫 ${college.name}` : (ctx?.needs_onboarding ? '🏫 Set your college' : 'AI FAQ College Chat Bot')}</span>
        </div>
        {menuOpen && (
          <div style={{
            position: 'absolute', top: '110%', right: 0, zIndex: 50,
            background: 'var(--bg-card, #1a2345)', color: 'var(--text-main, #fff)',
            border: '1px solid rgba(255,255,255,0.15)', borderRadius: 10,
            padding: '10px', display: 'flex', flexDirection: 'column', gap: 6, minWidth: 230
          }}>
            <div style={{ fontSize: '0.72rem', opacity: 0.7, padding: '2px 6px' }}>
              College Preference
            </div>
            <div style={{ fontSize: '0.8rem', padding: '2px 6px', fontWeight: 600 }}>
              {college ? college.name : 'Not set'}
            </div>
            <button className="composer-tool-btn" style={{ justifyContent: 'flex-start' }}
              onClick={() => { const n = window.prompt('Switch THIS conversation to which college? (full name)'); if (n) switchCollege(n); }}>
              🔄 Switch this conversation
            </button>
            <button className="composer-tool-btn" style={{ justifyContent: 'flex-start' }}
              onClick={() => changeDefault()}>
              ⭐ Change default college
            </button>
            <button className="composer-tool-btn" style={{ justifyContent: 'flex-start' }}
              onClick={forgetDefault}>
              🗑 Forget college
            </button>
          </div>
        )}
        <button 
          className="composer-tool-btn" 
          onClick={onNewChat} 
          title="New conversation"
          style={{ background: 'rgba(255,255,255,0.05)' }}
        >
          <Plus size={18} />
        </button>
      </div>
    </header>
  );
}
