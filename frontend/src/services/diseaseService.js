import { apiClient, ensureShape } from './apiClient';

const toList = (v) => (Array.isArray(v) ? v : v ? [String(v)] : []);

const normaliseDisease = (d) => ({
  code: d.disease_code ?? d.code,
  name: d.name ?? d.disease ?? d.disease_code,
  crop: d.crop ?? null,
  category: d.category ?? null,
  imageUrl: d.image_url ?? null,
  createdAt: d.created_at ?? null,
  symptomsSummary: d.symptoms_summary ?? d.symptoms_short ?? '',
  preventionSummary: d.prevention_summary ?? '',
  overview: d.overview ?? '',
  symptoms: toList(d.symptoms),
  favourableConditions: toList(d.favourable_conditions),
  preventive: toList(d.preventive_measures),
  cultural: toList(d.cultural_management),
  organic: toList(d.organic_management),
  chemical: toList(d.chemical_treatment),
  chemicalVerified: d.chemical_verified === true,
  consultExpert: toList(d.consult_expert),
  // Language the backend actually returned content in (used to show a fallback notice).
  contentLanguage: d.content_language ?? null,
});

export const diseaseService = {
  /** GET /diseases  -> { items: [...] } or [...]. Sends Accept-Language for localised content. */
  async list(lang, signal) {
    const { data } = await apiClient.get('/diseases', {
      signal,
      headers: lang ? { 'Accept-Language': lang } : {},
    });
    ensureShape(data, (d) => Array.isArray(d) || Array.isArray(d?.items), 'disease catalogue');
    return (Array.isArray(data) ? data : data.items).map(normaliseDisease);
  },

  /** GET /diseases/{disease_code} */
  async get(code, lang, signal) {
    const { data } = await apiClient.get(`/diseases/${encodeURIComponent(code)}`, {
      signal,
      headers: lang ? { 'Accept-Language': lang } : {},
    });
    ensureShape(data, (d) => d && typeof d === 'object' && (d.disease_code || d.code), 'disease');
    return normaliseDisease(data);
  },
};
