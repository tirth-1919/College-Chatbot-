const API_BASE = '/api/v1';

export const apiClient = {
  _refreshPromise: null,

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

  setSession(data) {
    this.setToken(data.access_token);
    if (data.refresh_token) localStorage.setItem('ait_refresh_token', data.refresh_token);
  },

  clearSession() {
    this.setToken(null);
    localStorage.removeItem('ait_refresh_token');
  },

  async refreshAccessToken() {
    // Single-flight: concurrent 401s share ONE refresh operation.
    if (this._refreshPromise) return this._refreshPromise;
    const refreshToken = localStorage.getItem('ait_refresh_token');
    if (!refreshToken) throw new Error('No refresh token available');

    // In-flight guard: prevents overlapping refresh calls if awaited twice.
    if (this._refreshing) throw new Error('Refresh already in progress');
    this._refreshing = true;

    this._refreshPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken })
        });
        if (!response.ok) throw new Error('Session refresh failed');
        const data = await response.json();
        this.setToken(data.access_token);
        return data.access_token;
      } finally {
        this._refreshing = false;
        this._refreshPromise = null;
      }
    })();

    return this._refreshPromise;
  },

  async authFetch(url, options = {}, allowRefresh = true) {
    const { skipAuth, skipRefresh, ...fetchOptions } = options;
    const requestOptions = { ...fetchOptions, headers: new Headers(fetchOptions.headers || {}) };
    if (!skipAuth) {
      const token = this.getToken();
      if (token) requestOptions.headers.set('Authorization', `Bearer ${token}`);
    }
    const response = await fetch(url, requestOptions);
    if (response.status !== 401 || !allowRefresh || skipRefresh || url.includes('/auth/refresh') || url.includes('/auth/logout')) return response;

    try {
      // ONE refresh, then retry the original request exactly once.
      await this.refreshAccessToken();
      return await this.authFetch(url, options, false);
    } catch (error) {
      // Refresh failed: clear auth state and require manual login.
      this.clearSession();
      window.dispatchEvent(new CustomEvent('ait-auth-expired'));
      throw error;
    }
  },

  async logout() {
    const token = this.getToken();
    if (token) {
      await this.authFetch(`${API_BASE}/auth/logout`, {
        method: 'POST',
        headers: { Authorization: `Bearer ${token}` },
        skipRefresh: true
      }).catch(() => {});
    }
    this.clearSession();
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
    this.setSession(data);
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
    this.setSession(data);
    return data;
  },

  async getProfile() {
    const res = await this.authFetch(`${API_BASE}/auth/me`, {
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
  async listConversations(search = '', archived = false) {
    const params = new URLSearchParams();
    if (search) params.set('search', search);
    if (archived) params.set('archived', 'true');
    const query = params.toString() ? `?${params}` : '';
    const res = await this.authFetch(`${API_BASE}/conversations${query}`, {
      headers: this.getHeaders()
    });
    if (!res.ok) return [];
    return await res.json();
  },

  async createConversation(title = 'New Conversation') {
    const res = await this.authFetch(`${API_BASE}/conversations`, {
      method: 'POST',
      headers: this.getHeaders(),
      body: JSON.stringify({ title })
    });
    return await res.json();
  },

  async getConversation(id) {
    const res = await this.authFetch(`${API_BASE}/conversations/${id}`, {
      headers: this.getHeaders()
    });
    if (!res.ok) return null;
    return await res.json();
  },

  async updateConversation(id, updates) {
    const res = await this.authFetch(`${API_BASE}/conversations/${id}`, {
      method: 'PATCH',
      headers: this.getHeaders(),
      body: JSON.stringify(updates)
    });
    return await res.json();
  },

  async deleteConversation(id) {
    const res = await this.authFetch(`${API_BASE}/conversations/${id}`, {
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
    const res = await this.authFetch(`${API_BASE}/files/upload`, {
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
    const response = await this.authFetch(`${API_BASE}/chat/stream`, {
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
  },

  // College Public Registration
  async registerCollege(data) {
    const res = await fetch(`${API_BASE}/colleges/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data),
    });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try { detail = (await res.json()).detail || detail; } catch {}
      throw new Error(detail);
    }
    return res.json();
  },

  async getRegistrationStatus(applicationId) {
    const res = await fetch(`${API_BASE}/colleges/registration-status/${encodeURIComponent(applicationId)}`);
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try { detail = (await res.json()).detail || detail; } catch {}
      throw new Error(detail);
    }
    return res.json();
  }
};

