import { apiClient, ensureShape } from './apiClient';

const toList = (v) => (Array.isArray(v) ? v : v ? [String(v)] : []);

/**
 * Normalise the /predict response so the UI is tolerant of small schema differences.
 * Documented contract: see README ("POST /predict").
 */
export const normalisePrediction = (raw) => {
  const t = raw.treatment || {};
  return {
    analysisId: raw.analysis_id ?? raw.id ?? null,
    crop: raw.crop ?? null,
    diseaseCode: raw.disease_code ?? null,
    disease: raw.disease ?? raw.disease_name ?? raw.disease_code ?? null,
    confidence: typeof raw.confidence === 'number' ? raw.confidence : null,
    lowConfidence: raw.low_confidence === true,
    modelVersion: raw.model_version ?? null,
    createdAt: raw.created_at ?? null,
    imageUrl: raw.image_url ?? null,
    treatment: {
      summary: t.summary ?? '',
      preventive: toList(t.preventive_measures),
      organic: toList(t.organic_treatment),
      chemical: toList(t.chemical_treatment),
    },
  };
};

export const analysisService = {
  /** POST /predict (multipart/form-data, field "image") */
  async predict(file, { signal, lang } = {}) {
    const form = new FormData();
    form.append('image', file);
    const { data } = await apiClient.post('/predict', form, {
      signal,
      headers: { 'Content-Type': 'multipart/form-data', ...(lang ? { 'Accept-Language': lang } : {}) },
      timeout: 60000,
    });
    ensureShape(data, (d) => d && typeof d === 'object' && d.success !== false && d.disease_code, 'prediction');
    return normalisePrediction(data);
  },
};
