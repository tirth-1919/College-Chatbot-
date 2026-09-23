const API_BASE = '/api/v1/admin';

class AdminAPI {
  constructor() {
    this._token = null;
    this._refreshPromise = null;
  }

  setToken(token) {
    this._token = token;
    if (token) localStorage.setItem('ait_admin_token', token);
    else localStorage.removeItem('ait_admin_token');
  }

  setSession(data) {
    this.setToken(data.access_token);
    if (data.refresh_token) localStorage.setItem('ait_admin_refresh_token', data.refresh_token);
  }

  clearSession() {
    this.setToken(null);
    localStorage.removeItem('ait_admin_refresh_token');
  }

  loadToken() {
    this._token = localStorage.getItem('ait_admin_token');
    return this._token;
  }

  get headers() {
    return {
      'Content-Type': 'application/json',
      ...(this._token ? { Authorization: `Bearer ${this._token}` } : {}),
    };
  }

  async refreshAccessToken() {
    // Single-flight: concurrent 401s share ONE refresh operation.
    if (this._refreshPromise) return this._refreshPromise;
    const refreshToken = localStorage.getItem('ait_admin_refresh_token');
    if (!refreshToken) throw new Error('No admin refresh token available');

    // In-flight guard: prevents overlapping refresh calls.
    if (this._refreshing) throw new Error('Refresh already in progress');
    this._refreshing = true;

    this._refreshPromise = (async () => {
      try {
        const response = await fetch(`${API_BASE}/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: refreshToken })
        });
        if (!response.ok) throw new Error('Admin session refresh failed');
        const data = await response.json();
        this.setToken(data.access_token);
        return data.access_token;
      } finally {
        this._refreshing = false;
        this._refreshPromise = null;
      }
    })();

    return this._refreshPromise;
  }

  async authFetch(url, options = {}, allowRefresh = true) {
    const { skipAuth, skipRefresh, ...fetchOptions } = options;
    const requestOptions = { ...fetchOptions, headers: new Headers(fetchOptions.headers || {}) };
    if (!skipAuth) {
      const token = this._token || localStorage.getItem('ait_admin_token');
      if (token) requestOptions.headers.set('Authorization', `Bearer ${token}`);
    }
    const response = await fetch(url, requestOptions);
    if (response.status !== 401 || !allowRefresh || skipRefresh || url.includes('/auth/refresh') || url.includes('/auth/logout')) return response;

    try {
      // ONE refresh, then retry the original request exactly once.
      await this.refreshAccessToken();
      return await this.authFetch(url, options, false);
    } catch (error) {
      this.clearSession();
      window.dispatchEvent(new CustomEvent('ait-admin-auth-expired'));
      throw error;
    }
  }

  async request(method, path, body) {
    const res = await this.authFetch(`${API_BASE}${path}`, {
      method,
      headers: this.headers,
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
      ...(path === '/auth/logout' ? { skipRefresh: true } : {})
    });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try { detail = (await res.json()).detail || detail; } catch {}
      throw new Error(detail);
    }
    return res.json();
  }

  get(path) { return this.request('GET', path); }
  post(path, body) { return this.request('POST', path, body); }
  put(path, body) { return this.request('PUT', path, body); }
  delete(path) { return this.request('DELETE', path); }
  patch(path, body) { return this.request('PATCH', path, body); }

  // --- Auth ---
  login(email, password, totp_code) { return this.post('/auth/login', { email, password, totp_code }); }
  verifyMfa(temp_token, totp_code) { return this.post('/auth/mfa-verify', { temp_token, totp_code }); }
  getProfile() { return this.get('/auth/me'); }
  logout() { return this.post('/auth/logout'); }
  refresh() { return this.request('POST', '/auth/refresh', { refresh_token: localStorage.getItem('ait_admin_refresh_token') }); }
  getSessions() { return this.get('/auth/sessions'); }
  revokeSession(id) { return this.post(`/auth/sessions/${id}/revoke`); }
  setupMfa() { return this.post('/auth/mfa/setup'); }

  // --- Dashboard ---
  getMetrics() { return this.get('/dashboard/metrics'); }

  // --- Knowledge ---
  getEntities(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this.get(`/knowledge${q ? '?' + q : ''}`);
  }
  getEntity(id) { return this.get(`/knowledge/${id}`); }
  createEntity(data) { return this.post('/knowledge', data); }
  updateEntity(id, data) { return this.put(`/knowledge/${id}`, data); }
  rollbackEntity(id, data) { return this.post(`/knowledge/${id}/rollback`, data); }
   deleteEntity(id) { return this.delete(`/knowledge/${id}`); }

  // --- Knowledge Database (Categories & Records) ---
  getKnowledgeCategories(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this.get(`/knowledge-db/categories${q ? '?' + q : ''}`);
  }
  createKnowledgeCategory(data) { return this.post('/knowledge-db/categories', data); }
  getKnowledgeCategory(id) { return this.get(`/knowledge-db/categories/${id}`); }
  updateKnowledgeCategory(id, data) { return this.request('PATCH', `/knowledge-db/categories/${id}`, data); }
  deleteKnowledgeCategory(id) { return this.delete(`/knowledge-db/categories/${id}`); }
  getKnowledgeRecords(categoryId, params = {}) {
    const q = new URLSearchParams(params).toString();
    return this.get(`/knowledge-db/categories/${categoryId}/records${q ? '?' + q : ''}`);
  }
  createKnowledgeRecord(categoryId, data) { return this.post(`/knowledge-db/categories/${categoryId}/records`, data); }
  getKnowledgeRecord(id) { return this.get(`/knowledge-db/records/${id}`); }
  updateKnowledgeRecord(id, data) { return this.request('PATCH', `/knowledge-db/records/${id}`, data); }
  deleteKnowledgeRecord(id) { return this.delete(`/knowledge-db/records/${id}`); }
  duplicateKnowledgeRecord(id) { return this.post(`/knowledge-db/records/${id}/duplicate`); }
  verifyKnowledgeRecord(id) { return this.post(`/knowledge-db/records/${id}/verify`); }
  enableKnowledgeRecord(id) { return this.post(`/knowledge-db/records/${id}/enable`); }
  disableKnowledgeRecord(id) { return this.post(`/knowledge-db/records/${id}/disable`); }
  exportKnowledgeRecords(categoryId) { return this.get(`/knowledge-db/export${categoryId ? `?category_id=${categoryId}` : ''}`); }

  // --- Website ---
  getSnapshots() { return this.get('/website/snapshots'); }
  syncWebsite() { return this.post('/website/sync'); }

  // --- Documents ---
  getDocuments() { return this.get('/documents'); }
  getDocumentChunks(id) { return this.get(`/documents/${id}/chunks`); }
  deleteDocument(id) { return this.delete(`/documents/${id}`); }
  async uploadDocument(file) {
    const fd = new FormData();
    fd.append('file', file);
    const res = await fetch(`${API_BASE}/documents/upload`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${this._token}` },
      body: fd,
    });
    if (!res.ok) throw new Error((await res.json()).detail || 'Upload failed');
    return res.json();
  }

  // --- Images ---
  getImages(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this.get(`/images${q ? '?' + q : ''}`);
  }
  syncImages() { return this.post('/images/sync'); }
  toggleImageVerification(id) { return this.post(`/images/${id}/verify`); }
  deleteImage(id) { return this.delete(`/images/${id}`); }

  // --- Conflicts ---
  getConflicts(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this.get(`/conflicts${q ? '?' + q : ''}`);
  }
  scanConflicts() { return this.post('/conflicts/scan'); }
  resolveConflict(id, data) { return this.post(`/conflicts/${id}/resolve`, data); }

  // --- AI Control ---
  getAiProviders() { return this.get('/ai/providers'); }
  toggleModel(id, is_enabled) { return this.post(`/ai/models/${id}/toggle`, { is_enabled }); }
  setModelPriority(id, priority) { return this.post(`/ai/models/${id}/priority`, { priority }); }
  resetCircuitBreaker(id) { return this.post(`/ai/models/${id}/circuit-breaker/reset`); }
  getQuotas() { return this.get('/ai/quotas'); }
  getUsageLogs() { return this.get('/ai/usage'); }
  getRuntimeStatus() { return this.get('/ai/runtime-status'); }
  getFailoverEvents(limit = 25) { return this.get(`/ai/failover-events?limit=${limit}`); }
  // Multi-credential management (live, no restart)
  getCredentials(provider) { return this.get(`/ai/credentials${provider ? `?provider=${provider}` : ''}`); }
  addCredential(data) { return this.post('/ai/credentials', data); }
  updateCredential(id, data) { return this.request('PATCH', `/ai/credentials/${id}`, data); }
  deleteCredential(id) { return this.delete(`/ai/credentials/${id}`); }
  testCredential(id) { return this.post(`/ai/credentials/${id}/test`); }
  recheckCredential(id) { return this.post(`/ai/credentials/${id}/recheck`); }
  rotateCredential(id) { return this.post(`/ai/credentials/${id}/rotate`); }

  // --- Users ---
  getUsers(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this.get(`/users${q ? '?' + q : ''}`);
  }
  changeUserRole(id, role) { return this.post(`/users/${id}/role`, { role }); }
  toggleUserStatus(id, is_active) { return this.post(`/users/${id}/status`, { is_active }); }

  // --- Gaps & Feedback ---
  getKnowledgeGaps(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this.get(`/knowledge-gaps${q ? '?' + q : ''}`);
  }
  resolveGap(id) { return this.post(`/knowledge-gaps/${id}/resolve`); }
  dismissGap(id) { return this.post(`/knowledge-gaps/${id}/dismiss`); }
  updateGap(id, data) { return this.patch(`/knowledge-gaps/${id}`, data); }
  createGapDraft(id, data) { return this.post(`/knowledge-gaps/${id}/create-draft`, data); }
  getFeedback(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this.get(`/feedback${q ? '?' + q : ''}`);
  }
  resolveFeedback(id) { return this.post(`/feedback/${id}/resolve`); }
  getGap(id) { return this.get(`/knowledge-gaps/${id}`); }

  // --- Security ---
  getAuditLogs() { return this.get('/security/audit-logs'); }
  getSecurityEvents() { return this.get('/security/security-events'); }

  // --- Settings ---
  getPrompts() { return this.get('/settings/prompts'); }
  addPromptVersion(slug, data) { return this.post(`/settings/prompts/${slug}/version`, data); }
  getFeatureFlags() { return this.get('/settings/feature-flags'); }
  toggleFlag(key, is_enabled) { return this.post(`/settings/feature-flags/${key}/toggle`, { is_enabled }); }
  createBackup() { return this.post('/settings/backup'); }
  getBackups() { return this.get('/settings/backups'); }

  // --- Automation ---
  getAutomationJobs() { return this.get('/automation/jobs'); }
  triggerJob(job_type, priority = 5, payload = {}) { return this.post('/automation/jobs/trigger', { job_type, priority, payload }); }
  getDeadLetters() { return this.get('/automation/dead-letter'); }
  retryDeadLetter(job_id) { return this.post(`/automation/dead-letter/${job_id}/retry`); }
  cancelDeadLetter(job_id) { return this.delete(`/automation/dead-letter/${job_id}`); }
  getWorkerStatus() { return this.get('/automation/worker-status'); }

  // --- Alerts ---
  getAlerts(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this.get(`/alerts${q ? '?' + q : ''}`);
  }
  acknowledgeAlert(id) { return this.post(`/alerts/${id}/acknowledge`); }
  resolveAlert(id, notes = '') { return this.post(`/alerts/${id}/resolve`, { notes }); }

  // --- Evaluation & Rollback ---
  getEvaluations() { return this.get('/evaluation/results'); }
  runEvaluation() { return this.post('/evaluation/run'); }
  rollbackKnowledge(entity_id, target_version) { return this.post('/evaluation/rollback/knowledge', { entity_id, target_version }); }
  rollbackPrompt(prompt_slug, target_version) { return this.post('/evaluation/rollback/prompt', { prompt_slug, target_version }); }
  rollbackFlag(flag_key) { return this.post('/evaluation/rollback/feature-flag', { flag_key }); }

  // --- Maintenance & Disaster Recovery ---
  getMaintenanceMode() { return this.get('/maintenance/mode'); }
  setMaintenanceMode(mode, message) { return this.post('/maintenance/mode', { mode, message }); }
  verifyRestore() { return this.post('/maintenance/restore/verify'); }

  // --- Colleges & Approval Center ---
  async registerCollege(data) {
    const res = await fetch('/api/v1/colleges/register', {
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
  }

  async getRegistrationStatus(applicationId) {
    const res = await fetch(`/api/v1/colleges/registration-status/${encodeURIComponent(applicationId)}`);
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try { detail = (await res.json()).detail || detail; } catch {}
      throw new Error(detail);
    }
    return res.json();
  }

  getColleges(params = {}) {
    const q = new URLSearchParams(params).toString();
    return this.get(`/colleges/${q ? '?' + q : ''}`);
  }
  getCollegeStats() { return this.get('/colleges/stats/summary'); }
  // --- College Details (SUPER_ADMIN master directory) ---
  getCollegeStatsFor(id) { return this.get(`/colleges/${id}/stats`); }
  getCollegeUsers(id) { return this.get(`/colleges/${id}/users`); }
  getCollegeKnowledge(id) { return this.get(`/colleges/${id}/knowledge`); }
  getCollegeDocuments(id) { return this.get(`/colleges/${id}/documents`); }
  getCollegeWebsite(id) { return this.get(`/colleges/${id}/website`); }
  getCollegeRag(id) { return this.get(`/colleges/${id}/rag`); }
  getCollegeChangeRequests(id) { return this.get(`/colleges/${id}/change-requests`); }
  getCollegeFeedback(id) { return this.get(`/colleges/${id}/feedback`); }
  getCollegeGaps(id) { return this.get(`/colleges/${id}/gaps`); }
  getCollegeAnalytics(id) { return this.get(`/colleges/${id}/analytics`); }
  getCollegeAudit(id) { return this.get(`/colleges/${id}/audit`); }
  async listColleges(params = {}) {
    const res = await this.getColleges({ ...params, per_page: 200 });
    // API returns { total, colleges: [...] } - unwrap to array
    if (Array.isArray(res)) return res;
    if (res && Array.isArray(res.colleges)) return res.colleges;
    return [];
  }
  getPendingColleges() { return this.get('/colleges/pending'); }
  getCollege(id) { return this.get(`/colleges/${id}`); }
  getCurrentCollege() { return this.get('/colleges/current'); }
  createCollege(data) { return this.post('/colleges', data); }
  updateCollege(id, data) { return this.patch(`/colleges/${id}`, data); }
  approveCollege(id) { return this.post(`/colleges/${id}/approve`); }
  rejectCollege(id, reason) { return this.post(`/colleges/${id}/reject`, { reason }); }
  requestCollegeInfo(id, notes) { return this.post(`/colleges/${id}/request-info`, { notes }); }
  requestInfoCollege(id, notes) { return this.requestCollegeInfo(id, notes); }
  sendCollegeCredentials(id) { return this.post(`/colleges/${id}/send-credentials`); }
  sendCredentialsCollege(id) { return this.sendCollegeCredentials(id); }
  suspendCollege(id) { return this.post(`/colleges/${id}/suspend`); }
  activateCollege(id) { return this.post(`/colleges/${id}/activate`); }

  // --- First Login Password Change ---
  changeFirstPassword(email, temporary_password, new_password) {
    return this.post('/auth/change-first-password', { email, temporary_password, new_password });
  }

  // --- Smart Upload ---
  async smartUpload(formData) {
    const res = await this.authFetch(`${API_BASE}/smart-upload/upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) {
      let detail = `HTTP ${res.status}`;
      try { detail = (await res.json()).detail || detail; } catch {}
      throw new Error(detail);
    }
    return res.json();
  }
    getStagedUploads() { return this.get('/smart-upload/staged'); }
    approveStagedUpload(id) { return this.post(`/smart-upload/staged/${id}/approve`); }
    rejectStagedUpload(id) { return this.post(`/smart-upload/staged/${id}/reject`); }

    // --- Change Requests (tenant-scoped approval workflow) ---
    async listChangeRequests(status) {
      const data = await this.get(`/change-requests/${status ? `?status_filter=${encodeURIComponent(status)}` : ''}`);
      return data?.items ?? data ?? [];  // unwrap paginated envelope
    }
    createChangeRequest(data) { return this.post('/change-requests/', data); }
    approveChangeRequest(id, notes) { return this.post(`/change-requests/${id}/approve`, { notes }); }
    rejectChangeRequest(id, notes) { return this.post(`/change-requests/${id}/reject`, { notes }); }
  }
  export const adminApi = new AdminAPI();
