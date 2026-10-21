import axios from 'axios';

const baseURL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');

/**
 * Normalised error thrown by every service call.
 * kind: 'network' | 'unauthorized' | 'validation' | 'server' | 'invalid_response' | 'client'
 */
export class ApiError extends Error {
  constructor(kind, message, { status, details } = {}) {
    super(message);
    this.name = 'ApiError';
    this.kind = kind;
    this.status = status;
    this.details = details;
  }
}

// Listeners are notified when an authenticated request returns 401 (expired session).
const unauthorizedListeners = new Set();
export const onUnauthorized = (fn) => {
  unauthorizedListeners.add(fn);
  return () => unauthorizedListeners.delete(fn);
};

export const apiClient = axios.create({
  baseURL,
  // Cookie-based session auth: browser sends the HttpOnly session cookie.
  // Backend must set CORS allow_credentials=True with an explicit origin.
  withCredentials: true,
  timeout: 30000,
  headers: { Accept: 'application/json' },
});

// Optional CSRF header support (double-submit cookie). Only applied if the cookie exists.
const CSRF_COOKIE = 'csrf_token';
const CSRF_HEADER = 'X-CSRF-Token';
const readCookie = (name) => {
  const match = document.cookie.split('; ').find((c) => c.startsWith(`${name}=`));
  return match ? decodeURIComponent(match.split('=')[1]) : null;
};

apiClient.interceptors.request.use((config) => {
  const method = (config.method || 'get').toLowerCase();
  if (!['get', 'head', 'options'].includes(method)) {
    const token = readCookie(CSRF_COOKIE);
    if (token) config.headers[CSRF_HEADER] = token;
  }
  return config;
});

const extractMessage = (data) => {
  if (!data) return null;
  if (typeof data.detail === 'string') return data.detail;
  if (Array.isArray(data.detail)) {
    return data.detail.map((d) => d.msg || JSON.stringify(d)).join('; ');
  }
  if (typeof data.message === 'string') return data.message;
  return null;
};

apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (axios.isCancel(error)) return Promise.reject(error);
    if (!error.response) {
      return Promise.reject(new ApiError('network', error.message, {}));
    }
    const { status, data } = error.response;
    const message = extractMessage(data);
    if (status === 401) {
      const isAuthCall = /\/auth\/(login|register)$/.test(error.config?.url || '');
      if (!isAuthCall) unauthorizedListeners.forEach((fn) => fn());
      return Promise.reject(new ApiError('unauthorized', message, { status, details: data }));
    }
    if (status === 400 || status === 409 || status === 422) {
      return Promise.reject(new ApiError('validation', message, { status, details: data }));
    }
    if (status >= 500) {
      return Promise.reject(new ApiError('server', message, { status, details: data }));
    }
    return Promise.reject(new ApiError('client', message, { status, details: data }));
  },
);

/** Helper to assert that a response body is a plain object / array as expected. */
export const ensureShape = (data, check, what = 'response') => {
  if (!check(data)) {
    throw new ApiError('invalid_response', `Unexpected ${what} from server`);
  }
  return data;
};

/** Resolve a backend-relative media URL (e.g. /media/abc.jpg) to an absolute URL. */
export const resolveMediaUrl = (url) => {
  if (!url) return null;
  if (/^https?:\/\//i.test(url) || url.startsWith('blob:') || url.startsWith('data:')) return url;
  if (import.meta.env.VITE_UI_PREVIEW === 'true' && url.startsWith('/')) {
    return url;
  }
  return `${baseURL}${url.startsWith('/') ? '' : '/'}${url}`;
};

export const API_BASE_URL = baseURL;
