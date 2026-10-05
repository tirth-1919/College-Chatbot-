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

// Conversation history is the authoritative post-stream state. Keep the
// tenant-separated branch blocks when an older server also returns the
// aggregate answer in `content` (or exposes the branches as `college_answers`).
export function normalizeMessage(message) {
  if (!message || typeof message !== 'object') return message;

  const branchAnswers = Array.isArray(message.college_answers)
    ? message.college_answers
    : Array.isArray(message.collegeAnswers)
      ? message.collegeAnswers
      : [];

  const existingBlocks = Array.isArray(message.blocks)
    ? message.blocks
    : [];

  const collegeBlocks = existingBlocks.filter(
    block => block?.type === 'college_answer'
  );

  // A college_answer block is the complete rendering contract for a branch.
  // Remove aggregate text/provenance blocks at normalization time as well as in
  // the view so a history refresh cannot reintroduce the stale answer through
  // a second rendering path.
  const normalizedBlocks = collegeBlocks.length > 0
    ? collegeBlocks
    : [
        ...existingBlocks,
        ...branchAnswers.map(answer => ({
          type: 'college_answer',
          ...answer
        }))
      ];

  return normalizedBlocks.length === existingBlocks.length &&
    branchAnswers.length === 0 &&
    normalizedBlocks.every(
      (block, index) => block === existingBlocks[index]
    )
    ? message
    : { ...message, blocks: normalizedBlocks };
}

