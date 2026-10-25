import React, { useState } from 'react';
import { Search, X, Hash, Shield } from 'lucide-react';

/**
 * Sidebar — Conversations panel (280px).
 * Shows broadcast channels and direct peer conversations.
 * All data comes from real application state — no dummy data.
 */
export function Sidebar({
  conversations,
  activeConversationId,
  onSelectConversation,
  currentUser,
  onOpenProfile,
  isMobileOpen,
}) {
  const [searchQuery, setSearchQuery] = useState('');
  const [filterTab, setFilterTab] = useState('all'); // 'all' | 'channels' | 'peers'

  const filteredConversations = conversations.filter((item) => {
    if (filterTab === 'channels' && item.type !== 'channel' && item.type !== 'broadcast') return false;
    if (filterTab === 'peers' && item.type !== 'direct') return false;
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      (item.name || '').toLowerCase().includes(q) ||
      (item.username || '').toLowerCase().includes(q) ||
      (item.ipAddress || '').includes(q)
    );
  });

  const channels = filteredConversations.filter(
    (c) => c.type === 'channel' || c.type === 'broadcast'
  );
  const directPeers = filteredConversations.filter((c) => c.type === 'direct');

  const getLastMessagePreview = (conv) => {
    if (!conv.messages || conv.messages.length === 0) return 'No messages yet';
    const last = conv.messages[conv.messages.length - 1];
    if (last.type === 'file') return `Attachment: ${last.file?.name || 'File'}`;
    if (last.type === 'system') return last.content;
    return last.content;
  };

  const renderConversationItem = (item) => {
    const isActive = item.id === activeConversationId;
    const isBroadcast = item.type === 'channel' || item.type === 'broadcast';
    const hasUnread = (item.unreadCount || 0) > 0;

    return (
      <div
        key={item.id}
        className={`conversation-item ${isActive ? 'active' : ''} ${hasUnread ? 'unread' : ''}`}
        onClick={() => onSelectConversation(item.id)}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ' ') onSelectConversation(item.id);
        }}
        aria-pressed={isActive}
        aria-label={`${isBroadcast ? 'Channel' : 'Direct message'}: ${item.name}${hasUnread ? `, ${item.unreadCount} unread` : ''}`}
      >
        {/* Avatar */}
        <div className="avatar-wrapper">
          <div className={`user-avatar ${isBroadcast ? 'channel' : ''}`}>
            {isBroadcast ? <Hash size={16} /> : (item.avatar || (item.name || 'U').slice(0, 2).toUpperCase())}
          </div>
          {!isBroadcast && (
            <span
              className={`status-badge ${item.status || 'offline'}`}
              title={`Status: ${item.status || 'offline'}`}
              aria-label={`${item.name} is ${item.status || 'offline'}`}
            />
          )}
        </div>

        {/* Content */}
        <div className="item-content">
          <div className="item-top">
            <span className="item-name">{item.name}</span>
            <span className="item-time">{item.lastActivity}</span>
          </div>
          <div className="item-bottom">
            <span className="item-preview">{getLastMessagePreview(item)}</span>
            {hasUnread ? (
              <span className="unread-badge">{item.unreadCount > 99 ? '99+' : item.unreadCount}</span>
            ) : (
              !isBroadcast && item.ipAddress && item.ipAddress !== '192.168.1.xxx' && (
                <span className="item-ip-badge">{item.ipAddress}</span>
              )
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <aside
      className={`sidebar ${!isMobileOpen ? 'hidden-mobile' : ''}`}
      aria-label="Conversations and LAN peers"
    >
      {/* Search */}
      <div className="sidebar-search-section">
        <div className="search-input-wrapper">
          <Search size={14} className="search-icon" aria-hidden="true" />
          <input
            type="search"
            className="search-input"
            placeholder="Search peers, channels..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search conversations"
          />
          {searchQuery && (
            <button
              className="search-clear-btn"
              onClick={() => setSearchQuery('')}
              aria-label="Clear search"
            >
              <X size={13} />
            </button>
          )}
        </div>
      </div>

      {/* Filter tabs */}
      <div className="sidebar-filters" role="tablist" aria-label="Conversation filters">
        {[
          { id: 'all', label: `All (${conversations.length})` },
          { id: 'channels', label: 'Channels' },
          { id: 'peers', label: 'Peers' },
        ].map(({ id, label }) => (
          <button
            key={id}
            type="button"
            role="tab"
            aria-selected={filterTab === id}
            className={`filter-tab ${filterTab === id ? 'active' : ''}`}
            onClick={() => setFilterTab(id)}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Conversation list */}
      <div className="sidebar-list" role="list">
        {channels.length > 0 && (
          <>
            <div className="list-section-header" aria-label="Broadcast channels section">
              Broadcast
            </div>
            {channels.map(renderConversationItem)}
          </>
        )}

        {directPeers.length > 0 && (
          <>
            <div className="list-section-header" aria-label="Direct messages section">
              Direct Messages
            </div>
            {directPeers.map(renderConversationItem)}
          </>
        )}

        {filteredConversations.length === 0 && (
          <div className="sidebar-empty">
            {searchQuery
              ? `No results for "${searchQuery}"`
              : 'No conversations yet.\nStart by selecting a LAN peer.'}
          </div>
        )}
      </div>

      {/* Footer: current user */}
      <div className="sidebar-footer">
        <div
          className="current-user-pill"
          onClick={onOpenProfile}
          role="button"
          tabIndex={0}
          onKeyDown={(e) => { if (e.key === 'Enter') onOpenProfile(); }}
          aria-label="Open profile and settings"
        >
          <div className="avatar-wrapper">
            <div
              className="user-avatar"
              style={{
                width: '32px',
                height: '32px',
                fontSize: '0.68rem',
                background: 'linear-gradient(135deg, rgba(16,185,129,0.2), rgba(16,185,129,0.08))',
                borderColor: 'var(--accent-border)',
                color: 'var(--accent-text)',
              }}
            >
              {currentUser.avatar}
            </div>
            <span className="status-badge online" aria-label="You are online" />
          </div>
          <div className="current-user-info">
            <span className="current-user-name">{currentUser.name}</span>
            <span className="current-user-sub">{currentUser.ipAddress}</span>
          </div>
        </div>

        <div className="sidebar-secure-badge" title="Zero-cloud LAN">
          <Shield size={11} />
          <span>Local</span>
        </div>
      </div>
    </aside>
  );
}
