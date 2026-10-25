import React, { useState, useRef, useEffect } from 'react';
import { UploadCloud, FileText, X, AlertTriangle, Shield } from 'lucide-react';
import { uploadFile } from '../../services/api';

/**
 * FileUploadModal — Drag-and-drop file upload dialog.
 * All upload/download logic unchanged. Visual redesign only.
 */
export function FileUploadModal({
  isOpen,
  onClose,
  onUploadComplete,
  conversationId,
  activeTargetName = 'Conversation',
  initialFile = null,
}) {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [caption, setCaption] = useState('');
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [error, setError] = useState('');
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (isOpen && initialFile) {
      validateAndSetFile(initialFile);
    }
  }, [isOpen, initialFile]);

  if (!isOpen) return null;

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const validateAndSetFile = (file) => {
    setError('');
    if (file.size === 0) {
      setError('Selected file is empty (0 bytes). Please choose a valid file.');
      setSelectedFile(null);
      return;
    }
    if (file.size > 50 * 1024 * 1024) {
      setError(`File size (${(file.size / (1024 * 1024)).toFixed(1)} MB) exceeds the 50 MB LAN transfer limit.`);
      setSelectedFile(null);
      return;
    }
    setSelectedFile(file);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.[0]) validateAndSetFile(e.dataTransfer.files[0]);
  };

  const handleFileChange = (e) => {
    if (e.target.files?.[0]) validateAndSetFile(e.target.files[0]);
    e.target.value = '';
  };

  const formatFileSize = (bytes) => {
    if (!bytes) return '0 B';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleStartUpload = async () => {
    if (!selectedFile) return;
    if (!conversationId) {
      setError('No active conversation target selected.');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);
    setError('');

    try {
      const result = await uploadFile({
        file: selectedFile,
        conversationId,
        caption: caption.trim() || undefined,
        onProgress: (pct) => setUploadProgress(pct),
      });

      onUploadComplete?.(result);
      handleReset();
    } catch (err) {
      setIsUploading(false);
      setError(err.message || 'File upload failed. Please try again.');
    }
  };

  const handleReset = () => {
    setSelectedFile(null);
    setCaption('');
    setError('');
    setIsUploading(false);
    setUploadProgress(0);
    if (fileInputRef.current) fileInputRef.current.value = '';
    onClose();
  };

  return (
    <div
      className="modal-overlay"
      onClick={handleReset}
      role="dialog"
      aria-modal="true"
      aria-labelledby="upload-modal-title"
    >
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <UploadCloud size={19} color="var(--accent-text)" />
            <h3 id="upload-modal-title" className="modal-title">Share File on LAN</h3>
          </div>
          <button
            className="modal-close-btn"
            onClick={handleReset}
            aria-label="Close file upload dialog"
            disabled={isUploading}
          >
            <X size={17} />
          </button>
        </div>

        {/* Body */}
        <div className="modal-body" style={{ gap: '14px' }}>
          {/* Destination */}
          <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            To: <strong style={{ color: 'var(--text-primary)' }}>{activeTargetName}</strong>
          </div>

          {/* Error */}
          {error && (
            <div className="upload-error-box">
              <AlertTriangle size={15} />
              <span>{error}</span>
            </div>
          )}

          {/* Dropzone */}
          <div
            className={`file-dropzone ${dragActive ? 'dragover' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
            role="button"
            tabIndex={0}
            onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') fileInputRef.current?.click(); }}
            aria-label="Drop a file here or click to browse"
          >
            <input
              ref={fileInputRef}
              type="file"
              style={{ display: 'none' }}
              onChange={handleFileChange}
              disabled={isUploading}
              aria-hidden="true"
            />
            <div className="dropzone-icon-box">
              <UploadCloud size={22} />
            </div>
            <div className="dropzone-title">
              Drop file here, or <span className="dropzone-browse">browse</span>
            </div>
            <div className="dropzone-subtitle">
              Documents, images, archives · Max 50 MB
            </div>
          </div>

          {/* Selected file */}
          {selectedFile && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-muted)',
              borderRadius: 'var(--radius-md)',
              padding: '12px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                  <div className="file-icon-box" style={{ width: 34, height: 34, flexShrink: 0 }}>
                    <FileText size={16} />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '0.83rem', fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {selectedFile.name}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>
                      {formatFileSize(selectedFile.size)} · {selectedFile.type || 'Binary'}
                    </div>
                  </div>
                </div>
                {!isUploading && (
                  <button
                    onClick={() => setSelectedFile(null)}
                    style={{ color: 'var(--text-muted)', padding: 4, flexShrink: 0 }}
                    aria-label="Remove selected file"
                  >
                    <X size={15} />
                  </button>
                )}
              </div>

              {/* Upload progress */}
              {isUploading && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: 6 }}>
                    <span>Streaming over LAN...</span>
                    <span style={{ fontWeight: 700, color: 'var(--accent-text)' }}>{uploadProgress}%</span>
                  </div>
                  <div className="progress-container">
                    <div className="progress-bar" style={{ width: `${uploadProgress}%` }} />
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Caption input */}
          <div className="form-group">
            <label className="form-label" htmlFor="file-caption">Optional Caption</label>
            <input
              id="file-caption"
              type="text"
              className="form-input"
              placeholder="Add a message or description..."
              value={caption}
              onChange={(e) => setCaption(e.target.value)}
              disabled={isUploading}
            />
          </div>

          {/* Security note */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            <Shield size={12} color="var(--accent-text)" />
            <span>LAN direct stream · SHA-256 hash verification on delivery</span>
          </div>
        </div>

        {/* Footer */}
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={handleReset} disabled={isUploading}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleStartUpload}
            disabled={!selectedFile || isUploading}
          >
            {isUploading ? `Uploading ${uploadProgress}%...` : 'Send File'}
          </button>
        </div>
      </div>
    </div>
  );
}
