/**
 * Credence API Client
 * Handles token storage, automatic token refreshing on 401, and unified HTTP requests.
 */

const API_BASE = '/api';

class ApiClient {
  constructor() {
    this.accessToken = localStorage.getItem('credence_access_token') || null;
    this.user = JSON.parse(localStorage.getItem('credence_user') || 'null');
    this.isRefreshing = false;
    this.refreshSubscribers = [];
  }

  setSession(token, user) {
    this.accessToken = token;
    this.user = user;
    if (token) {
      localStorage.setItem('credence_access_token', token);
    } else {
      localStorage.removeItem('credence_access_token');
    }
    if (user) {
      localStorage.setItem('credence_user', JSON.stringify(user));
    } else {
      localStorage.removeItem('credence_user');
    }
  }

  clearSession() {
    this.setSession(null, null);
  }

  isAuthenticated() {
    return !!this.accessToken && !!this.user;
  }

  subscribeTokenRefresh(cb) {
    this.refreshSubscribers.push(cb);
  }

  onRefreshed(token) {
    this.refreshSubscribers.map(cb => cb(token));
    this.refreshSubscribers = [];
  }

  async request(endpoint, options = {}) {
    const url = `${API_BASE}${endpoint}`;
    const headers = options.headers || {};

    if (this.accessToken && !headers['Authorization']) {
      headers['Authorization'] = `Bearer ${this.accessToken}`;
    }

    // Do not set Content-Type if sending FormData (browser sets boundary automatically)
    if (!(options.body instanceof FormData) && !headers['Content-Type']) {
      headers['Content-Type'] = 'application/json';
    }

    const config = {
      ...options,
      headers
    };

    try {
      let response = await fetch(url, config);

      // Handle 401 Unauthorized - Attempt Token Refresh
      if (response.status === 401 && !options._retry && !endpoint.includes('/auth/login') && !endpoint.includes('/auth/refresh')) {
        if (!this.isRefreshing) {
          this.isRefreshing = true;
          try {
            const refreshRes = await fetch(`${API_BASE}/auth/refresh`, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify({})
            });

            if (refreshRes.ok) {
              const data = await refreshRes.json();
              this.setSession(data.access_token, data.user);
              this.isRefreshing = false;
              this.onRefreshed(data.access_token);
              
              // Retry original request
              headers['Authorization'] = `Bearer ${data.access_token}`;
              return this.request(endpoint, { ...options, _retry: true, headers });
            } else {
              this.clearSession();
              this.isRefreshing = false;
              window.dispatchEvent(new CustomEvent('auth:session_expired'));
            }
          } catch (err) {
            this.clearSession();
            this.isRefreshing = false;
            window.dispatchEvent(new CustomEvent('auth:session_expired'));
          }
        } else {
          // Queue request until refresh finishes
          return new Promise(resolve => {
            this.subscribeTokenRefresh(newToken => {
              headers['Authorization'] = `Bearer ${newToken}`;
              resolve(this.request(endpoint, { ...options, _retry: true, headers }));
            });
          });
        }
      }

      const isJson = (response.headers.get('content-type') || '').includes('application/json');
      const data = isJson ? await response.json() : await response.text();

      if (!response.ok) {
        const errorMsg = (data && data.detail) ? data.detail : (typeof data === 'string' ? data : 'An error occurred.');
        const error = new Error(errorMsg);
        error.status = response.status;
        error.data = data;
        throw error;
      }

      return data;
    } catch (err) {
      throw err;
    }
  }

  // Convenience shortcuts
  get(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'GET' });
  }

  post(endpoint, body, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'POST',
      body: body instanceof FormData ? body : JSON.stringify(body)
    });
  }

  put(endpoint, body, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PUT',
      body: body instanceof FormData ? body : JSON.stringify(body)
    });
  }

  patch(endpoint, body, options = {}) {
    return this.request(endpoint, {
      ...options,
      method: 'PATCH',
      body: body instanceof FormData ? body : JSON.stringify(body)
    });
  }

  delete(endpoint, options = {}) {
    return this.request(endpoint, { ...options, method: 'DELETE' });
  }
}

const api = new ApiClient();
window.api = api;
