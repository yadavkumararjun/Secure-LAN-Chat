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
export function uploadFile({ file, conversationId, caption, onProgress }) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('file', file);
    formData.append('conversation_id', conversationId);
    if (caption && caption.trim()) {
      formData.append('caption', caption.trim());
    }

    xhr.open('POST', '/api/files/upload', true);
    xhr.withCredentials = true;

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
          }
        } catch {}
        reject(new Error(errMsg));
      }
    };

    xhr.onerror = () => {
      reject(new Error('Network error during file upload over LAN.'));
    };

    xhr.onabort = () => {
      reject(new Error('Upload canceled.'));
    };

    xhr.send(formData);
  });
}

/**
 * Download a shared file with authenticated credentials and trigger browser save dialog.
 */
export async function downloadFile(fileId, filename) {
  const response = await fetch(`/api/files/${encodeURIComponent(fileId)}/download`, {
    method: 'GET',
    credentials: 'include',
  });

  if (!response.ok) {
    let errorMsg = `Download failed with HTTP ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.error && errJson.error.message) {
        errorMsg = errJson.error.message;
      }
    } catch {}
    throw new Error(errorMsg);
  }

  const blob = await response.blob();
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename || `file-${fileId}`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  a.remove();
}

