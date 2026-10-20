import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Paperclip,
  Shield,
  Download,
  FileText,
  Image as ImageIcon,
  Check,
  CheckCheck,
  Trash2,
  Info,
  ChevronLeft,
  Radio,
  Clock,
  AlertCircle,
  RotateCcw,
  UploadCloud,
} from 'lucide-react';

export function ChatArea({
  conversation,
  currentUser,
  onSendMessage,
  onRetryMessage,
  onOpenUpload,
  onClearChat,
  onBackToSidebar,
  onDownloadFile,
  onLoadOlderMessages,
  hasMoreMessages = false,
  isLoadingOlder = false,
  typingUser = null,
  onTyping = null,
}) {
  const [inputText, setInputText] = useState('');
  const [isDragActive, setIsDragActive] = useState(false);
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const typingTimeoutRef = useRef(null);

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setIsDragActive(true);
    } else if (e.type === 'dragleave') {
      setIsDragActive(false);
    }
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      if (onOpenUpload) {
        onOpenUpload(e.dataTransfer.files[0]);
      }
    }
  };

  // Auto-scroll to bottom whenever new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation?.messages?.length]);

  // Handle send message
  const handleSend = () => {
    const text = inputText.trim();
    if (!text) return;
    onSendMessage(text);
    setInputText('');

    if (onTyping) {
      onTyping(false);
    }

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  // Keyboard navigation: Enter sends, Shift+Enter adds newline
  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaChange = (e) => {
    const val = e.target.value;
    if (val.length > 2000) return; // Strict length enforcement
    setInputText(val);

    // Typing indicator callback
    if (onTyping) {
      onTyping(true);
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = setTimeout(() => {
        onTyping(false);
      }, 2500);
    }

    // Auto-resize textarea
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  if (!conversation) return null;

  const isBroadcast = conversation.type === 'channel' || conversation.id === 'broadcast-general';
  const privacyExpectationText = isBroadcast
    ? 'Public LAN Broadcast — Visible to all connected peers on local network'
    : `Private Direct Message (E2E Isolation) — Visible only to you and @${conversation.username || conversation.name}`;

  return (
    <section
      className={`chat-area ${isDragActive ? 'drag-over' : ''}`}
      aria-label={`Conversation with ${conversation.name}`}
      onDragEnter={handleDrag}
      onDragOver={handleDrag}
      onDragLeave={handleDrag}
      onDrop={handleDrop}
      style={{ position: 'relative' }}
    >
      {/* Drag & Drop Visual Overlay */}
      {isDragActive && (
        <div style={{
          position: 'absolute',
          inset: 0,
          backgroundColor: 'rgba(15, 23, 42, 0.88)',
          zIndex: 40,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '12px',
          border: '2px dashed var(--accent-primary)',
          borderRadius: 'var(--radius-lg)',
          backdropFilter: 'blur(3px)',
          pointerEvents: 'none',
        }}>
          <UploadCloud size={44} color="var(--accent-text)" />
          <div style={{ fontSize: '1.05rem', fontWeight: 600, color: 'var(--text-primary)' }}>
            Drop file to share in {conversation.name}
          </div>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            LAN streaming transfer • Max 50 MB
          </div>
        </div>
      )}

      {/* Chat Header */}
      <div className="chat-header">
        <div className="chat-header-info">
          <button
            className="back-to-sidebar-btn"
            onClick={onBackToSidebar}
            aria-label="Back to conversations list"
          >
            <ChevronLeft size={20} />
          </button>

          <div className="avatar-wrapper">
            <div className={`user-avatar ${isBroadcast ? 'channel' : ''}`}>
              {conversation.avatar || (isBroadcast ? '#' : 'DM')}
            </div>
            {!isBroadcast && (
              <span className={`status-badge ${conversation.status || 'offline'}`} />
            )}
          </div>

          <div className="chat-header-details">
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <h2 className="chat-header-title">{conversation.name}</h2>
              {isBroadcast ? (
                <span className="channel-badge" title="Public Broadcast">Broadcast</span>
              ) : (
                <span className="status-pill online" style={{ fontSize: '0.68rem', padding: '1px 6px' }}>
                  {conversation.status === 'online' ? 'Online' : 'Offline'}
                </span>
              )}
            </div>

            <div className="chat-header-sub">
              <span>IP: {conversation.ipAddress || 'LAN'}</span>
              <span>•</span>
              <span className="lan-encryption-pill" title={privacyExpectationText}>
                {isBroadcast ? <Radio size={11} /> : <Shield size={11} />}
                {isBroadcast ? 'Public Broadcast' : 'Private Direct Message'}
              </span>
            </div>
          </div>
        </div>

        <div className="chat-header-actions">
          <button
            className="header-btn"
            onClick={() => onClearChat(conversation.id)}
            title="Clear conversation history from view"
            aria-label="Clear conversation history"
          >
            <Trash2 size={17} />
          </button>
        </div>
      </div>

      {/* Privacy Notice Banner */}
      <div
        style={{
          padding: '6px 16px',
          backgroundColor: isBroadcast ? 'rgba(234, 179, 8, 0.08)' : 'rgba(16, 185, 129, 0.08)',
          borderBottom: '1px solid var(--border-color)',
          fontSize: '0.74rem',
          color: isBroadcast ? 'var(--status-connecting)' : 'var(--accent-text)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        {isBroadcast ? <Radio size={13} /> : <Shield size={13} />}
        <span>{privacyExpectationText}</span>
      </div>

      {/* Messages Scroll Area */}
      <div className="messages-container" role="log" aria-live="polite">
        {/* Pagination Trigger: Load Older Messages */}
        {hasMoreMessages && (
          <div style={{ textAlign: 'center', margin: '8px 0' }}>
            <button
              onClick={onLoadOlderMessages}
              disabled={isLoadingOlder}
              style={{
                background: 'var(--surface-color)',
                border: '1px solid var(--border-color)',
                color: 'var(--text-secondary)',
                fontSize: '0.75rem',
                padding: '4px 12px',
                borderRadius: '12px',
                cursor: 'pointer',
              }}
            >
              {isLoadingOlder ? 'Loading earlier messages...' : '↑ Load older messages'}
            </button>
          </div>
        )}

        <div className="date-divider">
          <span className="date-divider-text">Local LAN Session Messages</span>
        </div>

        {(conversation.messages || []).map((msg) => {
          if (msg.type === 'system') {
            return (
              <div key={msg.id} className="system-message-row">
                <Info size={13} />
                <span>{msg.content}</span>
              </div>
            );
          }

          const isOutgoing = msg.senderId === currentUser.id;

          return (
            <div
              key={msg.id}
              className={`message-row ${isOutgoing ? 'outgoing' : 'incoming'}`}
            >
              {!isOutgoing && isBroadcast && (
                <div className="sender-header">
                  <span>{msg.senderName}</span>
                </div>
              )}

              <div className="message-bubble">
                <div className="message-text">{msg.content}</div>

                {/* File Attachment Card */}
                {msg.type === 'file' && msg.file && (
                  <div className="file-card">
                    <div className="file-icon-box">
                      {msg.file.type?.includes('image') ? (
                        <ImageIcon size={20} />
                      ) : (
                        <FileText size={20} />
                      )}
                    </div>
                    <div className="file-card-details">
                      <div className="file-card-name" title={msg.file.name}>{msg.file.name}</div>
                      <div className="file-card-meta">
                        <span>{msg.file.size}</span>
                        <span>•</span>
                        <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.62rem' }}>
                          SHA-256: {msg.file.checksum?.slice(0, 8)}...
                        </span>
                      </div>
                    </div>
                    <button
                      className="file-download-btn"
                      onClick={() => onDownloadFile(msg.file)}
                      title="Download file over LAN"
                      aria-label={`Download ${msg.file.name}`}
                    >
                      <Download size={15} />
                    </button>
                  </div>
                )}

                {/* Message Delivery State & Metadata */}
                <div className="message-meta">
                  <span>{msg.timestamp}</span>

                  {isOutgoing && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '3px' }}>
                      {msg.status === 'sending' && (
                        <span title="Sending over LAN socket...">
                          <Clock size={11} color="var(--text-muted)" />
                        </span>
                      )}
                      {msg.status === 'failed' && (
                        <button
                          onClick={() => onRetryMessage && onRetryMessage(msg)}
                          title="Delivery failed. Click to retry."
                          style={{
                            background: 'transparent',
                            border: 'none',
                            color: 'var(--status-offline)',
                            cursor: 'pointer',
                            display: 'inline-flex',
                            alignItems: 'center',
                            gap: '2px',
                            padding: 0,
                          }}
                        >
                          <AlertCircle size={12} />
                          <RotateCcw size={10} />
                        </button>
                      )}
                      {(!msg.status || msg.status === 'sent') && (
                        <span title="Server confirmed & persisted in SQLite">
                          <CheckCheck size={13} color="var(--accent-text)" />
                        </span>
                      )}
                    </span>
                  )}

                  {msg.isLocalMock && (
                    <span className="mock-badge" title="Initial mock notice">Mock</span>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* Transient Typing Indicator */}
        {typingUser && (
          <div style={{ padding: '6px 16px', color: 'var(--text-muted)', fontSize: '0.78rem', fontStyle: 'italic' }}>
            {typingUser} is typing...
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Message Composer */}
      <div className="composer-wrapper">
        <div className="composer-box">
          <button
            className="composer-action-btn"
            onClick={onOpenUpload}
            aria-label="Attach file to send over LAN"
            title="Attach and share file over LAN"
          >
            <Paperclip size={18} />
          </button>

          <textarea
            ref={textareaRef}
            className="composer-textarea"
            placeholder={
              isBroadcast
                ? 'Broadcast message to all LAN peers (visible to entire network)...'
                : `Message ${conversation.name} securely...`
            }
            rows={1}
            maxLength={2000}
            value={inputText}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            aria-label="Message input"
          />

          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!inputText.trim()}
            aria-label="Send message"
            title="Send (Enter)"
          >
            <Send size={16} />
          </button>
        </div>

        <div className="composer-footer-hints">
          <span>
            Press <span className="hint-key">Enter</span> to send, <span className="hint-key">Shift + Enter</span> for new line
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {inputText.length > 1800 && (
              <span style={{ color: inputText.length >= 2000 ? 'var(--status-offline)' : 'var(--status-connecting)' }}>
                {inputText.length} / 2000
              </span>
            )}
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: '5px', height: '5px', borderRadius: '50%', background: 'var(--accent-text)' }} />
              Zero-cloud LAN socket buffer
            </span>
          </span>
        </div>
      </div>
    </section>
  );
}
