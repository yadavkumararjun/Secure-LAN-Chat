import React from 'react';
import { ShieldCheck, MessageSquare, UploadCloud, Users } from 'lucide-react';

export function EmptyChatState({ onSelectBroadcast, onOpenUpload }) {
  return (
    <div className="empty-chat-state">
      <div className="empty-icon-card">
        <ShieldCheck size={36} />
      </div>

      <h2 className="empty-title">Select a Conversation</h2>
      <p className="empty-description">
        Choose a broadcast channel or connect directly with an active peer on your local Wi-Fi subnet.
        Messages and file transfers never leave this local network.
      </p>

      <div className="empty-actions-row">
        <button
          className="quick-action-btn primary"
          onClick={onSelectBroadcast}
        >
          <MessageSquare size={16} />
          <span>Join #general-lan</span>
        </button>

        <button
          className="quick-action-btn"
          onClick={onOpenUpload}
        >
          <UploadCloud size={16} />
          <span>Share File on LAN</span>
        </button>
      </div>

      <div style={{ marginTop: '36px', display: 'flex', gap: '24px', fontSize: '0.74rem', color: 'var(--text-muted)' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
          <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'var(--status-online)' }} />
          Local Subnet 192.168.1.0/24
        </span>
        <span>•</span>
        <span>Zero Cloud Dependencies</span>
        <span>•</span>
        <span>Argon2id + AES-GCM</span>
      </div>
    </div>
  );
}
