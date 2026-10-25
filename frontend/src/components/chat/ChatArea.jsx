import React, { useState, useRef, useEffect } from 'react';
import {
  Send,
  Paperclip,
  Shield,
  Download,
  FileText,
  Image as ImageIcon,
  CheckCheck,
  Trash2,
  ChevronLeft,
  Radio,
  Clock,
  AlertCircle,
  RotateCcw,
  UploadCloud,
  Info,
  Hash,
} from 'lucide-react';

/**
 * ChatArea — Main conversation panel.
 * Preserves all existing functionality: sending, retry, file upload/download,
 * typing indicator, drag-and-drop, pagination, broadcast vs DM distinctions.
 */
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
  const fileInputRef = useRef(null);

  const handlePaperclipClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChosen = (e) => {
    if (e.target.files && e.target.files[0]) {
      onOpenUpload?.(e.target.files[0]);
    }
    e.target.value = '';
  };

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
      onOpenUpload?.(e.dataTransfer.files[0]);
    }
  };

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [conversation?.messages?.length]);

  const handleSend = () => {
    const text = inputText.trim();
    if (!text) return;
    onSendMessage(text);
    setInputText('');
    onTyping?.(false);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaChange = (e) => {
    const val = e.target.value;
    if (val.length > 2000) return;
    setInputText(val);

    if (onTyping) {
      onTyping(true);
      if (typingTimeoutRef.current) clearTimeout(typingTimeoutRef.current);
      typingTimeoutRef.current = setTimeout(() => onTyping(false), 2500);
    }

    // Auto-resize
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  if (!conversation) return null;

  const isBroadcast = conversation.type === 'channel' || conversation.type === 'broadcast';
  const privacyText = isBroadcast
    ? 'Public LAN Broadcast — Visible to all connected peers on local network'
    : `Private Direct Message — Visible only to you and @${conversation.username || conversation.name}`;

  return (
    <section
      className={`chat-area`}
      aria-label={`Conversation: ${conversation.name}`}
      onDragEnter={handleDrag}
      onDragOver={handleDrag}
      onDragLeave={handleDrag}
      onDrop={handleDrop}
      style={{ position: 'relative' }}
    >
      {/* Drag & Drop overlay */}
      {isDragActive && (
        <div className="drag-drop-overlay">
          <UploadCloud size={48} className="drag-overlay-icon" />
          <div className="drag-overlay-text">Drop file to share in {conversation.name}</div>
          <div className="drag-overlay-sub">LAN transfer · Max 50 MB</div>
        </div>
      )}

      {/* Hidden file input (triggered by Paperclip button) */}
      <input
        ref={fileInputRef}
        type="file"
        style={{ display: 'none' }}
        onChange={handleFileChosen}
        aria-hidden="true"
      />

      {/* Chat header */}
      <div className="chat-header">
        <div className="chat-header-info">
          <button
            className="back-to-sidebar-btn"
            onClick={onBackToSidebar}
            aria-label="Back to conversations list"
          >
            <ChevronLeft size={18} />
          </button>

          {/* Avatar */}
          <div className="avatar-wrapper">
            <div className={`user-avatar ${isBroadcast ? 'channel' : ''}`} style={{ width: 36, height: 36 }}>
              {isBroadcast
                ? <Hash size={16} />
                : (conversation.avatar || (conversation.name || 'U').slice(0, 2).toUpperCase())}
            </div>
            {!isBroadcast && (
              <span className={`status-badge ${conversation.status || 'offline'}`} />
            )}
          </div>

          <div className="chat-header-details">
            <div className="chat-header-title">
              {conversation.name}
              {isBroadcast ? (
                <span className="channel-badge">
                  <Radio size={10} /> Broadcast
                </span>
              ) : (
                <span className={`status-pill ${conversation.status === 'online' ? 'online' : 'offline'}`}>
                  {conversation.status === 'online' ? 'Online' : 'Offline'}
                </span>
              )}
            </div>

            <div className="chat-header-sub">
              {!isBroadcast && conversation.ipAddress && (
                <>
                  <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.68rem' }}>
                    {conversation.ipAddress}
                  </span>
                  <span>·</span>
                </>
              )}
              <span className="lan-encryption-pill">
                {isBroadcast ? <Radio size={10} /> : <Shield size={10} />}
                {isBroadcast ? 'Public Broadcast' : 'Private DM'}
              </span>
            </div>
          </div>
        </div>

        <div className="chat-header-actions">
          <button
            className="header-btn"
            onClick={() => onClearChat(conversation.id)}
            title="Clear conversation view"
            aria-label="Clear conversation history from view"
          >
            <Trash2 size={16} />
          </button>
        </div>
      </div>

      {/* Privacy strip */}
      <div className={`privacy-strip ${isBroadcast ? 'broadcast' : 'direct'}`}>
        {isBroadcast ? <Radio size={11} /> : <Shield size={11} />}
        <span>{privacyText}</span>
      </div>

      {/* Messages scroll area */}
      <div className="messages-container" role="log" aria-live="polite" aria-label="Messages">
        {/* Load older messages */}
        {hasMoreMessages && (
          <button
            className="load-older-btn"
            onClick={onLoadOlderMessages}
            disabled={isLoadingOlder}
          >
            {isLoadingOlder ? (
              <>
                <span style={{ width: 12, height: 12, border: '2px solid var(--text-muted)', borderTopColor: 'transparent', borderRadius: '50%', display: 'inline-block', animation: 'spin 0.7s linear infinite' }} />
                Loading...
              </>
            ) : (
              'Load older messages'
            )}
          </button>
        )}

        {/* Session label */}
        <div className="date-divider">
          <span className="date-divider-text">LAN Session</span>
        </div>

        {/* Message list */}
        {(conversation.messages || []).map((msg) => {
          // System message
          if (msg.type === 'system') {
            return (
              <div key={msg.id} className="system-message-row">
                <Info size={12} />
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
              {/* Sender name (broadcast incoming only) */}
              {!isOutgoing && isBroadcast && (
                <div className="sender-header">{msg.senderName}</div>
              )}

              <div className="message-bubble">
                {/* Text content */}
                {msg.content && (
                  <div className="message-text">{msg.content}</div>
                )}

                {/* File attachment card */}
                {msg.type === 'file' && msg.file && (
                  <div className="file-attachment-container">
                    {msg.file.type?.includes('image') && msg.file.id && (
                      <div className="file-image-preview">
                        <img
                          src={`/api/files/${msg.file.id}/download`}
                          alt={msg.file.name}
                          className="chat-preview-img"
                          loading="lazy"
                          onError={(e) => {
                            e.currentTarget.parentElement.style.display = 'none';
                          }}
                        />
                      </div>
                    )}
                    <div className="file-card">
                      <div className="file-icon-box">
                        {msg.file.type?.includes('image') ? (
                          <ImageIcon size={18} />
                        ) : (
                          <FileText size={18} />
                        )}
                      </div>
                      <div className="file-card-details">
                        <div className="file-card-name" title={msg.file.name}>
                          {msg.file.name}
                        </div>
                        <div className="file-card-meta">
                          <span>{msg.file.size}</span>
                          {msg.file.checksum && (
                            <>
                              <span>·</span>
                              <span className="file-card-hash">
                                SHA:{msg.file.checksum.slice(0, 8)}…
                              </span>
                            </>
                          )}
                        </div>
                      </div>
                      <a
                        href={`/api/files/${msg.file.id}/download`}
                        download={msg.file.name}
                        className="file-download-btn"
                        onClick={() => onDownloadFile(msg.file)}
                        title={`Download ${msg.file.name}`}
                        aria-label={`Download file: ${msg.file.name}`}
                      >
                        <Download size={14} />
                      </a>
                    </div>
                  </div>
                )}

                {/* Message metadata row */}
                <div className="message-meta">
                  <span>{msg.timestamp}</span>
                  {isOutgoing && (
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '2px' }}>
                      {msg.status === 'sending' && (
                        <Clock size={10} style={{ opacity: 0.6 }} title="Sending..." />
                      )}
                      {msg.status === 'failed' && (
                        <button
                          className="msg-retry-btn"
                          onClick={() => onRetryMessage?.(msg)}
                          title="Failed. Click to retry."
                          aria-label="Retry sending message"
                        >
                          <AlertCircle size={11} />
                          <RotateCcw size={10} />
                        </button>
                      )}
                      {(!msg.status || msg.status === 'sent') && (
                        <CheckCheck size={12} color="var(--accent-text)" title="Delivered" />
                      )}
                    </span>
                  )}
                </div>
              </div>
            </div>
          );
        })}

        {/* Typing indicator */}
        {typingUser && (
          <div className="typing-indicator">
            <div className="typing-dots">
              <span /><span /><span />
            </div>
            <span>{typingUser} is typing</span>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Message composer */}
      <div className="composer-wrapper">
        <div className="composer-box">
          <button
            type="button"
            className="composer-action-btn"
            onClick={handlePaperclipClick}
            aria-label="Attach file to send over LAN"
            title="Attach file"
          >
            <Paperclip size={17} />
          </button>

          <textarea
            ref={textareaRef}
            className="composer-textarea"
            placeholder={
              isBroadcast
                ? 'Broadcast to all LAN peers...'
                : `Message ${conversation.name}...`
            }
            rows={1}
            maxLength={2000}
            value={inputText}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            aria-label="Message input"
            aria-multiline="true"
          />

          <button
            className="send-btn"
            onClick={handleSend}
            disabled={!inputText.trim()}
            aria-label="Send message"
            title="Send (Enter)"
          >
            <Send size={15} />
          </button>
        </div>

        <div className="composer-footer-hints">
          <span>
            <span className="hint-key">Enter</span> send ·{' '}
            <span className="hint-key">Shift+Enter</span> new line
          </span>
          <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
            {inputText.length > 1800 && (
              <span style={{ color: inputText.length >= 2000 ? 'var(--status-error)' : 'var(--status-away)' }}>
                {inputText.length}/2000
              </span>
            )}
            <span style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span style={{ width: 5, height: 5, borderRadius: '50%', background: 'var(--accent-text)' }} />
              LAN socket
            </span>
          </span>
        </div>
      </div>
    </section>
  );
}
