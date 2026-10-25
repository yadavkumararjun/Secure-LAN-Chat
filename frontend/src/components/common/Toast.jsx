import React from 'react';
import { CheckCircle2, Info, AlertTriangle, AlertCircle, X } from 'lucide-react';

export function Toast({ toast, onClose }) {
  const getIcon = () => {
    switch (toast.type) {
      case 'success': return <CheckCircle2 size={15} color="var(--status-online)" />;
      case 'warning': return <AlertTriangle size={15} color="var(--status-away)" />;
      case 'error':   return <AlertCircle size={15} color="var(--status-error)" />;
      default:        return <Info size={15} color="var(--accent-text)" />;
    }
  };

  return (
    <div className={`toast ${toast.type || 'info'}`} role="status" aria-live="polite">
      {getIcon()}
      <span style={{ flex: 1, fontSize: '0.8rem', lineHeight: 1.4 }}>{toast.message}</span>
      <button
        onClick={() => onClose(toast.id)}
        aria-label="Dismiss notification"
        style={{ color: 'var(--text-muted)', display: 'flex', padding: 2, flexShrink: 0 }}
      >
        <X size={13} />
      </button>
    </div>
  );
}

export function ToastContainer({ toasts, onClose }) {
  if (!toasts || toasts.length === 0) return null;

  return (
    <div className="toast-container" aria-label="Notifications">
      {toasts.map((toast) => (
        <Toast key={toast.id} toast={toast} onClose={onClose} />
      ))}
    </div>
  );
}
