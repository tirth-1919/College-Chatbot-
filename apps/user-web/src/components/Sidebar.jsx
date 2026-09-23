import React, { useState } from 'react';
import { 
  Plus, MessageSquare, Search, Pin, Trash2, Archive, ArchiveRestore,
  Pencil, LogIn, LogOut, X, Check
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
  onRenameConversation,
  onArchiveConversation,
  showArchived,
  onShowArchivedChange,
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
        <div className="brand-badge">
          <img src="/ai-faq-college-chat-bot-icon.svg" alt="AI FAQ College Chat Bot logo" className="brand-logo" />
          <div>
            <div className="brand-title">AI FAQ College Chat Bot</div>
            <div className="brand-subtitle">Ask anything about your college</div>
          </div>
        </div>
        <button className="item-action-icon mobile-menu-btn" onClick={onClose}>
          <X size={18} />
        </button>
      </div>

      <button className="sidebar-action-btn" onClick={() => { onNewChat(); if (window.innerWidth < 768) onClose(); }}>
        <Plus size={18} />
        <span>New Chat</span>
      </button>

      <button
        className="sidebar-archive-toggle"
        onClick={() => onShowArchivedChange(!showArchived)}
        aria-pressed={showArchived}
      >
        {showArchived ? <ArchiveRestore size={15} /> : <Archive size={15} />}
        <span>{showArchived ? 'Active conversations' : 'Archived conversations'}</span>
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
            <div className="group-title">{showArchived ? 'Archived' : 'Today'}</div>
            {today.map(c => (
              <ConversationItem 
                key={c.id} 
                conv={c} 
                isActive={c.id === currentId}
                onSelect={() => { onSelectConversation(c.id); if (window.innerWidth < 768) onClose(); }}
                onDelete={() => onDeleteConversation(c.id)}
                onTogglePin={() => onTogglePin(c.id, !c.is_pinned)}
                onRename={(title) => onRenameConversation(c.id, title)}
                onArchive={() => onArchiveConversation(c.id, !c.is_archived)}
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
                onRename={(title) => onRenameConversation(c.id, title)}
                onArchive={() => onArchiveConversation(c.id, !c.is_archived)}
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
                onRename={(title) => onRenameConversation(c.id, title)}
                onArchive={() => onArchiveConversation(c.id, !c.is_archived)}
              />
            ))}
          </div>
        )}

        {filtered.length === 0 && (
          <div style={{ textAlign: 'center', padding: '30px 10px', color: 'var(--text-dim)', fontSize: '0.85rem' }}>
          {showArchived ? 'No archived conversations found' : 'No conversations found'}
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

function ConversationItem({ conv, isActive, onSelect, onDelete, onTogglePin, onRename, onArchive }) {
  const [editing, setEditing] = useState(false);
  const [title, setTitle] = useState(conv.title);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState('');

  const cancelRename = () => {
    setTitle(conv.title);
    setError('');
    setEditing(false);
  };

  const saveRename = async () => {
    const trimmed = title.trim();
    if (!trimmed) {
      setError('A title is required.');
      return;
    }
    if (trimmed === conv.title) {
      setEditing(false);
      return;
    }
    setSaving(true);
    setError('');
    try {
      await onRename(trimmed);
      setEditing(false);
    } catch (err) {
      setError(err.message || 'Could not rename this conversation.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className={`conversation-item ${isActive ? 'active' : ''} ${editing ? 'editing' : ''}`} onClick={!editing ? onSelect : undefined}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', overflow: 'hidden' }}>
        <MessageSquare size={15} style={{ flexShrink: 0, opacity: isActive ? 1 : 0.6 }} />
        {editing ? (
          <div className="conversation-rename-wrap">
            <input
              className="conversation-rename-input"
              aria-label="Conversation title"
              value={title}
              maxLength={255}
              disabled={saving}
              autoFocus
              onChange={(event) => setTitle(event.target.value)}
              onKeyDown={(event) => {
                if (event.key === 'Enter') { event.preventDefault(); saveRename(); }
                if (event.key === 'Escape') cancelRename();
              }}
            />
            {error && <span className="conversation-action-error" role="alert">{error}</span>}
          </div>
        ) : <span className="conversation-item-title">{conv.title}</span>}
      </div>
      <div className="conversation-item-actions" onClick={e => e.stopPropagation()}>
        {editing ? <>
          <button className="item-action-icon" onClick={saveRename} disabled={saving} title="Save rename" aria-label="Save rename"><Check size={13} /></button>
          <button className="item-action-icon" onClick={cancelRename} disabled={saving} title="Cancel rename" aria-label="Cancel rename"><X size={13} /></button>
        </> : <>
        <button className="item-action-icon" onClick={() => setEditing(true)} title="Rename" aria-label="Rename"><Pencil size={13} /></button>
        <button 
          className="item-action-icon" 
          onClick={onTogglePin} 
          title={conv.is_pinned ? "Unpin" : "Pin"}
          style={{ color: conv.is_pinned ? 'var(--ait-accent)' : undefined }}
        >
          <Pin size={13} />
        </button>
        <button className="item-action-icon" onClick={onArchive} title={conv.is_archived ? 'Unarchive' : 'Archive'} aria-label={conv.is_archived ? 'Unarchive' : 'Archive'}>
          {conv.is_archived ? <ArchiveRestore size={13} /> : <Archive size={13} />}
        </button>
        <button className="item-action-icon" onClick={onDelete} title="Delete">
          <Trash2 size={13} />
        </button>
        </>}
      </div>
    </div>
  );
}
