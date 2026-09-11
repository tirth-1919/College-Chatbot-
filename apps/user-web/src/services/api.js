const API_BASE = '/api/v1';

export const apiClient = {
  getToken() {
    return localStorage.getItem('ait_auth_token');
  },

  setToken(token) {
    if (token) {
      localStorage.setItem('ait_auth_token', token);
    } else {
      localStorage.removeItem('ait_auth_token');
    }
  },

  getHeaders(isMultipart = false) {
    const headers = {};
    const token = this.getToken();
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }
    if (!isMultipart) {
      headers['Content-Type'] = 'application/json';
    }
    return headers;
  },

  // Auth
  async login(email, password) {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Login failed');
    }
    const data = await res.json();
    this.setToken(data.access_token);
    return data;
  },

  async signup(email, password, full_name) {
    const res = await fetch(`${API_BASE}/auth/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, full_name })
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Signup failed');
    }
    const data = await res.json();
    this.setToken(data.access_token);
    return data;
  },

  async getProfile() {
    const res = await fetch(`${API_BASE}/auth/me`, {
      headers: this.getHeaders()
    });
    if (!res.ok) return null;
    return await res.json();
  },

  async getOAuthStatus() {
    const res = await fetch(`${API_BASE}/auth/oauth/google/status`);
    return await res.json();
  },

  // Conversations
  async listConversations(search = '') {
    const query = search ? `?search=${encodeURIComponent(search)}` : '';
    const res = await fetch(`${API_BASE}/conversations${query}`, {
      headers: this.getHeaders()
    });
    if (!res.ok) return [];
    return await res.json();
  },

  async createConversation(title = 'New Conversation') {
    const res = await fetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ title })
    });
    return await res.json();
  },

  async getConversation(id) {
    const res = await fetch(`${API_BASE}/conversations/${id}`, {
      headers: this.getHeaders()
    });
    if (!res.ok) return null;
    return await res.json();
  },

  async updateConversation(id, updates) {
    const res = await fetch(`${API_BASE}/conversations/${id}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify(updates)
    });
    return await res.json();
  },

  async deleteConversation(id) {
    const res = await fetch(`${API_BASE}/conversations/${id}`, {
      method: 'DELETE',
      headers: this.getHeaders()
    });
    return await res.json();
  },

  // Suggestions
  async getSuggestions() {
    const res = await fetch(`${API_BASE}/chat/suggestions`);
    if (!res.ok) return [];
    return await res.json();
  },

  // Files
  async uploadFile(file) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch(`${API_BASE}/files/upload`, {
      method: 'POST',
      headers: this.getHeaders(true),
      body: formData
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'File upload failed');
    }
    return await res.json();
  },

  // Typed SSE Streaming
  async streamChat(conversationId, message, attachments, onEvent, signal) {
    const response = await fetch(`${API_BASE}/chat/stream`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({
        conversation_id: conversationId,
        message,
        attachments
      }),
      signal
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail || 'Streaming failed');
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder('utf-8');
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n\n');
      buffer = lines.pop(); // keep last incomplete chunk

      for (const block of lines) {
        if (!block.trim()) continue;
        const eventMatch = block.match(/^event:\s*(.+)$/m);
        const dataMatch = block.match(/^data:\s*(.+)$/m);

        if (eventMatch && dataMatch) {
          const eventType = eventMatch[1].trim();
          try {
            const data = JSON.parse(dataMatch[1].trim());
            onEvent(eventType, data);
          } catch (e) {
            console.error('Failed to parse SSE payload', e);
          }
        }
      }
    }
  }
};
