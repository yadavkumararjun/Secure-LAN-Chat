import React, { useState } from 'react';
import {
  ShieldCheck,
  Sun,
  Moon,
  Settings,
  Menu,
  ChevronDown,
  RefreshCw,
  Database,
  HardDrive,
  XCircle,
  Wifi,
} from 'lucide-react';

/**
 * AppHeader — Compact top bar with branding, real connection status,
 * health check dropdown, theme toggle, settings, and mobile toggle.
 */
export function AppHeader({
  theme,
  onToggleTheme,
  connectionStatus,
  onChangeConnectionStatus,
  backendHealth,
  onRefreshHealth,
  onOpenSettings,
  onToggleMobileSidebar,
  currentUser,
}) {
  const [showStatusMenu, setShowStatusMenu] = useState(false);

  const isHealthy = backendHealth?.status === 'healthy';

  const getStatusText = () => {
    if (connectionStatus === 'connected') return 'LAN Connected';
    if (connectionStatus === 'connecting') return 'Connecting...';
    if (isHealthy) return 'Backend Online';
    return 'Backend Offline';
  };

  const getStatusDotClass = () => {
    if (connectionStatus === 'connected' || isHealthy) return 'connected';
    if (connectionStatus === 'connecting') return 'connecting';
    return 'disconnected';
  };

  return (
    <header className="app-header">
      {/* Left: mobile toggle + brand */}
      <div className="header-left">
        <button
          className="mobile-toggle-btn"
          onClick={onToggleMobileSidebar}
          aria-label="Toggle navigation menu"
        >
          <Menu size={18} />
        </button>

        <div className="brand-badge">
          <div className="brand-icon-wrap">
            <ShieldCheck size={16} />
          </div>
          <span className="brand-title">
            Secure LAN Chat
            <span className="brand-tag">v1.0</span>
          </span>
        </div>
      </div>

      {/* Center: connection status with diagnostics dropdown */}
      <div className="header-center">
        <div style={{ position: 'relative' }}>
          <button
            className="connection-pill"
            onClick={() => setShowStatusMenu(!showStatusMenu)}
            aria-expanded={showStatusMenu}
            aria-haspopup="true"
            aria-label={`Connection status: ${getStatusText()}. Click for diagnostics.`}
          >
            <span className={`status-dot ${getStatusDotClass()}`} />
            <span>{getStatusText()}</span>
            <span style={{ fontFamily: 'var(--font-mono)', fontSize: '0.65rem', opacity: 0.55 }}>
              :8000
            </span>
            <ChevronDown size={11} style={{ opacity: 0.6 }} />
          </button>

          {showStatusMenu && (
            <>
              {/* Click-away backdrop */}
              <div
                style={{ position: 'fixed', inset: 0, zIndex: 55 }}
                onClick={() => setShowStatusMenu(false)}
                aria-hidden="true"
              />
              <div className="header-status-dropdown">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '10px' }}>
                  <span style={{ fontSize: '0.68rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                    Backend Subsystems
                  </span>
                  <button
                    onClick={() => { onRefreshHealth?.(); }}
                    style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '0.69rem', color: 'var(--accent-text)', padding: '2px 6px', borderRadius: 'var(--radius-sm)', background: 'var(--accent-subtle)', border: '1px solid var(--accent-border)' }}
                    title="Ping /api/health"
                  >
                    <RefreshCw size={10} /> Ping
                  </button>
                </div>

                {backendHealth ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 9px', background: 'var(--bg-input)', borderRadius: 'var(--radius-sm)', fontSize: '0.75rem' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)' }}>
                        <Database size={12} color="var(--accent-text)" /> SQLite WAL
                      </span>
                      <span style={{ color: 'var(--status-online)', fontWeight: 700, fontSize: '0.72rem' }}>
                        {backendHealth.database?.tables?.length || 5} tables
                      </span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 9px', background: 'var(--bg-input)', borderRadius: 'var(--radius-sm)', fontSize: '0.75rem' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)' }}>
                        <HardDrive size={12} color="var(--accent-text)" /> Uploads Storage
                      </span>
                      <span style={{ color: backendHealth.storage?.is_writable ? 'var(--status-online)' : 'var(--status-error)', fontWeight: 700, fontSize: '0.72rem' }}>
                        {backendHealth.storage?.is_writable ? 'Writable' : 'Locked'}
                      </span>
                    </div>

                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '6px 9px', background: 'var(--bg-input)', borderRadius: 'var(--radius-sm)', fontSize: '0.75rem' }}>
                      <span style={{ display: 'flex', alignItems: 'center', gap: '6px', color: 'var(--text-secondary)' }}>
                        <Wifi size={12} color="var(--accent-text)" /> WebSocket
                      </span>
                      <span style={{ color: connectionStatus === 'connected' ? 'var(--status-online)' : 'var(--status-error)', fontWeight: 700, fontSize: '0.72rem' }}>
                        {connectionStatus === 'connected' ? 'Open' : 'Closed'}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.66rem', color: 'var(--text-faint)', marginTop: '2px', padding: '0 2px' }}>
                      API v{backendHealth.version} · Status: {backendHealth.status}
                    </div>
                  </div>
                ) : (
                  <div style={{ padding: '8px', fontSize: '0.75rem', color: 'var(--status-error)', display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <XCircle size={13} /> Backend unreachable on :8000
                  </div>
                )}

                <div style={{ borderTop: '1px solid var(--border-subtle)', margin: '10px 0 6px' }} />

                <div style={{ fontSize: '0.66rem', fontWeight: 700, color: 'var(--text-faint)', marginBottom: '6px', textTransform: 'uppercase', letterSpacing: '0.07em' }}>
                  Simulate State
                </div>
                <div style={{ display: 'flex', gap: '4px' }}>
                  {[
                    { s: 'connected', label: 'Online', color: 'var(--status-online)' },
                    { s: 'connecting', label: 'Sync', color: 'var(--status-away)' },
                    { s: 'disconnected', label: 'Offline', color: 'var(--status-error)' },
                  ].map(({ s, label, color }) => (
                    <button
                      key={s}
                      className="btn btn-secondary"
                      style={{ flex: 1, padding: '4px 2px', fontSize: '0.68rem' }}
                      onClick={() => { onChangeConnectionStatus(s); setShowStatusMenu(false); }}
                    >
                      <span style={{ width: 6, height: 6, borderRadius: '50%', background: color, display: 'inline-block' }} />
                      {label}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </div>

      {/* Right: theme + settings */}
      <div className="header-right">
        <button
          className="header-btn"
          onClick={onToggleTheme}
          aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
          title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} theme`}
        >
          {theme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>

        <button
          className="header-btn"
          onClick={onOpenSettings}
          aria-label="Open settings"
          title="Settings"
        >
          <Settings size={17} />
        </button>
      </div>
    </header>
  );
}
