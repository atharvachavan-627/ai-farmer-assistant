import { apiClient } from './apiClient';

export const preferenceService = {
  /** GET /users/me/preferences  ->  { language: 'en' | 'hi' | 'mr', ... } */
  async get() {
    const { data } = await apiClient.get('/users/me/preferences');
    return data || {};
  },

  /** PUT /users/me/preferences */
  async update(prefs) {
    const { data } = await apiClient.put('/users/me/preferences', prefs);
    return data || {};
  },
};
