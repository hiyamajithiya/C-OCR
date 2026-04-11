/**
 * API service for C-OCR backend communication.
 */

import axios, { AxiosInstance, AxiosError } from 'axios';

// In development, use empty baseURL to leverage Vite's proxy
// In production, use the configured API base URL
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

class ApiService {
  private api: AxiosInstance;

  constructor() {
    this.api = axios.create({
      baseURL: API_BASE_URL,
    });

    // Request interceptor to add auth token
    this.api.interceptors.request.use(
      (config) => {
        const token = localStorage.getItem('access_token');
        if (token) {
          config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
      },
      (error) => Promise.reject(error)
    );

    // Response interceptor for error handling
    this.api.interceptors.response.use(
      (response) => response,
      (error: AxiosError) => {
        if (error.response?.status === 401) {
          // Only redirect if we have a token (meaning we were logged in)
          const token = localStorage.getItem('access_token');
          if (token && !window.location.pathname.includes('/login')) {
            console.warn('Authentication expired, redirecting to login');
            // Clear token and redirect to login
            localStorage.removeItem('access_token');
            localStorage.removeItem('user');
            window.location.href = '/login';
          }
        }
        return Promise.reject(error);
      }
    );
  }

  // Authentication
  async login(email: string, password: string) {
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);

    const response = await this.api.post('/api/v1/auth/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  }

  // Documents
  async uploadDocument(file: File, docCategory?: string) {
    const formData = new FormData();
    formData.append('file', file);
    if (docCategory) {
      formData.append('doc_category', docCategory);
    }

    // Let axios automatically set Content-Type with boundary for FormData
    const response = await this.api.post('/api/v1/documents/', formData);
    return response.data;
  }

  async getDocument(documentId: number) {
    const response = await this.api.get(`/api/v1/documents/${documentId}`);
    return response.data;
  }

  async getDocumentResult(documentId: number) {
    const response = await this.api.get(`/api/v1/documents/${documentId}/result`);
    return response.data;
  }

  async downloadDocument(documentId: number, kind: string = 'searchable_pdf') {
    const response = await this.api.get(
      `/api/v1/documents/${documentId}/download?kind=${kind}`,
      { responseType: 'blob' }
    );
    return response.data;
  }

  // Get document page image as blob (for img src via object URL)
  async getDocumentPageImage(documentId: number, pageNum: number, dpi: number = 150): Promise<Blob> {
    const response = await this.api.get(
      `/api/v1/documents/${documentId}/pages/${pageNum}/image?dpi=${dpi}`,
      { responseType: 'blob' }
    );
    return response.data;
  }

  // Get OCR data with word coordinates for a page
  async getDocumentPageOCR(documentId: number, pageNum: number) {
    const response = await this.api.get(`/api/v1/documents/${documentId}/pages/${pageNum}/ocr`);
    return response.data;
  }

  // List all documents for current user
  async listDocuments() {
    const response = await this.api.get('/api/v1/documents/');
    return response.data;
  }

  // Delete a document
  async deleteDocument(documentId: number) {
    const response = await this.api.delete(`/api/v1/documents/${documentId}`);
    return response.data;
  }

  // Bulk delete documents
  async bulkDeleteDocuments(documentIds: number[]) {
    const response = await this.api.post('/api/v1/documents/bulk-delete', documentIds);
    return response.data;
  }

  // Templates
  async createTemplate(data: { name: string; description?: string; doc_category?: string }) {
    const response = await this.api.post('/api/v1/templates/', data);
    return response.data;
  }

  async listTemplates() {
    const response = await this.api.get('/api/v1/templates/');
    return response.data;
  }

  async deleteTemplate(templateId: number) {
    const response = await this.api.delete(`/api/v1/templates/${templateId}`);
    return response.data;
  }

  async getTemplateVersions(templateId: number) {
    const response = await this.api.get(`/api/v1/templates/${templateId}/versions`);
    return response.data;
  }

  async createTemplateVersion(
    templateId: number,
    data: {
      signature_json: any;
      fields_json: any;
      rules_json: any;
    }
  ) {
    const response = await this.api.post(`/api/v1/templates/${templateId}/versions`, data);
    return response.data;
  }

  async applyTemplate(templateId: number, documentId: number) {
    const response = await this.api.post(`/api/v1/templates/${templateId}/apply`, {
      document_id: documentId
    });
    return response.data;
  }

  async getDocumentExtractions(documentId: number) {
    const response = await this.api.get(`/api/v1/templates/extractions/document/${documentId}`);
    return response.data;
  }

  // Corrections
  async submitCorrection(data: {
    document_id: number;
    extraction_result_id?: number;
    field_name: string;
    field_label?: string;
    field_type?: string;
    original_value?: string;
    original_confidence?: number;
    extraction_method?: string;
    corrected_value: string;
    correction_note?: string;
  }) {
    const response = await this.api.post('/api/v1/corrections/submit', data);
    return response.data;
  }

  async submitBulkCorrections(data: {
    document_id: number;
    extraction_result_id?: number;
    corrections: Array<{
      document_id: number;
      field_name: string;
      original_value?: string;
      corrected_value: string;
    }>;
  }) {
    const response = await this.api.post('/api/v1/corrections/submit-bulk', data);
    return response.data;
  }

  async getDocumentCorrections(documentId: number) {
    const response = await this.api.get(`/api/v1/corrections/document/${documentId}`);
    return response.data;
  }

  async getTemplateAccuracyStats(templateId: number, days: number = 30) {
    const response = await this.api.get(`/api/v1/corrections/template/${templateId}/stats?days=${days}`);
    return response.data;
  }

  async listAbbreviations() {
    const response = await this.api.get('/api/v1/corrections/abbreviations');
    return response.data;
  }

  async createAbbreviation(data: {
    abbreviation: string;
    expanded_form: string;
    field_type?: string;
    doc_category?: string;
  }) {
    const response = await this.api.post('/api/v1/corrections/abbreviations', data);
    return response.data;
  }

  async deleteAbbreviation(abbreviationId: number) {
    const response = await this.api.delete(`/api/v1/corrections/abbreviations/${abbreviationId}`);
    return response.data;
  }

  async triggerLearningProcess() {
    const response = await this.api.post('/api/v1/corrections/process-learning');
    return response.data;
  }

  // API Keys
  async createAPIKey(data: {
    name: string;
    scopes: string[];
    rate_limit: number;
    daily_quota: number;
    restrict_to_templates?: boolean;
    template_ids?: number[];
    expires_at?: string;
  }) {
    const response = await this.api.post('/api/v1/api-keys/', data);
    return response.data;
  }

  async listAPIKeys() {
    const response = await this.api.get('/api/v1/api-keys/');
    return response.data;
  }

  async listAPIKeysWithStats() {
    const response = await this.api.get('/api/v1/api-keys/with-stats');
    return response.data;
  }

  async getAPIKeyStats(keyId: number, days: number = 30) {
    const response = await this.api.get(`/api/v1/api-keys/${keyId}/stats`, {
      params: { days }
    });
    return response.data;
  }

  async updateAPIKeyTemplates(keyId: number, templateIds: number[], restrict: boolean = true) {
    const response = await this.api.put(`/api/v1/api-keys/${keyId}/templates`, templateIds, {
      params: { restrict }
    });
    return response.data;
  }

  async revokeAPIKey(keyId: number) {
    const response = await this.api.delete(`/api/v1/api-keys/${keyId}`);
    return response.data;
  }

  // Users
  async createUser(data: {
    name: string;
    email: string;
    password: string;
    role: 'admin' | 'operator' | 'reviewer';
  }) {
    const response = await this.api.post('/api/v1/users/', data);
    return response.data;
  }

  async listUsers() {
    const response = await this.api.get('/api/v1/users/');
    return response.data;
  }

  async getCurrentUser() {
    const response = await this.api.get('/api/v1/users/me');
    return response.data;
  }

  async updateUser(userId: number, data: any) {
    const response = await this.api.patch(`/api/v1/users/${userId}`, data);
    return response.data;
  }

  // Audit Logs
  async listAuditLogs(params?: { action?: string; limit?: number; offset?: number }) {
    const response = await this.api.get('/api/v1/audit-logs/', { params });
    return response.data;
  }

  // ── Entities (Admin) ──────────────────────────────────────────────

  async createEntity(data: any) {
    const response = await this.api.post('/api/v1/entities/', data);
    return response.data;
  }

  async listEntities() {
    const response = await this.api.get('/api/v1/entities/');
    return response.data;
  }

  async getEntity(entityId: number) {
    const response = await this.api.get(`/api/v1/entities/${entityId}`);
    return response.data;
  }

  async updateEntity(entityId: number, data: any) {
    const response = await this.api.patch(`/api/v1/entities/${entityId}`, data);
    return response.data;
  }

  async suspendEntity(entityId: number) {
    const response = await this.api.post(`/api/v1/entities/${entityId}/suspend`);
    return response.data;
  }

  async getEntityUsage(entityId: number, days: number = 30) {
    const response = await this.api.get(`/api/v1/entities/${entityId}/usage`, { params: { days } });
    return response.data;
  }

  async createEntityUser(entityId: number, data: { name: string; email: string; password: string }) {
    const response = await this.api.post(`/api/v1/entities/${entityId}/users`, data);
    return response.data;
  }

  async getEntityInvoices(entityId: number) {
    const response = await this.api.get(`/api/v1/entities/${entityId}/invoices`);
    return response.data;
  }

  async generateInvoice(entityId: number, periodStart: string, periodEnd: string) {
    const response = await this.api.post(`/api/v1/entities/${entityId}/generate-invoice`, null, {
      params: { period_start: periodStart, period_end: periodEnd },
    });
    return response.data;
  }

  // ── Analytics (Admin) ─────────────────────────────────────────────

  async getAnalyticsOverview() {
    const response = await this.api.get('/api/v1/analytics/overview');
    return response.data;
  }

  async getAnalyticsUsage(period: string = 'daily', days: number = 30) {
    const response = await this.api.get('/api/v1/analytics/usage', { params: { period, days } });
    return response.data;
  }

  async getAnalyticsTopEntities(limit: number = 10) {
    const response = await this.api.get('/api/v1/analytics/top-entities', { params: { limit } });
    return response.data;
  }

  async getAnalyticsRevenue(period: string = 'monthly') {
    const response = await this.api.get('/api/v1/analytics/revenue', { params: { period } });
    return response.data;
  }

  async getAnalyticsEndpoints() {
    const response = await this.api.get('/api/v1/analytics/endpoints');
    return response.data;
  }

  async getAnalyticsErrors() {
    const response = await this.api.get('/api/v1/analytics/errors');
    return response.data;
  }

  // ── Portal (Entity Self-Service) ──────────────────────────────────

  async portalLogin(email: string, password: string) {
    const params = new URLSearchParams();
    params.append('username', email);
    params.append('password', password);
    const response = await this.api.post('/api/v1/portal/login', params, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    return response.data;
  }

  async getPortalDashboard() {
    const response = await this.api.get('/api/v1/portal/dashboard');
    return response.data;
  }

  async getPortalUsage() {
    const response = await this.api.get('/api/v1/portal/usage');
    return response.data;
  }

  async getPortalAPIKeys() {
    const response = await this.api.get('/api/v1/portal/api-keys');
    return response.data;
  }

  async createPortalAPIKey(data: { name: string; scopes: string[]; rate_limit: number; daily_quota: number }) {
    const response = await this.api.post('/api/v1/portal/api-keys', data);
    return response.data;
  }

  async revokePortalAPIKey(keyId: number) {
    const response = await this.api.delete(`/api/v1/portal/api-keys/${keyId}`);
    return response.data;
  }

  async getPortalDocuments() {
    const response = await this.api.get('/api/v1/portal/documents');
    return response.data;
  }

  async getPortalBilling() {
    const response = await this.api.get('/api/v1/portal/billing');
    return response.data;
  }

  async getPortalWebhooks() {
    const response = await this.api.get('/api/v1/portal/webhooks');
    return response.data;
  }

  async testPortalWebhook() {
    const response = await this.api.post('/api/v1/portal/webhooks/test');
    return response.data;
  }
}

export const apiService = new ApiService();
