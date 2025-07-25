// API service for communicating with the Telephony CRM backend

const API_BASE_URL = 'https://nghki1cl0g5j.manus.space/api';

class ApiService {
  constructor() {
    this.token = localStorage.getItem('access_token');
  }

  setToken(token) {
    this.token = token;
    if (token) {
      localStorage.setItem('access_token', token);
    } else {
      localStorage.removeItem('access_token');
    }
  }

  getHeaders() {
    const headers = {
      'Content-Type': 'application/json',
    };

    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`;
    }

    return headers;
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
      headers: this.getHeaders(),
      ...options,
    };

    try {
      const response = await fetch(url, config);
      
      if (response.status === 401) {
        // Token expired or invalid
        this.setToken(null);
        window.location.href = '/login';
        throw new Error('Authentication required');
      }

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error?.message || `HTTP error! status: ${response.status}`);
      }

      return data;
    } catch (error) {
      console.error('API request failed:', error);
      throw error;
    }
  }

  // Authentication
  async login(credentials) {
    const response = await this.request('/auth/login', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });

    if (response.access_token) {
      this.setToken(response.access_token);
    }

    return response;
  }

  async logout() {
    try {
      await this.request('/auth/logout', { method: 'POST' });
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      this.setToken(null);
    }
  }

  async getCurrentUser() {
    return this.request('/auth/me');
  }

  // Users
  async getUsers(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/users${queryString ? `?${queryString}` : ''}`);
  }

  async createUser(userData) {
    return this.request('/users', {
      method: 'POST',
      body: JSON.stringify(userData),
    });
  }

  async updateUser(userId, userData) {
    return this.request(`/users/${userId}`, {
      method: 'PUT',
      body: JSON.stringify(userData),
    });
  }

  async deleteUser(userId) {
    return this.request(`/users/${userId}`, {
      method: 'DELETE',
    });
  }

  // Campaigns
  async getCampaigns(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/campaigns${queryString ? `?${queryString}` : ''}`);
  }

  async getCampaign(campaignId) {
    return this.request(`/campaigns/${campaignId}`);
  }

  async createCampaign(campaignData) {
    return this.request('/campaigns', {
      method: 'POST',
      body: JSON.stringify(campaignData),
    });
  }

  async updateCampaign(campaignId, campaignData) {
    return this.request(`/campaigns/${campaignId}`, {
      method: 'PUT',
      body: JSON.stringify(campaignData),
    });
  }

  async deleteCampaign(campaignId) {
    return this.request(`/campaigns/${campaignId}`, {
      method: 'DELETE',
    });
  }

  async assignUsersToCampaign(campaignId, userIds) {
    return this.request(`/campaigns/${campaignId}/assignments`, {
      method: 'POST',
      body: JSON.stringify({ user_ids: userIds }),
    });
  }

  // SIP Configuration
  async getSipConfigurations() {
    return this.request('/sip/configurations');
  }

  async createSipConfiguration(configData) {
    return this.request('/sip/configurations', {
      method: 'POST',
      body: JSON.stringify(configData),
    });
  }

  async updateSipConfiguration(configId, configData) {
    return this.request(`/sip/configurations/${configId}`, {
      method: 'PUT',
      body: JSON.stringify(configData),
    });
  }

  async testSipConfiguration(configId) {
    return this.request(`/sip/configurations/${configId}/test`, {
      method: 'POST',
    });
  }

  async activateSipConfiguration(configId) {
    return this.request(`/sip/configurations/${configId}/activate`, {
      method: 'POST',
    });
  }

  async getSipStatus() {
    return this.request('/sip/status');
  }

  // Leads
  async getLeads(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/leads${queryString ? `?${queryString}` : ''}`);
  }

  async getLead(leadId) {
    return this.request(`/leads/${leadId}`);
  }

  async createLead(leadData) {
    return this.request('/leads', {
      method: 'POST',
      body: JSON.stringify(leadData),
    });
  }

  async updateLead(leadId, leadData) {
    return this.request(`/leads/${leadId}`, {
      method: 'PUT',
      body: JSON.stringify(leadData),
    });
  }

  async deleteLead(leadId) {
    return this.request(`/leads/${leadId}`, {
      method: 'DELETE',
    });
  }

  async importLeads(campaignId, file, columnMapping = {}) {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('campaign_id', campaignId);
    formData.append('column_mapping', JSON.stringify(columnMapping));

    const response = await fetch(`${API_BASE_URL}/leads/import`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${this.token}`,
      },
      body: formData,
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || 'Import failed');
    }

    return response.json();
  }

  async getNextLead(campaignId) {
    return this.request(`/dialer/leads/next?campaign_id=${campaignId}`);
  }

  // Calls
  async getCalls(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/calls${queryString ? `?${queryString}` : ''}`);
  }

  async getCall(callId) {
    return this.request(`/calls/${callId}`);
  }

  async initiateCall(callData) {
    return this.request('/calls/initiate', {
      method: 'POST',
      body: JSON.stringify(callData),
    });
  }

  async hangupCall(callId) {
    return this.request(`/calls/${callId}/hangup`, {
      method: 'POST',
    });
  }

  async updateCallOutcome(callId, outcomeData) {
    return this.request(`/calls/${callId}/outcome`, {
      method: 'PUT',
      body: JSON.stringify(outcomeData),
    });
  }

  async getActiveCalls() {
    return this.request('/calls/active');
  }

  async getCallStats(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    return this.request(`/calls/stats${queryString ? `?${queryString}` : ''}`);
  }

  // Dialer
  async startCampaignDialer(campaignId) {
    return this.request(`/dialer/campaigns/${campaignId}/start`, {
      method: 'POST',
    });
  }

  async stopCampaignDialer(campaignId) {
    return this.request(`/dialer/campaigns/${campaignId}/stop`, {
      method: 'POST',
    });
  }

  async getDialerStatus(campaignId) {
    return this.request(`/dialer/campaigns/${campaignId}/status`);
  }

  async manualCall(callData) {
    return this.request('/dialer/manual-call', {
      method: 'POST',
      body: JSON.stringify(callData),
    });
  }

  async updateAgentStatus(status) {
    return this.request('/dialer/agent/status', {
      method: 'PUT',
      body: JSON.stringify({ status }),
    });
  }

  async getAgentStatus() {
    return this.request('/dialer/agent/status');
  }

  async getDialerStatistics(campaignId) {
    return this.request(`/dialer/campaigns/${campaignId}/statistics`);
  }

  // Health check
  async healthCheck() {
    return this.request('/health');
  }
}

export const apiService = new ApiService();
export default apiService;

