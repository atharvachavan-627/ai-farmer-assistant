import { apiClient, ensureShape } from './apiClient';

const normaliseRecord = (r) => ({
  analysisId: r.analysis_id ?? r.id,
  crop: r.crop ?? null,
  diseaseCode: r.disease_code ?? null,
  disease: r.disease ?? r.disease_name ?? r.disease_code ?? '',
  confidence: typeof r.confidence === 'number' ? r.confidence : null,
  createdAt: r.created_at ?? null,
  imageUrl: r.image_url ?? null,
});

export const historyService = {
  /**
   * GET /history
   * Query: page, page_size, search, crop, date_from, date_to, sort (newest|oldest)
   * Response: { items: [...], total, page, page_size, summary?: { by_disease: [{disease_code, disease, count}] } }
   * A bare array is also accepted.
   */
  async list(params = {}, signal) {
    const query = Object.fromEntries(Object.entries(params).filter(([, v]) => v !== '' && v != null));
    const { data } = await apiClient.get('/history', { params: query, signal });
    ensureShape(data, (d) => Array.isArray(d) || Array.isArray(d?.items), 'history');
    const items = (Array.isArray(data) ? data : data.items).map(normaliseRecord);
    return {
      items,
      total: Array.isArray(data) ? items.length : (data.total ?? items.length),
      page: data.page ?? params.page ?? 1,
      pageSize: data.page_size ?? params.page_size ?? items.length,
      byDisease: (data.summary?.by_disease ?? []).map((d) => ({
        diseaseCode: d.disease_code,
        disease: d.disease ?? d.disease_code,
        count: d.count,
      })),
    };
  },
};
