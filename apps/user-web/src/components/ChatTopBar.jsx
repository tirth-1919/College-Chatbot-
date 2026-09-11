import React from 'react';
import { Menu, ShieldCheck, Plus } from 'lucide-react';

export function ChatTopBar({ onToggleSidebar, activeTitle, onNewChat }) {
  return (
    <header className="chat-topbar">
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <button className="mobile-menu-btn" onClick={onToggleSidebar} title="Open sidebar menu">
          <Menu size={22} />
        </button>
        <span style={{ fontWeight: 600, fontSize: '0.95rem', color: 'var(--text-main)' }}>
          {activeTitle || 'AIT AI Assistant'}
        </span>
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: '14px' }}>
        <div className="authority-indicator">
          <span className="authority-dot"></span>
          <span>Official AIT Authority</span>
        </div>
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
