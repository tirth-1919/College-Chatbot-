import React, { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatTopBar } from './components/ChatTopBar';
import { WelcomeHero } from './components/WelcomeHero';
import { MessageList } from './components/MessageList';
import { Composer } from './components/Composer';
import { AuthModal } from './components/AuthModal';
import { ImageViewerModal } from './components/ImageViewerModal';
import CollegeRegisterPage from './pages/CollegeRegisterPage';
import { apiClient } from './services/api';
import './styles/theme.css';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [showArchived, setShowArchived] = useState(false);
  const [currentId, setCurrentId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [user, setUser] = useState(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [currentPath, setCurrentPath] = useState(window.location.pathname);
  // In-chat college onboarding state (server-derived; no selection page/modal).
  const [collegeCtx, setCollegeCtx] = useState(null);

  // Streaming State
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingDelta, setStreamingDelta] = useState('');
  const [streamingBlocks, setStreamingBlocks] = useState([]);
  const abortControllerRef = useRef(null);

  const navigate = (path) => {
    window.history.pushState({}, '', path);
    setCurrentPath(path);
  };

  // Load initial data
  useEffect(() => {
    const handleAuthExpired = () => setUser(null);
    const handlePopState = () => setCurrentPath(window.location.pathname);
    window.addEventListener('ait-auth-expired', handleAuthExpired);
    window.addEventListener('popstate', handlePopState);
    apiClient.getProfile().then(setUser).catch(() => {});
    loadConversations(false);
    return () => {
      window.removeEventListener('ait-auth-expired', handleAuthExpired);
      window.removeEventListener('popstate', handlePopState);
    };
  }, []);

  const loadConversations = async (archived = showArchived) => {
    try {
      const list = await apiClient.listConversations('', archived);
      setConversations(list);
    } catch (e) {
      console.error(e);
    }
  };

  // §19: fetch the server-derived college context for the active conversation.
  // Backend is authoritative (§11/§27); this only drives the in-chat prompt.
  const loadCollegeCtx = (convId) => {
    if (!apiClient.getToken()) return;
    const qs = convId ? `?conversation_id=${convId}` : '';
    apiClient.authFetch(`/api/v1/college-context/me${qs}`, {
      headers: apiClient.getHeaders()
    }).then(r => r.ok ? r.json() : null).then(setCollegeCtx).catch(() => {});
  };

  useEffect(() => { loadCollegeCtx(currentId); }, [currentId, messages.length]);

  const handleSelectConversation = async (id) => {
    if (isStreaming) handleStopStreaming();
    setCurrentId(id);
    try {
      const data = await apiClient.getConversation(id);
      if (data && data.messages) {
        setMessages(data.messages);
      } else {
        setMessages([]);
      }
    } catch (err) {
      console.error(err);
      setMessages([]);
    }
  };

  const handleNewChat = () => {
    if (isStreaming) handleStopStreaming();
    setCurrentId(null);
    setMessages([]);
  };

  const handleConversationViewChange = async (archived) => {
    if (isStreaming) handleStopStreaming();
    setShowArchived(archived);
    setCurrentId(null);
    setMessages([]);
    await loadConversations(archived);
  };

  const handleDeleteConversation = async (id) => {
    try {
      await apiClient.deleteConversation(id);
      if (currentId === id) {
        handleNewChat();
      }
      loadConversations();
    } catch (e) {
      console.error(e);
    }
  };

  const handleTogglePin = async (id, is_pinned) => {
    try {
      await apiClient.updateConversation(id, { is_pinned });
      loadConversations();
    } catch (e) {
      console.error(e);
    }
  };

  const handleRenameConversation = async (id, title) => {
    const response = await apiClient.updateConversation(id, { title });
    await loadConversations();
    return response;
  };

  const handleArchiveConversation = async (id, is_archived) => {
    await apiClient.updateConversation(id, { is_archived });
    if (currentId === id) handleNewChat();
    await loadConversations();
  };

  // §22/§61: [Switch] button on a college_switch_prompt block. The backend
  // /college-context/switch endpoint is the authoritative persistence point
  // (conversation.college_id in the DB); the conversation is then RELOADED
  // from the database so every subsequent question uses the new tenant.
  const handleCollegeSwitch = async (targetCollegeId) => {
    if (!currentId || !targetCollegeId) return false;
    try {
      const res = await apiClient.authFetch('/api/v1/college-context/switch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', ...(apiClient.getHeaders()) },
        body: JSON.stringify({ conversation_id: currentId, college_id: targetCollegeId })
      });
      if (!res.ok) return false;
      // Backend is authoritative (§22/§61/§67): reload the conversation and
      // college context from the DATABASE after the persisted switch.
      await loadCollegeCtx(currentId);
      const data = await apiClient.getConversation(currentId);
      setMessages(data?.messages || []);
      loadConversations();
      return true;
    } catch (e) {
      console.error('College switch failed:', e);
      return false; // conversation college unchanged; prompt stays visible
    }
  };

  const handleStopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
    setIsStreaming(false);
    if (streamingDelta) {
      setMessages(prev => [...prev, {
        id: 'aborted-' + Date.now(),
        sender: 'assistant',
        content: streamingDelta,
        blocks: streamingBlocks,
        grounding_status: 'stopped'
      }]);
      setStreamingDelta('');
      setStreamingBlocks([]);
    }
  };

  const handleSendMessage = async (text, attachments = []) => {
    const convId = currentId || `conv-${Date.now()}`;
    if (!currentId) {
      setCurrentId(convId);
    }

    // Append user message immediately
    const userMsg = {
      id: 'usr-' + Date.now(),
      sender: 'user',
      content: text,
      blocks: [{ type: 'text', content: text }]
    };
    setMessages(prev => [...prev, userMsg]);

    // Setup streaming
    setIsStreaming(true);
    setStreamingDelta('');
    setStreamingBlocks([]);

    const controller = new AbortController();
    abortControllerRef.current = controller;

    let accumulatedText = '';
    let accumulatedBlocks = [];

    try {
      await apiClient.streamChat(
        convId,
        text,
        attachments,
        (event, data) => {
          if (event === 'text_delta') {
            accumulatedText += data.delta;
            setStreamingDelta(accumulatedText);
          } else if (['image', 'table', 'citation', 'provenance_metadata', 'college_switch_prompt', 'suggested_action'].includes(event)) {
            // Interactive blocks (§22/§61) must survive the stream, otherwise
            // the [Switch] button never becomes clickable in a live session.
            accumulatedBlocks = [...accumulatedBlocks, data];
            setStreamingBlocks(accumulatedBlocks);
          } else if (event === 'message_complete') {
            setMessages(prev => [...prev, {
              id: data.message_id || 'asst-' + Date.now(),
              sender: 'assistant',
              content: accumulatedText,
              blocks: accumulatedBlocks,
              grounding_status: data.grounding_status || 'verified'
            }]);
            setIsStreaming(false);
            setStreamingDelta('');
            setStreamingBlocks([]);
            loadConversations();
          }
        },
        controller.signal
      );
    } catch (err) {
      if (err.name !== 'AbortError') {
        setMessages(prev => [...prev, {
          id: 'err-' + Date.now(),
          sender: 'assistant',
          content: `An error occurred: ${err.message}`,
          blocks: []
        }]);
      }
      setIsStreaming(false);
      setStreamingDelta('');
      setStreamingBlocks([]);
    }
  };

  const activeConv = conversations.find(c => c.id === currentId);

  if (currentPath === '/register-college') {
    return (
      <CollegeRegisterPage
        onBackToLogin={() => {
          navigate('/');
          setAuthModalOpen(true);
        }}
      />
    );
  }

  return (
    <div className="app-container">
      {/* Sidebar Navigation */}
      <Sidebar
        isOpen={sidebarOpen}
        onClose={() => setSidebarOpen(false)}
        conversations={conversations}
        currentId={currentId}
        onSelectConversation={handleSelectConversation}
        onNewChat={handleNewChat}
        onDeleteConversation={handleDeleteConversation}
        onTogglePin={handleTogglePin}
        onRenameConversation={handleRenameConversation}
        onArchiveConversation={handleArchiveConversation}
        showArchived={showArchived}
        onShowArchivedChange={handleConversationViewChange}
        user={user}
        onOpenAuth={() => setAuthModalOpen(true)}
        onLogout={async () => {
          await apiClient.logout();
          setUser(null);
          loadConversations(showArchived);
        }}
      />

      {/* Main Chat Workstation */}
      <main className="chat-main">
        <ChatTopBar
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          activeTitle={activeConv ? activeConv.title : "AI FAQ College Chat Bot"}
          onNewChat={handleNewChat}
          conversation={activeConv || (currentId ? { id: currentId, college_id: activeConv?.college_id ?? null } : null)}
        />

        {messages.length === 0 && !isStreaming ? (
          collegeCtx?.needs_onboarding && collegeCtx?.onboarding_message ? (
            <div className="welcome-hero">
              <h1 className="welcome-title">Which college information do you want?</h1>
              <p className="welcome-subtitle">
                Please enter your college name in the chat below (for example:
                RC Technical, or AIT).
              </p>
            </div>
          ) : (
            <WelcomeHero onSelectPrompt={() => handleNewChat()} />
          )
        ) : (
          <MessageList 
            messages={messages}
            streamingDelta={streamingDelta}
            streamingBlocks={streamingBlocks}
            isStreaming={isStreaming}
            onSelectSuggestion={(prompt) => handleSendMessage(prompt, [])}
            onCollegeSwitch={handleCollegeSwitch}
            onImageClick={(img) => setSelectedImage(img)}
          />
        )}

        <Composer 
          onSendMessage={handleSendMessage}
          isStreaming={isStreaming}
          onStopStreaming={handleStopStreaming}
        />
      </main>

      {/* Modals */}
      <AuthModal 
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onAuthSuccess={(u) => {
          setUser(u);
          loadConversations();
        }}
        onNavigateRegister={() => {
          setAuthModalOpen(false);
          navigate('/register-college');
        }}
      />

      <ImageViewerModal 
        image={selectedImage}
        onClose={() => setSelectedImage(null)}
      />
    </div>
  );
}
