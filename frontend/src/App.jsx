import React, { useState, useEffect, useRef, useCallback } from 'react';
import { AppHeader } from './components/layout/AppHeader';
import { Sidebar } from './components/sidebar/Sidebar';
import { ChatArea } from './components/chat/ChatArea';
import { EmptyChatState } from './components/chat/EmptyChatState';
import { AuthScreen } from './components/auth/AuthScreen';
import { FileUploadModal } from './components/files/FileUploadModal';
import { SettingsModal } from './components/settings/SettingsModal';
import { ToastContainer } from './components/common/Toast';
import { ConfirmDialog } from './components/common/ConfirmDialog';
import {
  fetchHealth,
  registerUser,
  loginUser,
  logoutUser,
  fetchCurrentUser,
  fetchUsers,
  fetchConversations,
  openDirectConversation,
  fetchConversationMessages,
  sendMessageRest,
  downloadFile,
} from './services/api';

function formatTime(isoString) {
  if (!isoString) return 'Just now';
  try {
    const d = new Date(isoString);
    if (isNaN(d.getTime())) return 'Just now';
    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  } catch {
    return 'Just now';
  }
}

function mapBackendMessage(m, currentUserId) {
  return {
    id: m.id,
    clientMsgId: m.client_msg_id,
    senderId: m.sender ? m.sender.id : null,
    senderName: m.sender ? (m.sender.display_name || m.sender.username) : 'System',
    type: m.message_type || 'text',
    content: m.content,
    file: m.file || null,
    timestamp: formatTime(m.created_at),
    status: 'sent',
    isOutgoing: m.sender && m.sender.id === currentUserId,
  };
}

