import React, { useState } from 'react';
import { 
  Plus, MessageSquare, Search, Pin, Trash2, Archive, 
  Settings, LogIn, LogOut, User as UserIcon, X, Check
} from 'lucide-react';

export function Sidebar({ 
  isOpen, 
  onClose, 
  conversations, 
  currentId, 
  onSelectConversation, 
  onNewChat,
  onDeleteConversation,
  onTogglePin,
  user,
  onOpenAuth,
  onLogout
}) {
  const [search, setSearch] = useState('');

  const filtered = conversations.filter(c => 
    c.title.toLowerCase().includes(search.toLowerCase())
  );

  // Group conversations: Today, Previous 7 Days, Older
  const now = new Date();
  const today = [];
  const pastWeek = [];
  const older = [];

  filtered.forEach(c => {
    const d = new Date(c.created_at || Date.now());
    const diffDays = (now - d) / (1000 * 60 * 60 * 24);
    if (diffDays < 1) today.push(c);
    else if (diffDays < 7) pastWeek.push(c);
    else older.push(c);
  });

  return (
    <aside className={`sidebar ${isOpen ? 'open' : ''}`}>
      <div className="sidebar-header">
        <a href="https://www.aitindia.in" target="_blank" rel="noreferrer" className="brand-badge">
          <img src="/ait-logo.webp" alt="AIT Logo" className="brand-logo" />
          <div>
            <div className="brand-title">AIT ASSISTANT</div>
            <div className="brand-subtitle">Official AI Portal</div>
          </div>
        </a>
        <button className="item-action-icon mobile-menu-btn" onClick={onClose}>
          <X size={18} />
        </button>
      </div>

      <button className="sidebar-action-btn" onClick={() => { onNewChat(); if (window.innerWidth < 768) onClose(); }}>
        <Plus size={18} />
        <span>New Chat</span>
      </button>

      <div className="conversation-search-box">
        <Search size={15} className="conversation-search-icon" />
        <input 
          type="text" 
          className="conversation-search-input"
          placeholder="Search chats..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>

      <div className="conversation-groups">
        {today.length > 0 && (
          <div>
            <div className="group-title">Today</div>
            {today.map(c => (
              <ConversationItem 
                key={c.id} 
                conv={c} 
                isActive={c.id === currentId}
                onSelect={() => { onSelectConversation(c.id); if (window.innerWidth < 768) onClose(); }}
                onDelete={() => onDeleteConversation(c.id)}
                onTogglePin={() => onTogglePin(c.id, !c.is_pinned)}
              />
            ))}
          </div>
        )}

        {pastWeek.length > 0 && (
          <div>
            <div className="group-title">Previous 7 Days</div>
            {pastWeek.map(c => (
              <ConversationItem 
                key={c.id} 
                conv={c} 
                isActive={c.id === currentId}
                onSelect={() => { onSelectConversation(c.id); if (window.innerWidth < 768) onClose(); }}
                onDelete={() => onDeleteConversation(c.id)}
                onTogglePin={() => onTogglePin(c.id, !c.is_pinned)}
              />
            ))}
          </div>
        )}

        {older.length > 0 && (
          <div>
            <div className="group-title">Older</div>
            {older.map(c => (
              <ConversationItem 
                key={c.id} 
                conv={c} 
                isActive={c.id === currentId}
                onSelect={() => { onSelectConversation(c.id); if (window.innerWidth < 768) onClose(); }}
                onDelete={() => onDeleteConversation(c.id)}
                onTogglePin={() => onTogglePin(c.id, !c.is_pinned)}
              />
            ))}
          </div>
        )}

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
            No conversations found
          </div>
        )}
      </div>

      <div className="sidebar-footer">
        {user ? (
          <div className="user-profile-badge">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <div style={{ width: 28, height: 28, borderRadius: '50%', background: 'var(--ait-accent)', color: 'white', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '0.8rem', fontWeight: 600 }}>
                {user.full_name ? user.full_name[0].toUpperCase() : 'U'}
              </div>
              <div style={{ fontSize: '0.85rem', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '120px' }}>
                {user.full_name}
              </div>
            </div>
            <button className="item-action-icon" onClick={onLogout} title="Logout">
              <LogOut size={16} />
            </button>
          </div>
        ) : (
          <button 
            className="user-profile-badge" 
            style={{ width: '100%', border: 'none', color: 'var(--text-main)', justifyContent: 'center', gap: '8px' }}
            onClick={onOpenAuth}
          >
            <LogIn size={16} color="var(--ait-accent)" />
            <span style={{ fontSize: '0.85rem', fontWeight: 500 }}>Sign In / Sign Up</span>
          </button>
        )}
      </div>
    </aside>
  );
}

function ConversationItem({ conv, isActive, onSelect, onDelete, onTogglePin }) {
  return (
    <div className={`conversation-item ${isActive ? 'active' : ''}`} onClick={onSelect}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
        <MessageSquare size={15} style={{ flexShrink: 0, opacity: isActive ? 1 : 0.6 }} />
        <span className="conversation-item-title">{conv.title}</span>
      </div>
      <div className="conversation-item-actions" onClick={e => e.stopPropagation()}>
        <button 
          className="item-action-icon" 
          onClick={onTogglePin} 
          title={conv.is_pinned ? "Unpin" : "Pin"}
          style={{ color: conv.is_pinned ? 'var(--ait-accent)' : undefined }}
        >
          <Pin size={13} />
        </button>
        <button className="item-action-icon" onClick={onDelete} title="Delete">
          <Trash2 size={13} />
        </button>
      </div>
    </div>
  );
}
