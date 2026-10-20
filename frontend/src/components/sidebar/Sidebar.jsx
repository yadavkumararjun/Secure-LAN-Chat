import React, { useState } from 'react';
import { Search, X, Hash, User, Shield, Radio, Volume2 } from 'lucide-react';

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
    // Tab filter
    if (filterTab === 'channels' && item.type !== 'channel') return false;
    if (filterTab === 'peers' && item.type !== 'direct') return false;

    // Search query filter
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    const nameMatch = (item.name || '').toLowerCase().includes(q);
    const userMatch = (item.username || '').toLowerCase().includes(q);
    const ipMatch = (item.ipAddress || '').includes(q);
    return nameMatch || userMatch || ipMatch;
  });

  const channels = filteredConversations.filter((c) => c.type === 'channel');
  const directPeers = filteredConversations.filter((c) => c.type === 'direct');

  const getLastMessagePreview = (conv) => {
    if (!conv.messages || conv.messages.length === 0) return 'No messages yet';
    const last = conv.messages[conv.messages.length - 1];
    if (last.type === 'file') return `📎 File: ${last.file?.name || 'Attachment'}`;
    if (last.type === 'system') return `ℹ️ ${last.content}`;
    return last.content;
  };

  return (
    <aside
      className={`sidebar ${!isMobileOpen ? 'hidden-mobile' : ''}`}
      aria-label="Conversations and online peers"
    >
      {/* Search Bar */}
      <div className="sidebar-search-section">
        <div className="search-input-wrapper">
          <Search size={15} className="search-icon" />
          <input
            type="text"
            className="search-input"
            placeholder="Search channels, peers, IP..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            aria-label="Search conversations"
          />
          {searchQuery && (
            <button
              className="search-clear-btn"
              onClick={() => setSearchQuery('')}
              aria-label="Clear search input"
            >
              <X size={14} />
            </button>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="sidebar-filters" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={filterTab === 'all'}
          className={`filter-tab ${filterTab === 'all' ? 'active' : ''}`}
          onClick={() => setFilterTab('all')}
        >
          All ({conversations.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={filterTab === 'channels'}
          className={`filter-tab ${filterTab === 'channels' ? 'active' : ''}`}
          onClick={() => setFilterTab('channels')}
        >
          Channels
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={filterTab === 'peers'}
          className={`filter-tab ${filterTab === 'peers' ? 'active' : ''}`}
          onClick={() => setFilterTab('peers')}
        >
          LAN Peers
        </button>
      </div>

      {/* Conversation List */}
      <div className="sidebar-list">
        {channels.length > 0 && (
          <>
            <div className="list-section-header">Broadcast Channels</div>
            {channels.map((conv) => {
              const isActive = conv.id === activeConversationId;
              return (
                <div
                  key={conv.id}
                  className={`conversation-item ${isActive ? 'active' : ''}`}
                  onClick={() => onSelectConversation(conv.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelectConversation(conv.id); }}
                  aria-pressed={isActive}
                >
                  <div className="avatar-wrapper">
                    <div className="user-avatar channel">
                      <Hash size={18} />
                    </div>
                  </div>

                  <div className="item-content">
                    <div className="item-top">
                      <span className="item-name">{conv.name}</span>
                      <span className="item-time">{conv.lastActivity}</span>
                    </div>
                    <div className="item-bottom">
                      <span className="item-preview">{getLastMessagePreview(conv)}</span>
                      {conv.unreadCount > 0 && (
                        <span className="unread-badge">{conv.unreadCount}</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </>
        )}

        {directPeers.length > 0 && (
          <>
            <div className="list-section-header">Direct LAN Peers</div>
            {directPeers.map((peer) => {
              const isActive = peer.id === activeConversationId;
              return (
                <div
                  key={peer.id}
                  className={`conversation-item ${isActive ? 'active' : ''}`}
                  onClick={() => onSelectConversation(peer.id)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') onSelectConversation(peer.id); }}
                  aria-pressed={isActive}
                >
                  <div className="avatar-wrapper">
                    <div className="user-avatar">{peer.avatar}</div>
                    <span className={`status-badge ${peer.status}`} title={`Status: ${peer.status}`} />
                  </div>

                  <div className="item-content">
                    <div className="item-top">
                      <span className="item-name">{peer.name}</span>
                      <span className="item-time">{peer.lastActivity}</span>
                    </div>
                    <div className="item-bottom">
                      <span className="item-preview">{getLastMessagePreview(peer)}</span>
                      {peer.unreadCount > 0 ? (
                        <span className="unread-badge">{peer.unreadCount}</span>
                      ) : (
                        <span className="item-ip-badge">{peer.ipAddress}</span>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}
          </>
        )}

        {filteredConversations.length === 0 && (
          <div style={{ textAlign: 'center', padding: '32px 16px', color: 'var(--text-muted)', fontSize: '0.82rem' }}>
            No matching channels or LAN peers found.
          </div>
        )}
      </div>

      {/* Sidebar Footer with Current User Profile */}
      <div className="sidebar-footer">
        <div
          className="current-user-pill"
          onClick={onOpenProfile}
          title="Click to view profile & LAN keys"
          role="button"
          tabIndex={0}
        >
          <div className="avatar-wrapper">
            <div className="user-avatar" style={{ width: '32px', height: '32px', fontSize: '0.72rem' }}>
              {currentUser.avatar}
            </div>
            <span className="status-badge online" />
          </div>

          <div className="current-user-info">
            <span className="current-user-name">{currentUser.name}</span>
            <span className="current-user-ip">{currentUser.ipAddress}</span>
          </div>
        </div>

        <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '3px' }}>
          <Shield size={12} color="var(--accent-text)" /> Local
        </span>
      </div>
    </aside>
  );
}
