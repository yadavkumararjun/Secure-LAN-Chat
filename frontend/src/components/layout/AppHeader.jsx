import React, { useState } from 'react';
import {
  ShieldCheck,
  Sun,
  Moon,
  Settings,
  User,
  Menu,
  ChevronDown,
  RefreshCw,
  Database,
  HardDrive,
  CheckCircle2,
  XCircle,
} from 'lucide-react';

export function AppHeader({
  theme,
  onToggleTheme,
  connectionStatus, // 'connected' | 'connecting' | 'disconnected'
  onChangeConnectionStatus,
  backendHealth,
  onRefreshHealth,
  onOpenSettings,
  onOpenProfile,
  onToggleMobileSidebar,
  currentUser,
}) {
  const [showStatusMenu, setShowStatusMenu] = useState(false);

  const getStatusText = () => {
    if (connectionStatus === 'connecting') return 'Probing Backend...';
    if (backendHealth?.status === 'healthy') return 'Backend Online (SQLite WAL)';
    if (connectionStatus === 'connected') return 'LAN Connected';
    return 'Backend Offline';
  };

  return (
    <header className="app-header">
      <div className="header-left">
        <button
          className="mobile-toggle-btn"
          onClick={onToggleMobileSidebar}
          aria-label="Toggle navigation menu"
        >
          <Menu size={20} />
        </button>

        <div className="brand-badge">
          <div className="brand-icon-wrap">
            <ShieldCheck size={18} />
          </div>
          <span className="brand-title">
            Secure LAN Chat
            <span className="brand-tag">v1.0 LAN</span>
          </span>
        </div>
      </div>

      <div className="header-center">
        {/* Connection status with dropdown for inspection and health refreshing */}
        <div style={{ position: 'relative' }}>
          <button
            className="connection-pill"
            onClick={() => setShowStatusMenu(!showStatusMenu)}
            aria-expanded={showStatusMenu}
            aria-label={`Connection status: ${getStatusText()}. Click for subsystem diagnostics.`}
          >
            <span className={`status-dot ${connectionStatus}`} />
            <span>{getStatusText()}</span>
            <span style={{ fontSize: '0.68rem', opacity: 0.6, fontFamily: 'var(--font-mono)' }}>
              :8000
            </span>
            <ChevronDown size={12} style={{ opacity: 0.7 }} />
          </button>

          {showStatusMenu && (
            <div
              style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                left: '50%',
                transform: 'translateX(-50%)',
                backgroundColor: 'var(--bg-card)',
                border: '1px solid var(--border-strong)',
                borderRadius: 'var(--radius-md)',
                boxShadow: 'var(--shadow-lg)',
                padding: '10px',
                width: '280px',
                zIndex: 60,
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontSize: '0.72rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Backend Subsystems
                </span>
                <button
                  onClick={() => { onRefreshHealth && onRefreshHealth(); }}
                  style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.7rem', color: 'var(--accent-text)', padding: '2px 4px', borderRadius: 'var(--radius-sm)' }}
                  title="Ping /api/health now"
                >
                  <RefreshCw size={11} /> Ping
                </button>
              </div>

              {backendHealth ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', fontSize: '0.76rem', color: 'var(--text-secondary)' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 6px', background: 'var(--bg-input)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <Database size={13} color="var(--accent-text)" /> SQLite WAL
                    </span>
                    <span style={{ color: 'var(--status-online)', fontWeight: 600 }}>
                      {backendHealth.database?.tables?.length || 5} tables
                    </span>
                  </div>

                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '4px 6px', background: 'var(--bg-input)', borderRadius: 'var(--radius-sm)' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: '5px' }}>
                      <HardDrive size={13} color="var(--accent-text)" /> Sandboxed Uploads
                    </span>
                    <span style={{ color: 'var(--status-online)', fontWeight: 600 }}>
                      {backendHealth.storage?.is_writable ? 'Writable' : 'Locked'}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: '4px' }}>
                    Server Version: {backendHealth.version} • Status: {backendHealth.status}
                  </div>
                </div>
              ) : (
                <div style={{ padding: '8px', fontSize: '0.76rem', color: 'var(--status-error)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <XCircle size={14} /> Backend endpoint unreachable on :8000
                </div>
              )}

              <div style={{ borderTop: '1px solid var(--border-subtle)', margin: '8px 0 6px' }} />

              <div style={{ fontSize: '0.68rem', fontWeight: 600, color: 'var(--text-muted)', marginBottom: '4px', textTransform: 'uppercase' }}>
                Simulate State (Demo)
              </div>
              <div style={{ display: 'flex', gap: '4px' }}>
                <button
                  className="btn btn-secondary"
                  style={{ flex: 1, padding: '3px 6px', fontSize: '0.7rem' }}
                  onClick={() => { onChangeConnectionStatus('connected'); setShowStatusMenu(false); }}
                >
                  🟢 Online
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ flex: 1, padding: '3px 6px', fontSize: '0.7rem' }}
                  onClick={() => { onChangeConnectionStatus('connecting'); setShowStatusMenu(false); }}
                >
                  🟡 Sync
                </button>
                <button
                  className="btn btn-secondary"
                  style={{ flex: 1, padding: '3px 6px', fontSize: '0.7rem' }}
                  onClick={() => { onChangeConnectionStatus('disconnected'); setShowStatusMenu(false); }}
                >
                  🔴 Offline
                </button>
              </div>
            </div>
          )}
        </div>
      </div>

      <div className="header-right">
        {/* Light/Dark Theme Toggle */}
        <button
          className="header-btn"
          onClick={onToggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        >
          {theme === 'dark' ? <Sun size={18} /> : <Moon size={18} />}
        </button>

        {/* Profile / Settings Button */}
        <button
          className="header-btn"
          onClick={onOpenSettings}
          aria-label="Open settings and network configuration"
          title="Network and Security Settings"
        >
          <Settings size={18} />
        </button>

        <button
          className="header-btn"
          onClick={onOpenProfile}
          aria-label="Open user profile"
          title="User Profile"
        >
          <User size={18} />
        </button>
      </div>
    </header>
  );
}