export default function App() {
  // Theme state: defaults to dark charcoal
  const [theme, setTheme] = useState(() => {
    return localStorage.getItem('secure_lan_theme') || 'dark';
  });

  // Authentication state
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [currentUser, setCurrentUser] = useState(null);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);
  const [isAuthSubmitting, setIsAuthSubmitting] = useState(false);
  const [authError, setAuthError] = useState('');

  // Connection & Diagnostics
  const [connectionStatus, setConnectionStatus] = useState('connecting');
  const [backendHealth, setBackendHealth] = useState(null);

  // Conversations and active selection
  const [conversations, setConversations] = useState([]);
  const [activeConversationId, setActiveConversationId] = useState('broadcast-general');
  const [paginationInfo, setPaginationInfo] = useState({}); // convId -> { offset, total, hasMore, loading }
  const [typingUsers, setTypingUsers] = useState({}); // convId -> username

  // Mobile sidebar visibility
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);

  // Dialog states
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isUploadOpen, setIsUploadOpen] = useState(false);
  const [pendingUploadFile, setPendingUploadFile] = useState(null);
  const [isLogoutConfirmOpen, setIsLogoutConfirmOpen] = useState(false);
  const [chatToClearId, setChatToClearId] = useState(null);

  // Toasts
  const [toasts, setToasts] = useState([]);

  // Active WebSocket reference
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectAttemptsRef = useRef(0);

  // Apply theme to document body
  useEffect(() => {
    document.body.className = `theme-${theme}`;
    localStorage.setItem('secure_lan_theme', theme);
  }, [theme]);

  const addToast = (message, type = 'info') => {
    const id = `toast-${Date.now()}-${Math.random()}`;
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 4000);
  };

  const removeToast = (id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
  };

  const toggleTheme = () => {
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
    addToast(`Switched to ${theme === 'dark' ? 'light' : 'dark charcoal'} theme`, 'info');
  };

  // 1. Verify Existing Session on Mount
  useEffect(() => {
    async function verifyExistingSession() {
      try {
        const user = await fetchCurrentUser();
        setCurrentUser({
          id: user.id,
          username: user.username,
          name: user.display_name || user.username,
          avatar: user.avatar || user.username.slice(0, 2).toUpperCase(),
          ipAddress: window.location.hostname || 'localhost',
          status: 'online',
          encryptionKeyFingerprint: 'SHA256:7f4a...9b12',
        });
        setIsAuthenticated(true);
      } catch {
        setIsAuthenticated(false);
      } finally {
        setIsCheckingAuth(false);
      }
    }

    verifyExistingSession();
  }, []);

  // 2. Health check polling against FastAPI backend
  const checkBackendHealth = async (showToastOnSuccess = false) => {
    try {
      const health = await fetchHealth();
      setBackendHealth(health);
      if (health.status === 'healthy') {
        if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
          setConnectionStatus('connected');
        }
        if (showToastOnSuccess) {
          addToast(`Backend healthy: SQLite WAL online (${health.database?.tables?.length || 6} tables)`, 'success');
        }
      }
    } catch {
      setBackendHealth(null);
      setConnectionStatus('disconnected');
    }
  };

  useEffect(() => {
    checkBackendHealth();
    const interval = setInterval(checkBackendHealth, 10000);
    return () => clearInterval(interval);
  }, []);

  // 3. Load & Synchronize Conversations & Users
  const syncConversations = useCallback(async () => {
    if (!isAuthenticated || !currentUser) return;

    try {
      const [backendConvs, allUsers] = await Promise.all([
        fetchConversations(),
        fetchUsers(),
      ]);

      // Ensure broadcast channel is present
      let mergedList = backendConvs.map((c) => ({
        id: c.id,
        type: c.type,
        name: c.name || (c.peer ? (c.peer.display_name || c.peer.username) : 'Direct Peer'),
        username: c.username || c.peer?.username,
        avatar: c.avatar || (c.type === 'channel' ? '#' : (c.peer?.avatar || 'DM')),
        status: c.status || 'offline',
        ipAddress: c.ipAddress || '192.168.1.xxx',
        encryptionStatus: c.encryptionStatus || (c.type === 'channel' ? 'Public LAN Broadcast' : 'Private Direct Message'),
        unreadCount: 0,
        lastActivity: c.last_message ? formatTime(c.last_message.created_at) : 'Active',
        peer: c.peer,
        messages: [],
      }));

      // Add registered users who do not yet have an opened direct conversation
      const existingPeerUserIds = new Set(
        backendConvs
          .filter((c) => c.type === 'direct' && c.peer)
          .map((c) => c.peer.id)
      );

      const uncontactedUsers = allUsers.filter(
        (u) => u.id !== currentUser.id && !existingPeerUserIds.has(u.id)
      );

      for (const u of uncontactedUsers) {
        mergedList.push({
          id: `user-${u.id}`,
          type: 'direct',
          name: u.display_name || u.username,
          username: u.username,
          avatar: u.avatar || u.username.slice(0, 2).toUpperCase(),
          status: u.is_online ? 'online' : 'offline',
          ipAddress: '192.168.1.xxx',
          unreadCount: 0,
          lastActivity: u.is_online ? 'Active now' : 'Offline',
          encryptionStatus: 'Private Direct Message',
          peer: u,
          messages: [],
        });
      }

      setConversations((prev) => {
        // Retain existing loaded messages in memory
        return mergedList.map((newItem) => {
          const oldItem = prev.find((p) => p.id === newItem.id);
          return {
            ...newItem,
            messages: oldItem && oldItem.messages?.length ? oldItem.messages : newItem.messages,
            unreadCount: oldItem?.unreadCount || 0,
          };
        });
      });
    } catch (err) {
      console.warn('Failed to synchronize conversations:', err);
    }
  }, [isAuthenticated, currentUser]);

  useEffect(() => {
    if (isAuthenticated) {
      syncConversations();
    }
  }, [isAuthenticated, syncConversations]);

  // 4. Fetch Message History for a conversation
  const loadConversationMessages = useCallback(async (convId, isLoadMore = false) => {
    if (!convId || convId.startsWith('user-')) return;

    setPaginationInfo((prev) => ({
      ...prev,
      [convId]: { ...(prev[convId] || {}), loading: true },
    }));

    try {
      const currentOffset = isLoadMore ? (paginationInfo[convId]?.offset || 0) + 50 : 0;
      const res = await fetchConversationMessages(convId, { limit: 50, offset: currentOffset });

      const mapped = res.messages.map((m) => mapBackendMessage(m, currentUser?.id));

      setConversations((prev) =>
        prev.map((c) => {
          if (c.id === convId) {
            const newMessages = isLoadMore ? [...mapped, ...(c.messages || [])] : mapped;
            return {
              ...c,
              messages: newMessages,
              lastActivity: mapped.length ? mapped[mapped.length - 1].timestamp : c.lastActivity,
            };
          }
          return c;
        })
      );

      setPaginationInfo((prev) => ({
        ...prev,
        [convId]: {
          offset: currentOffset,
          total: res.total,
          hasMore: res.has_more,
          loading: false,
        },
      }));
    } catch (err) {
      console.warn(`Failed to load messages for ${convId}:`, err);
      setPaginationInfo((prev) => ({
        ...prev,
        [convId]: { ...(prev[convId] || {}), loading: false },
      }));
    }
  }, [currentUser?.id, paginationInfo]);

  // Load messages whenever active conversation changes
  useEffect(() => {
    if (isAuthenticated && activeConversationId && !activeConversationId.startsWith('user-')) {
      loadConversationMessages(activeConversationId);
    }
  }, [isAuthenticated, activeConversationId, loadConversationMessages]);

  // 5. Connect WebSocket (/ws/chat) with Auto-Reconnect & Heartbeat
  useEffect(() => {
    if (!isAuthenticated || !currentUser) return;

    let socket;
    let heartbeatInterval;
    let isMounted = true;

    const connectWebSocket = () => {
      setConnectionStatus('connecting');
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${protocol}//${window.location.host}/ws/chat`;

      try {
        socket = new WebSocket(wsUrl);
        wsRef.current = socket;

        socket.onopen = () => {
          if (!isMounted) return;
          setConnectionStatus('connected');
          reconnectAttemptsRef.current = 0;

          // Heartbeat ping every 20 seconds
          heartbeatInterval = setInterval(() => {
            if (socket.readyState === WebSocket.OPEN) {
              socket.send(JSON.stringify({ type: 'ping' }));
            }
          }, 20000);
        };

        socket.onmessage = (event) => {
          if (!isMounted) return;
          try {
            const payload = JSON.parse(event.data);

            // AUTH_SUCCESS
            if (payload.event === 'AUTH_SUCCESS') {
              syncConversations();
            }

            // PRESENCE_CHANGE
            if (payload.event === 'PRESENCE_CHANGE') {
              const { user_id, status } = payload.data;
              setConversations((prev) =>
                prev.map((c) => {
                  if (c.peer && c.peer.id === user_id) {
                    return { ...c, status };
                  }
                  if (c.id === `user-${user_id}`) {
                    return { ...c, status };
                  }
                  return c;
                })
              );
            }

            // MESSAGE_ACK (Delivery confirmed by server)
            if (payload.event === 'MESSAGE_ACK') {
              const { client_msg_id, message_id, conversation_id } = payload.data;
              setConversations((prev) =>
                prev.map((c) => {
                  if (c.id === conversation_id) {
                    return {
                      ...c,
                      messages: (c.messages || []).map((m) =>
                        m.clientMsgId === client_msg_id
                          ? { ...m, id: message_id, status: 'sent' }
                          : m
                      ),
                    };
                  }
                  return c;
                })
              );
            }

            // NEW_MESSAGE (Delivered to eligible recipients)
            if (payload.event === 'NEW_MESSAGE') {
              const { message: rawMsg, conversation_id } = payload.data;
              const mapped = mapBackendMessage(rawMsg, currentUser.id);

              setConversations((prev) => {
                return prev.map((c) => {
                  if (c.id === conversation_id) {
                    const currentMsgs = c.messages || [];
                    const existsByClientMsgId = mapped.clientMsgId && currentMsgs.some((m) => m.clientMsgId === mapped.clientMsgId);
                    const existsById = currentMsgs.some((m) => m.id === mapped.id);

                    let updatedList;
                    if (existsByClientMsgId) {
                      updatedList = currentMsgs.map((m) =>
                        m.clientMsgId === mapped.clientMsgId ? mapped : m
                      );
                    } else if (!existsById) {
                      updatedList = [...currentMsgs, mapped];
                    } else {
                      updatedList = currentMsgs;
                    }

                    const isUnread = conversation_id !== activeConversationId && !mapped.isOutgoing;

                    return {
                      ...c,
                      lastActivity: mapped.timestamp,
                      unreadCount: isUnread ? (c.unreadCount || 0) + 1 : c.unreadCount,
                      messages: updatedList,
                    };
                  }
                  return c;
                });
              });

              if (conversation_id !== activeConversationId && !mapped.isOutgoing) {
                addToast(`New message from ${mapped.senderName}`, 'info');
              }
            }

            // TYPING_INDICATOR
            if (payload.event === 'TYPING_INDICATOR') {
              const { conversation_id, username, is_typing } = payload.data;
              setTypingUsers((prev) => ({
                ...prev,
                [conversation_id]: is_typing ? username : null,
              }));
            }

            // ERROR
            if (payload.event === 'ERROR') {
              const { client_msg_id, message } = payload.data;
              if (client_msg_id) {
                setConversations((prev) =>
                  prev.map((c) => ({
                    ...c,
                    messages: (c.messages || []).map((m) =>
                      m.clientMsgId === client_msg_id ? { ...m, status: 'failed' } : m
                    ),
                  }))
                );
              }
              addToast(`Message error: ${message}`, 'error');
            }
          } catch (e) {
            console.error('Error handling WebSocket frame:', e);
          }
        };

        socket.onclose = () => {
          if (!isMounted) return;
          clearInterval(heartbeatInterval);
          setConnectionStatus('disconnected');

          // Exponential backoff reconnect
          const delay = Math.min(1000 * Math.pow(2, reconnectAttemptsRef.current), 10000);
          reconnectAttemptsRef.current += 1;
          reconnectTimeoutRef.current = setTimeout(() => {
            if (isMounted && isAuthenticated) {
              connectWebSocket();
            }
          }, delay);
        };
      } catch (err) {
        setConnectionStatus('disconnected');
      }
    };

    connectWebSocket();

    return () => {
      isMounted = false;
      clearInterval(heartbeatInterval);
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    };
  }, [isAuthenticated, currentUser?.id, activeConversationId, syncConversations]);

  // 6. Auth Handlers
  const handleLogin = async ({ username, password }) => {
    setIsAuthSubmitting(true);
    setAuthError('');
    try {
      const user = await loginUser({ username, password });
      setCurrentUser({
        id: user.id,
        username: user.username,
        name: user.display_name || user.username,
        avatar: user.avatar || user.username.slice(0, 2).toUpperCase(),
        ipAddress: window.location.hostname || 'localhost',
        status: 'online',
        encryptionKeyFingerprint: 'SHA256:7f4a...9b12',
      });
      setIsAuthenticated(true);
      addToast(`Signed in as ${user.username}`, 'success');
    } catch (err) {
      setAuthError(err.message);
      addToast(err.message, 'error');
    } finally {
      setIsAuthSubmitting(false);
    }
  };

  const handleRegister = async ({ username, password, displayName }) => {
    setIsAuthSubmitting(true);
    setAuthError('');
    try {
      const user = await registerUser({ username, password, displayName });
      setCurrentUser({
        id: user.id,
        username: user.username,
        name: user.display_name || user.username,
        avatar: user.avatar || user.username.slice(0, 2).toUpperCase(),
        ipAddress: window.location.hostname || 'localhost',
        status: 'online',
        encryptionKeyFingerprint: 'SHA256:7f4a...9b12',
      });
      setIsAuthenticated(true);
      addToast(`Registered account for ${user.username}`, 'success');
    } catch (err) {
      setAuthError(err.message);
      addToast(err.message, 'error');
    } finally {
      setIsAuthSubmitting(false);
    }
  };

  const handleLogout = async () => {
    try {
      await logoutUser();
    } catch (err) {
      console.warn('Logout API error:', err);
    } finally {
      if (wsRef.current) {
        wsRef.current.close();
      }
      setIsAuthenticated(false);
      setCurrentUser(null);
      setIsLogoutConfirmOpen(false);
      setIsSettingsOpen(false);
      addToast('Signed out of LAN session', 'info');
    }
  };

  // 7. Select Conversation Handler
  const handleSelectConversation = async (convId) => {
    setIsMobileSidebarOpen(false);

    // If selecting an uncontacted peer placeholder (e.g., 'user-5')
    if (convId.startsWith('user-')) {
      const targetUserId = parseInt(convId.replace('user-', ''), 10);
      try {
        const directConv = await openDirectConversation(targetUserId);
        setActiveConversationId(directConv.id);
        await syncConversations();
        await loadConversationMessages(directConv.id);
        return;
      } catch (err) {
        addToast(`Could not initialize chat: ${err.message}`, 'error');
        return;
      }
    }

    setActiveConversationId(convId);
    setConversations((prev) =>
      prev.map((c) => (c.id === convId ? { ...c, unreadCount: 0 } : c))
    );
    loadConversationMessages(convId);
  };

  // 8. Send Message with Delivery Confirmation & Fallback
  const handleSendMessage = async (text) => {
    if (!activeConversationId) return;

    const clientMsgId = `cmsg-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
    const optimisticMessage = {
      id: clientMsgId,
      clientMsgId,
      senderId: currentUser.id,
      senderName: currentUser.name || currentUser.username,
      type: 'text',
      content: text,
      timestamp: formatTime(new Date().toISOString()),
      status: 'sending',
      isOutgoing: true,
    };

    // Add optimistic message to conversation
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === activeConversationId) {
          return {
            ...c,
            lastActivity: optimisticMessage.timestamp,
            messages: [...(c.messages || []), optimisticMessage],
          };
        }
        return c;
      })
    );

    // Send via WebSocket if open
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          event: 'CHAT_MESSAGE',
          data: {
            conversation_id: activeConversationId,
            content: text,
            client_msg_id: clientMsgId,
          },
        })
      );
    } else {
      // Fallback: send via REST API
      try {
        const savedMsg = await sendMessageRest(activeConversationId, {
          content: text,
          clientMsgId,
        });
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id === activeConversationId) {
              return {
                ...c,
                messages: (c.messages || []).map((m) =>
                  m.clientMsgId === clientMsgId
                    ? { ...m, id: savedMsg.id, status: 'sent' }
                    : m
                ),
              };
            }
            return c;
          })
        );
      } catch (err) {
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id === activeConversationId) {
              return {
                ...c,
                messages: (c.messages || []).map((m) =>
                  m.clientMsgId === clientMsgId ? { ...m, status: 'failed' } : m
                ),
              };
            }
            return c;
          })
        );
        addToast(`Failed to send message: ${err.message}`, 'error');
      }
    }
  };

  // 9. Retry Failed Message
  const handleRetryMessage = async (failedMsg) => {
    // Reset status to sending
    setConversations((prev) =>
      prev.map((c) => {
        if (c.id === activeConversationId) {
          return {
            ...c,
            messages: (c.messages || []).map((m) =>
              m.clientMsgId === failedMsg.clientMsgId ? { ...m, status: 'sending' } : m
            ),
          };
        }
        return c;
      })
    );

    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(
        JSON.stringify({
          event: 'CHAT_MESSAGE',
          data: {
            conversation_id: activeConversationId,
            content: failedMsg.content,
            client_msg_id: failedMsg.clientMsgId,
          },
        })
      );
    } else {
      try {
        const savedMsg = await sendMessageRest(activeConversationId, {
          content: failedMsg.content,
          clientMsgId: failedMsg.clientMsgId,
        });
        setConversations((prev) =>
          prev.map((c) => {
            if (c.id === activeConversationId) {
              return {
                ...c,
                messages: (c.messages || []).map((m) =>
                  m.clientMsgId === failedMsg.clientMsgId
                    ? { ...m, id: savedMsg.id, status: 'sent' }
                    : m
                ),
              };
            }
            return c;
          })
        );
      } catch (err) {
        addToast(`Retry failed: ${err.message}`, 'error');
      }
    }
  };

  // 10. Typing Status Emitter
  const handleTyping = (isTyping) => {
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN && activeConversationId) {
      wsRef.current.send(
        JSON.stringify({
          event: 'TYPING_INDICATOR',
          data: {
            conversation_id: activeConversationId,
            is_typing: isTyping,
          },
        })
      );
    }
  };

  const handleClearChatConfirm = () => {
    if (!chatToClearId) return;

    setConversations((prev) =>
      prev.map((conv) => {
        if (conv.id === chatToClearId) {
          return {
            ...conv,
            messages: [
              {
                id: `sys-${Date.now()}`,
                senderId: 'system',
                senderName: 'LAN System',
                type: 'system',
                content: 'Chat view cleared for this session.',
                timestamp: 'Just now',
              },
            ],
          };
        }
        return conv;
      })
    );

    setChatToClearId(null);
    addToast('Conversation view cleared', 'info');
  };

  // 11. File Transfer Handlers
  const handleOpenUpload = (file = null) => {
    setPendingUploadFile(file && file instanceof File ? file : null);
    setIsUploadOpen(true);
  };

  const handleDownloadFile = async (fileInfo) => {
    if (!fileInfo || !fileInfo.id) return;
    try {
      addToast(`Downloading ${fileInfo.name}...`, 'info');
      await downloadFile(fileInfo.id, fileInfo.name);
      addToast(`Downloaded ${fileInfo.name}`, 'success');
    } catch (err) {
      addToast(`Download failed: ${err.message}`, 'error');
    }
  };

  const handleUploadComplete = (result) => {
    setIsUploadOpen(false);
    setPendingUploadFile(null);
    addToast(`File shared over LAN: ${result.original_name}`, 'success');
  };

  const activeConversation = conversations.find((c) => c.id === activeConversationId);
  const activePagination = paginationInfo[activeConversationId] || {};

  // Loading indicator while checking session cookie
  if (isCheckingAuth) {
    return (
      <div className="auth-page">
        <div style={{ color: 'var(--text-secondary)', fontSize: '0.88rem' }}>
          Checking local LAN session...
        </div>
      </div>
    );
  }

  // Render AuthScreen if unauthenticated
  if (!isAuthenticated || !currentUser) {
    return (
      <>
        <AuthScreen
          onLogin={handleLogin}
          onRegister={handleRegister}
          authError={authError}
          isSubmitting={isAuthSubmitting}
        />
        <ToastContainer toasts={toasts} onClose={removeToast} />
      </>
    );
  }

  return (
    <div className="app-container">
      {/* Header */}
      <AppHeader
        theme={theme}
        onToggleTheme={toggleTheme}
        connectionStatus={connectionStatus}
        onChangeConnectionStatus={(newStatus) => {
          setConnectionStatus(newStatus);
          addToast(`Connection status: ${newStatus}`, newStatus === 'connected' ? 'success' : 'warning');
        }}
        backendHealth={backendHealth}
        onRefreshHealth={() => checkBackendHealth(true)}
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenProfile={() => setIsSettingsOpen(true)}
        onToggleMobileSidebar={() => setIsMobileSidebarOpen(!isMobileSidebarOpen)}
        currentUser={currentUser}
      />

      {/* Main Workspace Layout */}
      <main className="workspace-layout">
        <Sidebar
          conversations={conversations}
          activeConversationId={activeConversationId}
          onSelectConversation={handleSelectConversation}
          currentUser={currentUser}
          onOpenProfile={() => setIsSettingsOpen(true)}
          isMobileOpen={isMobileSidebarOpen}
        />

        {activeConversation ? (
          <ChatArea
            conversation={activeConversation}
            currentUser={currentUser}
            onSendMessage={handleSendMessage}
            onRetryMessage={handleRetryMessage}
            onOpenUpload={handleOpenUpload}
            onClearChat={(id) => setChatToClearId(id)}
            onBackToSidebar={() => setIsMobileSidebarOpen(true)}
            onDownloadFile={handleDownloadFile}
            onLoadOlderMessages={() => loadConversationMessages(activeConversationId, true)}
            hasMoreMessages={activePagination.hasMore}
            isLoadingOlder={activePagination.loading}
            typingUser={typingUsers[activeConversationId]}
            onTyping={handleTyping}
          />
        ) : (
          <EmptyChatState
            onSelectBroadcast={() => setActiveConversationId('broadcast-general')}
            onOpenUpload={() => handleOpenUpload(null)}
          />
        )}
      </main>

      {/* File Upload Modal */}
      <FileUploadModal
        isOpen={isUploadOpen}
        onClose={() => {
          setIsUploadOpen(false);
          setPendingUploadFile(null);
        }}
        onUploadComplete={handleUploadComplete}
        conversationId={activeConversation ? activeConversation.id : 'broadcast-general'}
        activeTargetName={activeConversation ? activeConversation.name : 'LAN Broadcast'}
        initialFile={pendingUploadFile}
      />

      {/* Settings & Profile Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        currentUser={currentUser}
        onUpdateUser={(updated) => {
          setCurrentUser(updated);
          setIsSettingsOpen(false);
          addToast('Profile updated', 'success');
        }}
        onRequestLogout={() => setIsLogoutConfirmOpen(true)}
        onCopyIp={() => {
          navigator.clipboard?.writeText(currentUser.ipAddress);
          addToast(`Copied LAN IP: ${currentUser.ipAddress}`, 'success');
        }}
      />

      {/* Logout Confirmation Dialog */}
      <ConfirmDialog
        isOpen={isLogoutConfirmOpen}
        title="Sign Out of LAN"
        message="Are you sure you want to sign out? Your session cookie will be cleared and your presence will be set to offline."
        confirmLabel="Sign Out"
        isDanger={true}
        onConfirm={handleLogout}
        onCancel={() => setIsLogoutConfirmOpen(false)}
      />

      {/* Clear Chat Confirmation Dialog */}
      <ConfirmDialog
        isOpen={!!chatToClearId}
        title="Clear Conversation History"
        message="This will clear all messages in this conversation for your current session view."
        confirmLabel="Clear Messages"
        isDanger={true}
        onConfirm={handleClearChatConfirm}
        onCancel={() => setChatToClearId(null)}
      />

      {/* Toast Notification Container */}
      <ToastContainer toasts={toasts} onClose={removeToast} />
    </div>
  );
}
