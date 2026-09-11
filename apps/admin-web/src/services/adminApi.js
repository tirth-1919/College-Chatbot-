const API_BASE = '/api/v1/admin';

class AdminAPI {
  constructor() {
    this._token = null;
  }

  setToken(token) {
    this._token = token;
    if (token) localStorage.setItem('ait_admin_token', token);
    else localStorage.removeItem('ait_admin_token');
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

  async request(method, path, body) {
    const res = await fetch(`${API_BASE}${path}`, {
      method,
      headers: this.headers,
      ...(body !== undefined ? { body: JSON.stringify(body) } : {}),
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

  // --- Auth ---
  login(email, password, totp_code) { return this.post('/auth/login', { email, password, totp_code }); }
  verifyMfa(temp_token, totp_code) { return this.post('/auth/mfa-verify', { temp_token, totp_code }); }
  getProfile() { return this.get('/auth/me'); }
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
  getFeedback() { return this.get('/feedback'); }

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
}

export const adminApi = new AdminAPI();
