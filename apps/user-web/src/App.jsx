import React, { useState, useEffect, useRef } from 'react';
import { Sidebar } from './components/Sidebar';
import { ChatTopBar } from './components/ChatTopBar';
import { WelcomeHero } from './components/WelcomeHero';
import { MessageList } from './components/MessageList';
import { Composer } from './components/Composer';
import { AuthModal } from './components/AuthModal';
import { ImageViewerModal } from './components/ImageViewerModal';
import { apiClient } from './services/api';
import './styles/theme.css';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [conversations, setConversations] = useState([]);
  const [currentId, setCurrentId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [user, setUser] = useState(null);
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);

  // Streaming State
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingDelta, setStreamingDelta] = useState('');
  const [streamingBlocks, setStreamingBlocks] = useState([]);
  const abortControllerRef = useRef(null);

  // Load initial data
  useEffect(() => {
    apiClient.getProfile().then(setUser).catch(() => {});
    loadConversations();
  }, []);

  const loadConversations = async () => {
    try {
      const list = await apiClient.listConversations();
      setConversations(list);
    } catch (e) {
      console.error(e);
    }
  };

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
          } else if (['image', 'table', 'citation', 'provenance_metadata'].includes(event)) {
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
        user={user}
        onOpenAuth={() => setAuthModalOpen(true)}
        onLogout={() => {
          apiClient.setToken(null);
          setUser(null);
          loadConversations();
        }}
      />

      {/* Main Chat Workstation */}
      <main className="chat-main">
        <ChatTopBar 
          onToggleSidebar={() => setSidebarOpen(!sidebarOpen)}
          activeTitle={activeConv ? activeConv.title : "Ahmedabad Institute of Technology"}
          onNewChat={handleNewChat}
        />

        {messages.length === 0 && !isStreaming ? (
          <WelcomeHero onSelectPrompt={(prompt) => handleSendMessage(prompt, [])} />
        ) : (
          <MessageList 
            messages={messages}
            streamingDelta={streamingDelta}
            streamingBlocks={streamingBlocks}
            isStreaming={isStreaming}
            onSelectSuggestion={(prompt) => handleSendMessage(prompt, [])}
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
      />

      <ImageViewerModal 
        image={selectedImage}
        onClose={() => setSelectedImage(null)}
      />
    </div>
  );
}
