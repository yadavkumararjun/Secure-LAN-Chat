import React, { useState } from 'react';
import { ShieldCheck, Lock, User, Eye, EyeOff, ArrowRight, Wifi, Loader2 } from 'lucide-react';

export function AuthScreen({ onLogin, onRegister, authError = '', isSubmitting = false }) {
  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [username, setUsername] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [localError, setLocalError] = useState('');

  const displayError = localError || authError;

  const handleSubmit = (e) => {
    e.preventDefault();
    setLocalError('');

    const cleanUsername = username.trim().toLowerCase();

    if (!cleanUsername) {
      setLocalError('Username is required.');
      return;
    }
    if (cleanUsername.length < 3) {
      setLocalError('Username must be at least 3 characters.');
      return;
    }
    if (!/^[a-z0-9_]+$/.test(cleanUsername)) {
      setLocalError('Username may only contain letters, numbers, and underscores.');
      return;
    }
    if (!password) {
      setLocalError('Password is required.');
      return;
    }

    if (mode === 'register') {
      if (password.length < 6) {
        setLocalError('Password must be at least 6 characters.');
        return;
      }
      if (password !== confirmPassword) {
        setLocalError('Passwords do not match.');
        return;
      }
      onRegister({
        username: cleanUsername,
        password,
        displayName: displayName.trim() || undefined,
      });
    } else {
      onLogin({ username: cleanUsername, password });
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        <div className="auth-header">
          <div className="auth-logo">
            <ShieldCheck size={28} />
          </div>
          <h1 className="auth-title">Secure LAN Chat</h1>
          <p className="auth-sub">Local subnet authentication & encrypted communication</p>
        </div>

        <div className="auth-tabs" role="tablist">
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'login'}
            className={`auth-tab-btn ${mode === 'login' ? 'active' : ''}`}
            onClick={() => { setMode('login'); setLocalError(''); }}
            disabled={isSubmitting}
          >
            Sign In
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={mode === 'register'}
            className={`auth-tab-btn ${mode === 'register' ? 'active' : ''}`}
            onClick={() => { setMode('register'); setLocalError(''); }}
            disabled={isSubmitting}
          >
            Register Account
          </button>
        </div>

        {displayError && (
          <div
            style={{
              padding: '10px 12px',
              borderRadius: 'var(--radius-md)',
              backgroundColor: 'rgba(239, 68, 68, 0.12)',
              border: '1px solid rgba(239, 68, 68, 0.3)',
              color: 'var(--status-error)',
              fontSize: '0.82rem',
              marginBottom: '14px',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
            role="alert"
          >
            <span>{displayError}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div className="form-group">
            <label className="form-label" htmlFor="auth-username">LAN Username</label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <User size={16} style={{ position: 'absolute', left: '12px', color: 'var(--text-muted)' }} />
              <input
                id="auth-username"
                type="text"
                className="form-input"
                style={{ paddingLeft: '36px' }}
                placeholder="e.g. arjun_host"
                value={username}
                onChange={(e) => { setUsername(e.target.value); setLocalError(''); }}
                autoComplete="username"
                disabled={isSubmitting}
              />
            </div>
          </div>

          {mode === 'register' && (
            <div className="form-group">
              <label className="form-label" htmlFor="auth-display-name">Display Name (Optional)</label>
              <input
                id="auth-display-name"
                type="text"
                className="form-input"
                placeholder="e.g. Arjun (Host PC)"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                disabled={isSubmitting}
              />
            </div>
          )}

          <div className="form-group">
            <label className="form-label" htmlFor="auth-password">Password</label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Lock size={16} style={{ position: 'absolute', left: '12px', color: 'var(--text-muted)' }} />
              <input
                id="auth-password"
                type={showPassword ? 'text' : 'password'}
                className="form-input"
                style={{ paddingLeft: '36px', paddingRight: '36px' }}
                placeholder="••••••••"
                value={password}
                onChange={(e) => { setPassword(e.target.value); setLocalError(''); }}
                autoComplete={mode === 'login' ? 'current-password' : 'new-password'}
                disabled={isSubmitting}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                aria-label={showPassword ? 'Hide password' : 'Show password'}
                style={{ position: 'absolute', right: '10px', color: 'var(--text-muted)', display: 'flex' }}
                disabled={isSubmitting}
              >
                {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
              </button>
            </div>
            {mode === 'register' && (
              <span className="form-hint">At least 6 characters. Hashed with Argon2id.</span>
            )}
          </div>

          {mode === 'register' && (
            <div className="form-group">
              <label className="form-label" htmlFor="auth-confirm-password">Confirm Password</label>
              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <Lock size={16} style={{ position: 'absolute', left: '12px', color: 'var(--text-muted)' }} />
                <input
                  id="auth-confirm-password"
                  type={showPassword ? 'text' : 'password'}
                  className="form-input"
                  style={{ paddingLeft: '36px' }}
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => { setConfirmPassword(e.target.value); setLocalError(''); }}
                  autoComplete="new-password"
                  disabled={isSubmitting}
                />
              </div>
            </div>
          )}

          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '0.78rem' }}>
            <span style={{ color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: '4px' }}>
              <Wifi size={12} /> Local Subnet Authentication
            </span>
            <span style={{ color: 'var(--text-muted)' }}>HTTP-only Cookie</span>
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ height: '40px', marginTop: '4px' }}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <Loader2 size={16} className="animate-spin" />
                {mode === 'login' ? 'Signing In...' : 'Registering...'}
              </span>
            ) : (
              <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span>{mode === 'login' ? 'Sign In to LAN' : 'Create Local Account'}</span>
                <ArrowRight size={16} />
              </span>
            )}
          </button>
        </form>

        <div style={{ marginTop: '16px', paddingTop: '14px', borderTop: '1px solid var(--border-subtle)', textAlign: 'center', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
          {mode === 'login' ? (
            <span>New device on this network? Switch to <strong>Register Account</strong> to create your credentials.</span>
          ) : (
            <span>Already have an account? Switch to <strong>Sign In</strong>.</span>
          )}
        </div>
      </div>
    </div>
  );
}
