// API client for Secure LAN Chat Backend

/**
 * Common fetch helper ensuring credentials (HTTP-only cookies) are sent.
 */
async function apiRequest(endpoint, options = {}) {
  const config = {
    ...options,
    credentials: 'include', // Ensure session cookies are sent with requests
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {}),
    },
  };

  const response = await fetch(endpoint, config);

  if (!response.ok) {
    let errorDetail = `HTTP ${response.status}: ${response.statusText}`;
    try {
      const errJson = await response.json();
      if (errJson?.error?.message) {
        errorDetail = errJson.error.message;
      } else if (errJson?.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore json parse error
    }
    const error = new Error(errorDetail);
    error.status = response.status;
    throw error;
  }

  return await response.json();
}

export async function fetchHealth() {
  return await apiRequest('/api/health', { method: 'GET' });
}

export async function registerUser({ username, password, displayName }) {
  return await apiRequest('/api/auth/register', {
    method: 'POST',
    body: JSON.stringify({
      username,
      password,
      display_name: displayName || undefined,
    }),
  });
}

export async function loginUser({ username, password }) {
  return await apiRequest('/api/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  });
}

export async function logoutUser() {
  return await apiRequest('/api/auth/logout', { method: 'POST' });
}

export async function fetchCurrentUser() {
  return await apiRequest('/api/auth/me', { method: 'GET' });
}

export async function fetchUsers(searchQuery = '') {
  const url = searchQuery ? `/api/users?q=${encodeURIComponent(searchQuery)}` : '/api/users';
  return await apiRequest(url, { method: 'GET' });
}

export async function fetchConversations() {
  return await apiRequest('/api/conversations', { method: 'GET' });
}

export async function openDirectConversation(recipientId) {
  return await apiRequest('/api/conversations/direct', {
    method: 'POST',
    body: JSON.stringify({ recipient_id: recipientId }),
  });
}

export async function fetchConversationMessages(conversationId, { limit = 50, offset = 0 } = {}) {
  const url = `/api/conversations/${encodeURIComponent(conversationId)}/messages?limit=${limit}&offset=${offset}`;
  return await apiRequest(url, { method: 'GET' });
}

export async function sendMessageRest(conversationId, { content, clientMsgId, messageType = 'text' }) {
  return await apiRequest(`/api/conversations/${encodeURIComponent(conversationId)}/messages`, {
    method: 'POST',
    body: JSON.stringify({
      content,
      client_msg_id: clientMsgId || undefined,
      message_type: messageType,
    }),
  });
}

/**
 * Upload a file with streaming progress monitoring over local LAN.
 * Uses XMLHttpRequest for reliable progress events.
 */
export async function uploadFile({ file, conversationId, caption, onProgress }) {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('conversation_id', conversationId);
  if (caption && caption.trim()) {
    formData.append('caption', caption.trim());
  }

  // 1. Try streaming upload via XMLHttpRequest (provides accurate progress percentages)
  try {
    return await new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', '/api/files/upload', true);
      xhr.withCredentials = true;
      xhr.timeout = 120000; // 2 minute timeout for large LAN file transfers

      if (xhr.upload && onProgress) {
        xhr.upload.onprogress = (event) => {
          if (event.lengthComputable) {
            const percentComplete = Math.round((event.loaded / event.total) * 100);
            onProgress(percentComplete);
          }
        };
      }

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            resolve(data);
          } catch {
            resolve({ message: 'Upload succeeded' });
          }
        } else {
          let errMsg = `Upload failed (HTTP ${xhr.status})`;
          try {
            const errJson = JSON.parse(xhr.responseText);
            if (errJson.error && errJson.error.message) {
              errMsg = errJson.error.message;
            } else if (errJson.message) {
              errMsg = errJson.message;
            } else if (errJson.detail) {
              errMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
            }
          } catch {}
          reject(new Error(errMsg));
        }
      };

      xhr.ontimeout = () => {
        reject(new Error('Upload timed out. The local network connection may be slow or interrupted.'));
      };

      xhr.onerror = () => {
        const netErr = new Error('XHR_NETWORK_ERROR');
        netErr.isNetworkError = true;
        reject(netErr);
      };

      xhr.onabort = () => {
        reject(new Error('Upload canceled.'));
      };

      xhr.send(formData);
    });
  } catch (err) {
    if (err.message === 'XHR_NETWORK_ERROR') {
      // 2. Resilient fallback to fetch API if XHR was blocked or reset
      console.warn('[Upload] XHR failed, retrying via standard fetch API...');
      try {
        const response = await fetch('/api/files/upload', {
          method: 'POST',
          credentials: 'include',
          body: formData,
        });

        if (!response.ok) {
          let errMsg = `Upload failed (HTTP ${response.status})`;
          try {
            const errJson = await response.json();
            if (errJson.error && errJson.error.message) {
              errMsg = errJson.error.message;
            } else if (errJson.message) {
              errMsg = errJson.message;
            } else if (errJson.detail) {
              errMsg = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
            }
          } catch {}
          throw new Error(errMsg);
        }

        onProgress?.(100);
        return await response.json();
      } catch (fetchErr) {
        throw new Error(
          fetchErr.message && fetchErr.message !== 'Failed to fetch'
            ? fetchErr.message
            : 'Network error during file upload over LAN. Please verify the backend server is running on port 8000.'
        );
      }
    }
    throw err;
  }
}

/**
 * Download a shared file with authenticated credentials and trigger browser save dialog.
 * Uses native download anchor for fast, unbuffered direct streaming to user's Downloads folder.
 */
export async function downloadFile(fileId, filename) {
  const downloadUrl = `/api/files/${encodeURIComponent(fileId)}/download`;
  const cleanFilename = (filename || `file-${fileId}`).replace(/[/\\?%*:|"<>]/g, '_');

  const a = document.createElement('a');
  a.style.display = 'none';
  a.href = downloadUrl;
  a.download = cleanFilename;
  document.body.appendChild(a);
  a.click();

  setTimeout(() => {
    a.remove();
  }, 1000);
}