function normalizeMessages(messages) {
  return Array.isArray(messages)
    ? messages.map(normalizeMessage)
    : [];
}

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
  const [conversationState, setConversationState] = useState('empty');
  const [conversationError, setConversationError] = useState('');

  // In-chat college onboarding state (server-derived; no selection page/modal).
  const [collegeCtx, setCollegeCtx] = useState(null);

  // Streaming State
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingDelta, setStreamingDelta] = useState('');
  const [streamingBlocks, setStreamingBlocks] = useState([]);
  const abortControllerRef = useRef(null);
  const streamingMessageIdRef = useRef(null);

  const navigate = (path) => {
    window.history.pushState({}, '', path);
    setCurrentPath(path);
  };

  // Load initial data
  useEffect(() => {
    const handleAuthExpired = () => {
      setUser(null);
      setCurrentId(null);
      setMessages([]);
      setConversationState('empty');
    };

    const handlePopState = () => {
      setCurrentPath(window.location.pathname);
    };

    window.addEventListener('ait-auth-expired', handleAuthExpired);
    window.addEventListener('popstate', handlePopState);

    // Do not probe protected endpoints without a session. More importantly,
    // restore the user before treating conversation failures as auth failures.
    const token = apiClient.getToken();

    if (token) {
      apiClient.getProfile()
        .then(profile => {
          setUser(profile);

          if (profile) {
            return loadConversations(false);
          }

          return null;
        })
        .catch(() => {});
    }

    return () => {
      window.removeEventListener(
        'ait-auth-expired',
        handleAuthExpired
      );
      window.removeEventListener(
        'popstate',
        handlePopState
      );
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

    const qs = convId
      ? `?conversation_id=${convId}`
      : '';

    apiClient.authFetch(
      `/api/v1/college-context/me${qs}`,
      {
        headers: apiClient.getHeaders()
      }
    )
      .then(r => r.ok ? r.json() : null)
      .then(setCollegeCtx)
      .catch(() => {});
  };

  useEffect(() => {
    loadCollegeCtx(currentId);
  }, [currentId, messages.length]);

  const handleSelectConversation = async (id) => {
    if (isStreaming) {
      handleStopStreaming();
    }

    setCurrentId(id);
    setMessages([]);
    setConversationError('');
    setConversationState('loading');

    try {
      const data = await apiClient.getConversation(id);

      if (!data || data.id !== id) {
        throw new Error(
          'The conversation could not be found.'
        );
      }

      // The API is authoritative for both messages and tenant context.
      // The sidebar object is never used as a fallback for the active
      // conversation.
      const loadedMessages = normalizeMessages(
        data.messages
      );

      setMessages(loadedMessages);

      setConversationState(
        loadedMessages.length
          ? 'loaded'
          : 'empty'
      );

      loadCollegeCtx(id);
    } catch (err) {
      console.error(
        'Conversation load failed:',
        err
      );

      setConversationError(
        err.message ||
        'Conversation could not be loaded.'
      );

      setConversationState('error');
    }
  };

  const handleNewChat = () => {
    if (isStreaming) {
      handleStopStreaming();
    }

    setCurrentId(null);
    setMessages([]);
    setConversationError('');
    setConversationState('empty');
    setCollegeCtx(null);

    // A new chat has no visible state change when the welcome screen is already
    // open, so move focus to the composer to provide immediate feedback and let
    // the user start typing right away.
    window.setTimeout(() => {
      document
        .querySelector('.composer-textarea')
        ?.focus();
    }, 0);
  };

  const handleConversationViewChange = async (archived) => {
    if (isStreaming) {
      handleStopStreaming();
    }

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
      await apiClient.updateConversation(
        id,
        { is_pinned }
      );

      loadConversations();
    } catch (e) {
      console.error(e);
    }
  };

  const handleRenameConversation = async (id, title) => {
    const response = await apiClient.updateConversation(
      id,
      { title }
    );

    await loadConversations();

    return response;
  };

  const handleArchiveConversation = async (
    id,
    is_archived
  ) => {
    await apiClient.updateConversation(
      id,
      { is_archived }
    );

    if (currentId === id) {
      handleNewChat();
    }

    await loadConversations();
  };

  // §22/§61: [Switch] button on a college_switch_prompt block.
  // The backend /college-context/switch endpoint is the authoritative
  // persistence point (conversation.college_id in the DB); the conversation
  // is then RELOADED from the database so every subsequent question uses
  // the new tenant.
  const handleCollegeSwitch = async (
    targetCollegeId
  ) => {
    if (!currentId || !targetCollegeId) {
      return false;
    }

    try {
      const res = await apiClient.authFetch(
        '/api/v1/college-context/switch',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...apiClient.getHeaders()
          },
          body: JSON.stringify({
            conversation_id: currentId,
            college_id: targetCollegeId
          })
        }
      );

      if (!res.ok) {
        return false;
      }

      const payload = await res.json();

      // Backend is authoritative (§22/§61/§67): reload the conversation and
      // college context from the DATABASE after the persisted switch.
      // The post-switch onboarding message was persisted server-side, so the
      // switch prompt disappears (§8) and refresh keeps the new tenant (§9).
      await loadCollegeCtx(currentId);

      const data = await apiClient.getConversation(
        currentId
      );

      setMessages(
        normalizeMessages(data?.messages)
      );

      // §14: NEVER auto-answer on switch. The persisted assistant message
      // only confirms the connection and asks what the user wants to know.
      if (
        payload?.knowledge &&
        window.__CollegeSwitchDebug
      ) {
        window.__CollegeSwitchDebug(payload);
      }

      loadConversations();

      return true;
    } catch (e) {
      console.error(
        'College switch failed:',
        e
      );

      return false;
    }
  };

  const handleStopStreaming = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }

    setIsStreaming(false);

    if (streamingDelta || streamingBlocks.length > 0) {
      setMessages(prev => prev.map(message =>
        message.id === streamingMessageIdRef.current
          ? {
              ...message,
              content: streamingDelta,
              blocks: streamingBlocks,
              grounding_status: 'stopped'
            }
          : message
      ));

      streamingMessageIdRef.current = null;
      setStreamingDelta('');
      setStreamingBlocks([]);
    } else {
      streamingMessageIdRef.current = null;
    }
  };

  const handleSendMessage = async (
    text,
    attachments = []
  ) => {
    if (abortControllerRef.current) return;

    let convId = currentId;

    if (!convId) {
      // A normal conversation is created only after the backend has an explicit
      // selected tenant. The context endpoint is authoritative; no default or
      // first-college fallback is used here.
      const ctx = await apiClient.authFetch(
        '/api/v1/college-context/me',
        {
          headers: apiClient.getHeaders()
        }
      )
        .then(r => r.ok ? r.json() : null)
        .catch(() => null);

      let collegeId =
        ctx?.default_college?.id;

      if (!collegeId) {
        // Missing default college is the authenticated onboarding state,
        // not an authentication failure. Resolve the college name typed into
        // the existing in-chat onboarding prompt before creating a NORMAL chat.
        const resolved = await apiClient.authFetch(
          '/api/v1/college-context/resolve',
          {
            method: 'POST',
            headers: apiClient.getHeaders(),
            body: JSON.stringify({
              college_name: text
            })
          }
        )
          .then(async response => {
            const payload =
              await response.json()
                .catch(() => ({}));

            return response.ok
              ? payload
              : {
                  status: 'ERROR',
                  message: payload.detail
                };
          })
          .catch(() => ({
            status: 'ERROR'
          }));

        if (
          resolved.status !== 'RESOLVED' ||
          !resolved.college?.id
        ) {
          setConversationError(
            resolved.message ||
            'Please enter the full name of your college to continue.'
          );

          setConversationState('error');

          return;
        }

        collegeId =
          resolved.college.id;
      }

      let created;

      try {
        created = await apiClient.createConversation(
          'New Conversation',
          collegeId
        );
      } catch (err) {
        setConversationError(
          err.message ||
          'Could not create a new conversation.'
        );

        setConversationState('error');

        return;
      }

      if (
        !created?.id ||
        !created?.college_id
      ) {
        setConversationError(
          'The server did not return a tenant-scoped conversation.'
        );

        setConversationState('error');

        return;
      }

      convId = created.id;

      setCurrentId(convId);
      setConversationState('empty');

      await loadConversations();

      if (!ctx?.default_college?.id) {
        // Persist the server-owned onboarding message on the newly created
        // conversation. The backend validates ownership and the target tenant.
        const initialized =
          await apiClient.authFetch(
            '/api/v1/college-context/switch',
            {
              method: 'POST',
              headers: apiClient.getHeaders(),
              body: JSON.stringify({
                conversation_id: convId,
                college_id: collegeId
              })
            }
          );

        if (!initialized.ok) {
          setConversationError(
            'The college was resolved, but the conversation could not be initialized.'
          );

          setConversationState('error');

          return;
        }

        // FIX:
        // The previous code referenced `data`, but no `data` variable existed
        // in this scope. The switch response is stored in `initialized`.
        const initializedData =
          await initialized.json()
            .catch(() => ({}));

        const loadedMessages =
          normalizeMessages(
            initializedData?.messages
          );

        setMessages(loadedMessages);

        setConversationState(
          loadedMessages.length
            ? 'loaded'
            : 'empty'
        );

        loadCollegeCtx(convId);

        return;
      }
    }

    // Append user message immediately
    const userMsg = {
      id: 'usr-' + Date.now(),
      sender: 'user',
      content: text,
      blocks: [
        {
          type: 'text',
          content: text
        }
      ]
    };

    const assistantMessageId = 'asst-stream-' + Date.now();
    streamingMessageIdRef.current = assistantMessageId;

    setMessages(prev => [
      ...prev,
      userMsg,
      {
        id: assistantMessageId,
        sender: 'assistant',
        content: '',
        blocks: [],
        grounding_status: 'streaming'
      }
    ]);

    // Setup streaming
    setIsStreaming(true);
    setStreamingDelta('');
    setStreamingBlocks([]);

    const controller =
      new AbortController();

    abortControllerRef.current =
      controller;

    let accumulatedText = '';
    let accumulatedBlocks = [];
    let multiCollegeResponse = false;

    try {
      await apiClient.streamChat(
        convId,
        text,
        attachments,
        (event, data) => {
          if (event === 'text_delta') {
            // A multi-college response is rendered only from its dedicated
            // college_answer blocks, even if an older backend/proxy also sends
            // aggregate text_delta events.
            if (!multiCollegeResponse) {
              accumulatedText += data.delta;
              setStreamingDelta(
                accumulatedText
              );
              setMessages(prev => prev.map(message =>
                message.id === streamingMessageIdRef.current
                  ? { ...message, content: accumulatedText }
                  : message
              ));
            }
          } else if (
            [
              'image',
              'table',
              'citation',
              'provenance_metadata',
              'college_answer',
              'college_switch_prompt',
              'suggested_action'
            ].includes(event)
          ) {
            // The first college_answer establishes the exclusive multi-college
            // rendering path. Drop any aggregate text already received and
            // preserve every branch block and its metadata.
            if (event === 'college_answer') {
              multiCollegeResponse = true;
              accumulatedText = '';
              setStreamingDelta('');
            }

            accumulatedBlocks = [
              ...accumulatedBlocks,
              data
            ];

            setStreamingBlocks(
              accumulatedBlocks
            );
            setMessages(prev => prev.map(message =>
              message.id === streamingMessageIdRef.current
                ? { ...message, blocks: accumulatedBlocks }
                : message
            ));
          } else if (
            event === 'message_complete'
          ) {
            if (!streamingMessageIdRef.current) return;

            const streamedMessage =
              normalizeMessage({
                id:
                  data.message_id ||
                  'asst-' + Date.now(),
                sender: 'assistant',
                content: accumulatedText,
                blocks: accumulatedBlocks,
                provenance:
                  accumulatedBlocks.find(
                    block =>
                      block.type ===
                      'provenance'
                  ) || {},
                grounding_status:
                  data.grounding_status ||
                  'unverified'
              });

            setMessages(prev => prev.map(message =>
              message.id === streamingMessageIdRef.current
                ? { ...streamedMessage, id: message.id }
                : message
            ));

            setIsStreaming(false);
            setStreamingDelta('');
            setStreamingBlocks([]);

            loadConversations();

            // Do not let the persisted aggregate `content` replace the
            // structured streamed answer. Reload the conversation once after
            // completion, then normalize the server object before rendering.
            streamingMessageIdRef.current = null;
            abortControllerRef.current = null;

            apiClient
              .getConversation(convId)
              .then(history => {
                setMessages(
                  normalizeMessages(
                    history?.messages
                  )
                );
              })
              .catch(() => {
                // The streamed structured message remains visible if refresh
                // fails.
              });
          }
        },
        controller.signal
      );
    } catch (err) {
      if (err.name !== 'AbortError') {
        setMessages(prev => prev.map(message =>
          message.id === streamingMessageIdRef.current
            ? {
                ...message,
                content: `An error occurred: ${err.message}`,
                blocks: [],
                grounding_status: 'error'
              }
            : message
        ));
      }

      setIsStreaming(false);
      setStreamingDelta('');
      setStreamingBlocks([]);
      abortControllerRef.current = null;
      streamingMessageIdRef.current = null;
    }
  };

  const activeConv =
    conversations.find(
      c => c.id === currentId
    );

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
        onSelectConversation={
          handleSelectConversation
        }
        onNewChat={handleNewChat}
        onDeleteConversation={
          handleDeleteConversation
        }
        onTogglePin={handleTogglePin}
        onRenameConversation={
          handleRenameConversation
        }
        onArchiveConversation={
          handleArchiveConversation
        }
        showArchived={showArchived}
        onShowArchivedChange={
          handleConversationViewChange
        }
        user={user}
        onOpenAuth={() =>
          setAuthModalOpen(true)
        }
        onLogout={async () => {
          await apiClient.logout();
          setUser(null);
          loadConversations(
            showArchived
          );
        }}
      />

      {/* Main Chat Workstation */}
      <main className="chat-main">
        <ChatTopBar
          onToggleSidebar={() =>
            setSidebarOpen(!sidebarOpen)
          }
          activeTitle={
            activeConv
              ? activeConv.title
              : 'AI FAQ College Chat Bot'
          }
          onNewChat={handleNewChat}
          conversation={
            activeConv ||
            (
              currentId
                ? {
                    id: currentId,
                    college_id:
                      activeConv?.college_id ??
                      null
                  }
                : null
            )
          }
        />

        {conversationState === 'loading' ? (
          <div
            className="welcome-hero"
            role="status"
          >
            <h1 className="welcome-title">
              Loading conversation...
            </h1>
          </div>
        ) : conversationState === 'error' ? (
          <div
            className="welcome-hero"
            role="alert"
          >
            <h1 className="welcome-title">
              Conversation unavailable
            </h1>

            <p className="welcome-subtitle">
              {
                conversationError ||
                'Please try again.'
              }
            </p>
          </div>
        ) : messages.length === 0 &&
          !isStreaming ? (
          collegeCtx?.needs_onboarding &&
          collegeCtx?.onboarding_message ? (
            <div className="welcome-hero">
              <h1 className="welcome-title">
                Which college information do you want?
              </h1>

              <p className="welcome-subtitle">
                Please enter your college name in the
                chat below (for example: RC Technical,
                or AIT).
              </p>
            </div>
          ) : (
            <WelcomeHero
              onNewChat={handleNewChat}
            />
          )
        ) : (
          <MessageList
            messages={messages}
            streamingDelta={streamingDelta}
            streamingBlocks={streamingBlocks}
            isStreaming={isStreaming}
            onSelectSuggestion={prompt =>
              handleSendMessage(prompt, [])
            }
            onCollegeSwitch={
              handleCollegeSwitch
            }
            onImageClick={img =>
              setSelectedImage(img)
            }
          />
        )}

        <Composer
          onSendMessage={handleSendMessage}
          isStreaming={isStreaming}
          onStopStreaming={
            handleStopStreaming
          }
        />
      </main>

      {/* Modals */}
      <AuthModal
        isOpen={authModalOpen}
        onClose={() =>
          setAuthModalOpen(false)
        }
        onAuthSuccess={u => {
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
        onClose={() =>
          setSelectedImage(null)
        }
      />
    </div>
  );
}