import React, { useState } from 'react';
import { ShieldCheck, Lock, User, Eye, EyeOff, ArrowRight, Wifi, Loader2 } from 'lucide-react';

/**
 * AuthScreen — Full-page dark authentication with login and registration.
 * All validation and submission logic unchanged. Visual redesign only.
 */
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

    if (!cleanUsername) { setLocalError('Username is required.'); return; }
    if (cleanUsername.length < 3) { setLocalError('Username must be at least 3 characters.'); return; }
    if (!/^[a-z0-9_]+$/.test(cleanUsername)) {
      setLocalError('Username may only contain letters, numbers, and underscores.');
      return;
    }
    if (!password) { setLocalError('Password is required.'); return; }

    if (mode === 'register') {
      if (password.length < 6) { setLocalError('Password must be at least 6 characters.'); return; }
      if (password !== confirmPassword) { setLocalError('Passwords do not match.'); return; }
      onRegister({ username: cleanUsername, password, displayName: displayName.trim() || undefined });
    } else {
      onLogin({ username: cleanUsername, password });
    }
  };

  return (
    <div className="auth-page">
      <div className="auth-card">
        {/* Header */}
        <div className="auth-header">
          <div className="auth-logo">
            <ShieldCheck size={30} />
          </div>
          <h1 className="auth-title">Secure LAN Chat</h1>
          <p className="auth-sub">Local network authentication · Zero cloud</p>
        </div>

        {/* Mode tabs */}
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
            Register
          </button>
        </div>

        {/* Error alert */}
        {displayError && (
          <div className="auth-error-box" role="alert">
            <span style={{ fontWeight: 600 }}>⚠</span>
            <span>{displayError}</span>
          </div>
        )}

        {/* Form */}
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {/* Username */}
          <div className="form-group">
            <label className="form-label" htmlFor="auth-username">Username</label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <User size={15} style={{ position: 'absolute', left: 12, color: 'var(--text-muted)', pointerEvents: 'none' }} />
              <input
                id="auth-username"
                type="text"
                className="form-input"
                style={{ paddingLeft: 36 }}
                placeholder="e.g. arjun_host"
                value={username}
                onChange={(e) => { setUsername(e.target.value); setLocalError(''); }}
                autoComplete="username"
                disabled={isSubmitting}
              />
            </div>
          </div>

          {/* Display Name (register only) */}
          {mode === 'register' && (
            <div className="form-group">
              <label className="form-label" htmlFor="auth-display-name">Display Name <span style={{ color: 'var(--text-muted)', fontWeight: 400 }}>(optional)</span></label>
              <input
                id="auth-display-name"
                type="text"
                className="form-input"
                placeholder="e.g. Arjun (Lab PC)"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                disabled={isSubmitting}
              />
            </div>
          )}

          {/* Password */}
          <div className="form-group">
            <label className="form-label" htmlFor="auth-password">Password</label>
            <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
              <Lock size={15} style={{ position: 'absolute', left: 12, color: 'var(--text-muted)', pointerEvents: 'none' }} />
              <input
                id="auth-password"
                type={showPassword ? 'text' : 'password'}
                className="form-input"
                style={{ paddingLeft: 36, paddingRight: 38 }}
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
                style={{ position: 'absolute', right: 10, color: 'var(--text-muted)', display: 'flex', padding: 2 }}
                disabled={isSubmitting}
              >
                {showPassword ? <EyeOff size={15} /> : <Eye size={15} />}
              </button>
            </div>
            {mode === 'register' && (
              <span className="form-hint">At least 6 characters · Hashed with Argon2id</span>
            )}
          </div>

          {/* Confirm Password (register only) */}
          {mode === 'register' && (
            <div className="form-group">
              <label className="form-label" htmlFor="auth-confirm-password">Confirm Password</label>
              <div style={{ position: 'relative', display: 'flex', alignItems: 'center' }}>
                <Lock size={15} style={{ position: 'absolute', left: 12, color: 'var(--text-muted)', pointerEvents: 'none' }} />
                <input
                  id="auth-confirm-password"
                  type={showPassword ? 'text' : 'password'}
                  className="form-input"
                  style={{ paddingLeft: 36 }}
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => { setConfirmPassword(e.target.value); setLocalError(''); }}
                  autoComplete="new-password"
                  disabled={isSubmitting}
                />
              </div>
            </div>
          )}

          {/* Network info row */}
          <div className="auth-network-row">
            <span style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
              <Wifi size={12} /> Local Subnet · HTTP-only Cookie
            </span>
            <span>Port 8000</span>
          </div>

          {/* Submit */}
          <button
            type="submit"
            className="btn btn-primary"
            style={{ height: 40, width: '100%', marginTop: 2 }}
            disabled={isSubmitting}
          >
            {isSubmitting ? (
              <>
                <Loader2 size={15} className="animate-spin" />
                {mode === 'login' ? 'Signing In...' : 'Registering...'}
              </>
            ) : (
              <>
                {mode === 'login' ? 'Sign In to LAN' : 'Create Account'}
                <ArrowRight size={15} />
              </>
            )}
          </button>
        </form>

        {/* Switch mode hint */}
        <div style={{ marginTop: 16, paddingTop: 14, borderTop: '1px solid var(--border-subtle)', textAlign: 'center', fontSize: '0.77rem', color: 'var(--text-muted)' }}>
          {mode === 'login' ? (
            <span>New to this network? Switch to <strong style={{ color: 'var(--text-secondary)' }}>Register</strong> above.</span>
          ) : (
            <span>Already have an account? Switch to <strong style={{ color: 'var(--text-secondary)' }}>Sign In</strong>.</span>
          )}
        </div>
      </div>
    </div>
  );
}
