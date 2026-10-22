import { apiClient, ensureShape } from './apiClient';

const toList = (v) => (Array.isArray(v) ? v : v ? [String(v)] : []);

/**
 * Normalise the /predict response so the UI is tolerant of small schema differences.
 * Documented contract: see README ("POST /predict").
 */
export const normalisePrediction = (raw) => {
  const t = raw.treatment || {};
  const s = raw.severity || null;
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
    severity: s ? {
      status: s.status ?? 'unavailable',
      estimatedAffectedAreaPercent: typeof s.estimated_affected_area_percent === 'number' && Number.isFinite(s.estimated_affected_area_percent) ? s.estimated_affected_area_percent : null,
      category: s.category ?? null,
      method: s.method ?? null,
      message: s.message ?? null,
      affectedPixels: typeof s.affected_pixels === 'number' ? s.affected_pixels : null,
      totalLeafPixels: typeof s.total_leaf_pixels === 'number' ? s.total_leaf_pixels : null,
      confidenceLevel: s.confidence_level ?? null,
      disclaimer: s.disclaimer ?? null,
    } : null,
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
