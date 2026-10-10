import { apiClient, ensureShape } from './apiClient';

const isUser = (u) => u && typeof u === 'object' && (u.email || u.id);

// Accepts either a bare user object or { user: {...} }.
const unwrapUser = (data) => ensureShape(data?.user ?? data, isUser, 'user profile');

export const authService = {
  /** GET /auth/me - verifies the current session with the backend. */
  async getCurrentUser(signal) {
    const { data } = await apiClient.get('/auth/me', { signal });
    return unwrapUser(data);
  },

  /** POST /auth/login - backend sets an HttpOnly session cookie. */
  async login({ email, password }) {
    const { data } = await apiClient.post('/auth/login', { email, password });
    return data;
  },

  /** POST /auth/register */
  async register({ name, email, password }) {
    const { data } = await apiClient.post('/auth/register', { name, email, password });
    return data;
  },

  /** POST /auth/logout - backend clears the session cookie. */
  async logout() {
    await apiClient.post('/auth/logout');
  },
};
