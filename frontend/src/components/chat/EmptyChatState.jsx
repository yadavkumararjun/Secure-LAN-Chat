import React from 'react';
import { ShieldCheck, MessageSquare, UploadCloud } from 'lucide-react';

/**
 * EmptyChatState — Shown when no conversation is selected.
 * Provides quick actions to join #general-lan or share a file.
 */
export function EmptyChatState({ onSelectBroadcast, onOpenUpload }) {
  return (
    <div className="empty-chat-state">
      <div className="empty-icon-card">
        <ShieldCheck size={34} />
      </div>

      <h2 className="empty-title">Select a Conversation</h2>
      <p className="empty-description">
        Choose a broadcast channel or connect directly with an active peer on your local network.
        All messages and file transfers stay on this subnet — zero cloud, zero internet.
      </p>

      <div className="empty-actions-row">
        <button
          className="quick-action-btn primary"
          onClick={onSelectBroadcast}
          aria-label="Join the general LAN broadcast channel"
        >
          <MessageSquare size={15} />
          Join #general-lan
        </button>

        <button
          className="quick-action-btn"
          onClick={onOpenUpload}
          aria-label="Share a file over the LAN"
        >
          <UploadCloud size={15} />
          Share File on LAN
        </button>
      </div>

      <div className="empty-network-badges">
        <span className="dot" aria-hidden="true" />
        <span>192.168.x.x Subnet</span>
        <span>·</span>
        <span>Zero Cloud</span>
        <span>·</span>
        <span>Argon2id + SQLite WAL</span>
      </div>
    </div>
  );
}
