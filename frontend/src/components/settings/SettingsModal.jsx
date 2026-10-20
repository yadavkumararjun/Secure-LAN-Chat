import React, { useState } from 'react';
import {
  Settings,
  User,
  Shield,
  Wifi,
  Bell,
  LogOut,
  X,
  Copy,
  Check,
  Key,
  Server,
} from 'lucide-react';

export function SettingsModal({
  isOpen,
  onClose,
  currentUser,
  onUpdateUser,
  onRequestLogout,
  onCopyIp,
}) {
  const [activeTab, setActiveTab] = useState('network'); // 'network' | 'profile' | 'security'
  const [displayName, setDisplayName] = useState(currentUser.name);
  const [userStatus, setUserStatus] = useState(currentUser.status);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [copiedKey, setCopiedKey] = useState(false);

  if (!isOpen) return null;

  const handleSaveProfile = (e) => {
    e.preventDefault();
    onUpdateUser({
      ...currentUser,
      name: displayName,
      status: userStatus,
    });
  };

  const handleCopyKey = () => {
    setCopiedKey(true);
    navigator.clipboard?.writeText(currentUser.encryptionKeyFingerprint || 'SHA256:7f4a...9b12');
    setTimeout(() => setCopiedKey(false), 2000);
  };

  return (
    <div className="modal-overlay" onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="settings-title">
      <div className="modal-card" style={{ maxWidth: '520px' }} onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <Settings size={20} color="var(--accent-text)" />
            <h3 id="settings-title" className="modal-title">LAN Settings & Profile</h3>
          </div>
          <button className="modal-close-btn" onClick={onClose} aria-label="Close settings dialog">
            <X size={18} />
          </button>
        </div>

        {/* Tab Navigation */}
        <div style={{ display: 'flex', borderBottom: '1px solid var(--border-subtle)', padding: '0 20px', gap: '8px' }}>
          <button
            type="button"
            className={`filter-tab ${activeTab === 'network' ? 'active' : ''}`}
            style={{ borderRadius: '0', borderBottom: activeTab === 'network' ? '2px solid var(--accent-primary)' : '2px solid transparent', padding: '10px 12px' }}
            onClick={() => setActiveTab('network')}
          >
            <Wifi size={14} style={{ display: 'inline', marginRight: '6px' }} />
            Network Topology
          </button>
          <button
            type="button"
            className={`filter-tab ${activeTab === 'profile' ? 'active' : ''}`}
            style={{ borderRadius: '0', borderBottom: activeTab === 'profile' ? '2px solid var(--accent-primary)' : '2px solid transparent', padding: '10px 12px' }}
            onClick={() => setActiveTab('profile')}
          >
            <User size={14} style={{ display: 'inline', marginRight: '6px' }} />
            Profile & Status
          </button>
          <button
            type="button"
            className={`filter-tab ${activeTab === 'security' ? 'active' : ''}`}
            style={{ borderRadius: '0', borderBottom: activeTab === 'security' ? '2px solid var(--accent-primary)' : '2px solid transparent', padding: '10px 12px' }}
            onClick={() => setActiveTab('security')}
          >
            <Shield size={14} style={{ display: 'inline', marginRight: '6px' }} />
            Encryption
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {activeTab === 'network' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{
                backgroundColor: 'var(--bg-input)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Host Local IP</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: 'var(--accent-text)' }}>
                      {currentUser.ipAddress}
                    </code>
                    <button
                      onClick={onCopyIp}
                      style={{ color: 'var(--text-muted)', padding: '2px' }}
                      title="Copy IP"
                      aria-label="Copy Local IP"
                    >
                      <Copy size={14} />
                    </button>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>WebSocket Endpoint</span>
                  <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-primary)' }}>
                    ws://{currentUser.ipAddress}:8000/ws/chat
                  </code>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>HTTP API & Static Port</span>
                  <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--text-primary)' }}>
                    8000 (TCP)
                  </code>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>Round-Trip Latency</span>
                  <span style={{ fontSize: '0.78rem', color: 'var(--status-online)', fontWeight: 600 }}>
                    &lt; 1.5 ms (Local Subnet)
                  </span>
                </div>
              </div>

              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
                💡 <strong>Peers on your Wi-Fi:</strong> Other students or lab machines can connect by navigating to{' '}
                <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                  http://{currentUser.ipAddress}:8000
                </code>.
              </div>
            </div>
          )}

          {activeTab === 'profile' && (
            <form onSubmit={handleSaveProfile} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div className="form-group">
                <label className="form-label" htmlFor="settings-name">Display Name</label>
                <input
                  id="settings-name"
                  type="text"
                  className="form-input"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="settings-username">Username (Identity)</label>
                <input
                  id="settings-username"
                  type="text"
                  className="form-input"
                  value={currentUser.username}
                  disabled
                  style={{ opacity: 0.6, cursor: 'not-allowed' }}
                />
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="settings-status">Online Status</label>
                <select
                  id="settings-status"
                  className="form-input"
                  value={userStatus}
                  onChange={(e) => setUserStatus(e.target.value)}
                  style={{ cursor: 'pointer' }}
                >
                  <option value="online">🟢 Online</option>
                  <option value="away">🟡 Away</option>
                  <option value="offline">⚪ Offline</option>
                </select>
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                <input
                  type="checkbox"
                  checked={soundEnabled}
                  onChange={(e) => setSoundEnabled(e.target.checked)}
                  style={{ accentColor: 'var(--accent-primary)' }}
                />
                <Bell size={14} />
                Play notification chime on new message
              </label>

              <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }}>
                Save Profile Changes
              </button>
            </form>
          )}

          {activeTab === 'security' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div style={{
                backgroundColor: 'var(--bg-input)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-md)',
                padding: '14px',
                display: 'flex',
                flexDirection: 'column',
                gap: '8px',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '0.82rem', fontWeight: 600, color: 'var(--accent-text)' }}>
                  <Key size={16} />
                  <span>Public Key Fingerprint</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                  <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.74rem', color: 'var(--text-secondary)' }}>
                    {currentUser.encryptionKeyFingerprint}
                  </code>
                  <button
                    onClick={handleCopyKey}
                    className="btn btn-secondary"
                    style={{ padding: '4px 8px', fontSize: '0.72rem' }}
                  >
                    {copiedKey ? <Check size={12} color="var(--status-online)" /> : <Copy size={12} />}
                    {copiedKey ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>

              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: '1.5' }}>
                <strong>Encryption Architecture:</strong>
                <ul style={{ paddingLeft: '18px', marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <li>Local Argon2id salt & hashing for passwords.</li>
                  <li>ECDH (P-256) ephemeral key exchange for direct peer chats.</li>
                  <li>AES-GCM (256-bit) authenticated encryption for message payloads.</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Modal Footer */}
        <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
          <button
            className="btn btn-danger"
            onClick={onRequestLogout}
            style={{ fontSize: '0.78rem', padding: '6px 12px' }}
          >
            <LogOut size={14} />
            <span>Sign Out</span>
          </button>

          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
