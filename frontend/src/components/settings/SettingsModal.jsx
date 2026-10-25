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
} from 'lucide-react';

/**
 * SettingsModal — Three-tab settings/profile dialog.
 * Cosmetic redesign only — all existing logic, data, and handlers unchanged.
 */
export function SettingsModal({
  isOpen,
  onClose,
  currentUser,
  onUpdateUser,
  onRequestLogout,
  onCopyIp,
}) {
  const [activeTab, setActiveTab] = useState('network');
  const [displayName, setDisplayName] = useState(currentUser.name);
  const [userStatus, setUserStatus] = useState(currentUser.status);
  const [soundEnabled, setSoundEnabled] = useState(true);
  const [copiedKey, setCopiedKey] = useState(false);

  if (!isOpen) return null;

  const handleSaveProfile = (e) => {
    e.preventDefault();
    onUpdateUser({ ...currentUser, name: displayName, status: userStatus });
  };

  const handleCopyKey = () => {
    setCopiedKey(true);
    navigator.clipboard?.writeText(currentUser.encryptionKeyFingerprint || 'SHA256:7f4a...9b12');
    setTimeout(() => setCopiedKey(false), 2000);
  };

  const tabs = [
    { id: 'network', icon: Wifi, label: 'Network' },
    { id: 'profile', icon: User, label: 'Profile' },
    { id: 'security', icon: Shield, label: 'Encryption' },
  ];

  return (
    <div
      className="modal-overlay"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="settings-title"
    >
      <div
        className="modal-card"
        style={{ maxWidth: '500px' }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <Settings size={18} color="var(--accent-text)" />
            <h3 id="settings-title" className="modal-title">Settings &amp; Profile</h3>
          </div>
          <button
            className="modal-close-btn"
            onClick={onClose}
            aria-label="Close settings"
          >
            <X size={17} />
          </button>
        </div>

        {/* Tab bar */}
        <div className="settings-tab-bar" role="tablist">
          {tabs.map(({ id, icon: Icon, label }) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={activeTab === id}
              className={`settings-tab ${activeTab === id ? 'active' : ''}`}
              onClick={() => setActiveTab(id)}
            >
              <Icon size={13} />
              {label}
            </button>
          ))}
        </div>

        {/* Body */}
        <div className="modal-body">
          {/* --- NETWORK TAB --- */}
          {activeTab === 'network' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {[
                { label: 'Host Local IP', value: currentUser.ipAddress, mono: true, action: onCopyIp },
                { label: 'WebSocket Endpoint', value: `ws://${currentUser.ipAddress}:8000/ws/chat`, mono: true },
                { label: 'HTTP API Port', value: '8000 (TCP)', mono: true },
                { label: 'Round-Trip Latency', value: '< 2 ms (Local Subnet)', color: 'var(--status-online)' },
              ].map(({ label, value, mono, action, color }) => (
                <div key={label} className="settings-row">
                  <span className="settings-row-label">{label}</span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span
                      className="settings-row-value"
                      style={{
                        fontFamily: mono ? 'var(--font-mono)' : 'inherit',
                        fontSize: mono ? '0.75rem' : '0.8rem',
                        color: color || (mono ? 'var(--accent-text)' : 'var(--text-primary)'),
                        fontWeight: color ? 700 : undefined,
                      }}
                    >
                      {value}
                    </span>
                    {action && (
                      <button
                        onClick={action}
                        style={{ color: 'var(--text-muted)', padding: 2, display: 'flex' }}
                        title="Copy"
                        aria-label="Copy IP address"
                      >
                        <Copy size={13} />
                      </button>
                    )}
                  </div>
                </div>
              ))}

              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', lineHeight: 1.55, marginTop: 4 }}>
                💡 <strong style={{ color: 'var(--text-secondary)' }}>LAN access:</strong> Peers on the same Wi-Fi can connect at{' '}
                <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--accent-text)', fontSize: '0.72rem' }}>
                  http://{currentUser.ipAddress}:8000
                </code>
              </div>
            </div>
          )}

          {/* --- PROFILE TAB --- */}
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
                  style={{ opacity: 0.5, cursor: 'not-allowed' }}
                />
                <span className="form-hint">Username cannot be changed after registration.</span>
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
                  <option value="online">Online</option>
                  <option value="away">Away</option>
                  <option value="offline">Appear Offline</option>
                </select>
              </div>

              <label style={{ display: 'flex', alignItems: 'center', gap: 9, cursor: 'pointer', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
                <input
                  type="checkbox"
                  checked={soundEnabled}
                  onChange={(e) => setSoundEnabled(e.target.checked)}
                  style={{ accentColor: 'var(--accent-primary)', width: 14, height: 14 }}
                />
                <Bell size={13} />
                Play notification sound on new message
              </label>

              <button type="submit" className="btn btn-primary" style={{ alignSelf: 'flex-start' }}>
                Save Changes
              </button>
            </form>
          )}

          {/* --- SECURITY TAB --- */}
          {activeTab === 'security' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
              <div className="settings-row" style={{ flexDirection: 'column', alignItems: 'flex-start', gap: 10 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: '0.8rem', fontWeight: 600, color: 'var(--accent-text)' }}>
                  <Key size={14} />
                  Public Key Fingerprint
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 8, width: '100%' }}>
                  <code style={{ fontFamily: 'var(--font-mono)', fontSize: '0.72rem', color: 'var(--text-secondary)', wordBreak: 'break-all' }}>
                    {currentUser.encryptionKeyFingerprint}
                  </code>
                  <button
                    onClick={handleCopyKey}
                    className="btn btn-secondary"
                    style={{ padding: '4px 8px', fontSize: '0.7rem', flexShrink: 0 }}
                  >
                    {copiedKey ? <Check size={11} color="var(--status-online)" /> : <Copy size={11} />}
                    {copiedKey ? 'Copied' : 'Copy'}
                  </button>
                </div>
              </div>

              <div style={{ fontSize: '0.78rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
                <strong>Encryption Architecture:</strong>
                <ul style={{ paddingLeft: 18, marginTop: 8, display: 'flex', flexDirection: 'column', gap: 5 }}>
                  <li>Argon2id password hashing with unique salts.</li>
                  <li>ECDH (P-256) ephemeral key exchange for DM peers.</li>
                  <li>AES-GCM 256-bit authenticated message encryption.</li>
                  <li>HTTP-only session cookies — no localStorage secrets.</li>
                </ul>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="modal-footer" style={{ justifyContent: 'space-between' }}>
          <button
            className="btn btn-danger"
            onClick={onRequestLogout}
          >
            <LogOut size={14} />
            Sign Out
          </button>
          <button className="btn btn-secondary" onClick={onClose}>
            Close
          </button>
        </div>
      </div>
    </div>
  );
}
