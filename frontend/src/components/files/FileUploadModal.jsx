import React, { useState, useRef, useEffect } from 'react';
import { UploadCloud, File, X, AlertTriangle, Shield } from 'lucide-react';
import { uploadFile } from '../../services/api';

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
    if (initialFile) {
      validateAndSetFile(initialFile);
    }
  }, [initialFile]);

  if (!isOpen) return null;

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const validateAndSetFile = (file) => {
    setError('');
    // Client-side empty file check
    if (file.size === 0) {
      setError('Selected file is empty (0 bytes). Please choose a valid file.');
      setSelectedFile(null);
      return;
    }
    // Max 50 MB
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
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      validateAndSetFile(e.target.files[0]);
    }
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
      setError('No active conversation target selected to receive this file.');
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

      if (onUploadComplete) {
        onUploadComplete(result);
      }
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
    onClose();
  };

  return (
    <div className="modal-overlay" onClick={handleReset} role="dialog" aria-modal="true" aria-labelledby="upload-modal-title">
      <div className="modal-card" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div className="modal-title-group">
            <UploadCloud size={20} color="var(--accent-text)" />
            <h3 id="upload-modal-title" className="modal-title">Share File on LAN</h3>
          </div>
          <button className="modal-close-btn" onClick={handleReset} aria-label="Close file upload dialog" disabled={isUploading}>
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div className="modal-body" style={{ gap: '14px' }}>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
            Destination: <strong style={{ color: 'var(--text-primary)' }}>{activeTargetName}</strong>
          </div>

          {error && (
            <div style={{
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
              padding: '10px 14px',
              backgroundColor: 'rgba(239, 68, 68, 0.1)',
              border: '1px solid var(--status-offline)',
              borderRadius: 'var(--radius-md)',
              color: 'var(--status-offline)',
              fontSize: '0.82rem',
            }}>
              <AlertTriangle size={16} />
              <span>{error}</span>
            </div>
          )}

          {/* Drag & Drop Dropzone */}
          <div
            className={`file-dropzone ${dragActive ? 'dragover' : ''}`}
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            onClick={() => fileInputRef.current?.click()}
          >
            <input
              ref={fileInputRef}
              type="file"
              style={{ display: 'none' }}
              onChange={handleFileChange}
              disabled={isUploading}
            />

            <div className="dropzone-icon-box">
              <UploadCloud size={24} color="var(--accent-text)" />
            </div>

            <div className="dropzone-title">
              Drop file here, or <span className="dropzone-browse">browse</span>
            </div>
            <div className="dropzone-subtitle">
              Documents, images, archives • Max LAN transfer size: 50 MB
            </div>
          </div>

          {/* Selected File Card & Progress */}
          {selectedFile && (
            <div style={{
              display: 'flex',
              flexDirection: 'column',
              gap: '10px',
              backgroundColor: 'var(--bg-tertiary)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-md)',
              padding: '14px',
            }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0 }}>
                  <div className="file-icon-box" style={{ width: '34px', height: '34px' }}>
                    <File size={18} />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {selectedFile.name}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                      {formatFileSize(selectedFile.size)} • {selectedFile.type || 'Binary stream'}
                    </div>
                  </div>
                </div>

                {!isUploading && (
                  <button
                    onClick={() => setSelectedFile(null)}
                    style={{ color: 'var(--text-muted)', padding: '4px', background: 'none', border: 'none', cursor: 'pointer' }}
                    aria-label="Remove selected file"
                  >
                    <X size={16} />
                  </button>
                )}
              </div>

              {isUploading && (
                <div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '0.72rem', color: 'var(--text-secondary)', marginBottom: '4px' }}>
                    <span>Streaming over LAN socket buffer...</span>
                    <span style={{ fontWeight: 600 }}>{uploadProgress}%</span>
                  </div>
                  <div className="progress-container">
                    <div className="progress-bar" style={{ width: `${uploadProgress}%` }} />
                  </div>
                </div>
              )}
            </div>
          )}

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

          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.74rem', color: 'var(--text-muted)' }}>
            <Shield size={13} color="var(--accent-text)" />
            <span>LAN Direct Stream • End-to-end payload encryption scheduled for Phase 6</span>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <button className="btn btn-secondary" onClick={handleReset} disabled={isUploading}>
            Cancel
          </button>
          <button
            className="btn btn-primary"
            onClick={handleStartUpload}
            disabled={!selectedFile || isUploading}
          >
            {isUploading ? `Uploading (${uploadProgress}%)...` : 'Send File to LAN'}
          </button>
        </div>
      </div>
    </div>
  );
}
