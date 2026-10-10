/**
 * UI PREVIEW MODE - development only.
 *
 * Lets you click through the interface without a backend. It replaces the HTTP transport of the
 * shared axios client with an in-browser stub. Everything it returns is sample data, NOT real
 * model output. It is only loaded by `npm run dev:preview` (see main.jsx) and is never part of
 * a production build.
 */
import { AxiosError } from 'axios';
import { apiClient } from '../services/apiClient';

const SESSION_KEY = 'afa.preview.session';
const HISTORY_KEY = 'afa.preview.history';
const USERS_KEY = 'afa.preview.users';

const read = (key, fallback) => {
  try {
    const v = sessionStorage.getItem(key);
    return v ? JSON.parse(v) : fallback;
  } catch {
    return fallback;
  }
};
const write = (key, value) => {
  try {
    if (value == null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* ignore */
  }
};
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

// ---- Sample disease content (generic; deliberately contains NO chemical products or doses) ----
const DISEASES = [
  {
    disease_code: 'Tomato___Early_blight',
    name: 'Tomato Early Blight',
    crop: 'tomato',
    category: 'Fungal',
    created_at: '2026-09-20T09:00:00Z',
    symptoms_summary: 'Dark spots with concentric rings on older leaves, often with a yellow halo.',
    prevention_summary: 'Rotate crops, remove infected leaves and avoid wetting foliage.',
    overview: 'A fungal leaf disease that usually starts on the lower, older leaves and can spread upward.',
    symptoms: ['Brown to black spots with target-like rings', 'Yellowing around the spots', 'Leaves dry and drop in severe cases'],
    favourable_conditions: ['Warm, humid weather', 'Leaf wetness from overhead watering or dew'],
    preventive_measures: ['Rotate with non-solanaceous crops', 'Remove and dispose of infected plant debris', 'Space plants for good airflow'],
    cultural_management: ['Water at the base of plants', 'Mulch to reduce soil splash'],
    organic_management: ['Remove affected lower leaves early'],
    chemical_treatment: [],
    chemical_verified: false,
    consult_expert: ['The disease keeps spreading despite removing leaves', 'Fruit or stems are affected'],
    content_language: 'en',
  },
  {
    disease_code: 'Tomato___Late_blight',
    name: 'Tomato Late Blight',
    crop: 'tomato',
    category: 'Oomycete',
    created_at: '2026-09-22T09:00:00Z',
    symptoms_summary: 'Water-soaked grey-green patches that turn brown; white growth under leaves in humid weather.',
    prevention_summary: 'Use healthy planting material, keep foliage dry and remove infected plants quickly.',
    overview: 'A fast-spreading disease favoured by cool, wet conditions that can damage leaves, stems and fruit.',
    symptoms: ['Large water-soaked lesions on leaves', 'Dark patches on stems', 'Firm brown rot on fruit'],
    favourable_conditions: ['Cool nights with high humidity', 'Prolonged rain or leaf wetness'],
    preventive_measures: ['Plant healthy seedlings', 'Avoid overcrowding', 'Destroy infected plants promptly'],
    cultural_management: ['Improve drainage', 'Avoid overhead irrigation'],
    organic_management: [],
    chemical_treatment: [],
    chemical_verified: false,
    consult_expert: ['Symptoms appear suddenly across many plants'],
    content_language: 'en',
  },
  {
    disease_code: 'Potato___Early_blight',
    name: 'Potato Early Blight',
    crop: 'potato',
    category: 'Fungal',
    created_at: '2026-09-25T09:00:00Z',
    symptoms_summary: 'Dark, ring-patterned spots on older leaves that enlarge and merge.',
    prevention_summary: 'Rotate crops, use healthy seed tubers and keep plants well nourished.',
    overview: 'A common fungal disease of potato foliage that is worse on stressed or poorly fed plants.',
    symptoms: ['Concentric brown spots on lower leaves', 'Leaf yellowing and early drying'],
    favourable_conditions: ['Alternating wet and dry periods', 'Nutrient-stressed plants'],
    preventive_measures: ['Use certified seed tubers', 'Rotate crops', 'Remove volunteer potato plants'],
    cultural_management: ['Maintain balanced fertilisation', 'Avoid water stress'],
    organic_management: [],
    chemical_treatment: [],
    chemical_verified: false,
    consult_expert: ['More than a few leaves are affected'],
    content_language: 'en',
  },
  {
    disease_code: 'Potato___Late_blight',
    name: 'Potato Late Blight',
    crop: 'potato',
    category: 'Oomycete',
    created_at: '2026-09-28T09:00:00Z',
    symptoms_summary: 'Pale green to dark water-soaked blotches on leaves that spread quickly in damp weather.',
    prevention_summary: 'Plant healthy tubers, hill soil well and destroy infected plants.',
    overview: 'A serious disease that can destroy foliage within days under cool, wet conditions and can affect tubers.',
    symptoms: ['Water-soaked blotches on leaves', 'White fuzzy growth on leaf undersides in humid air', 'Brown, firm rot in tubers'],
    favourable_conditions: ['Cool, wet and humid weather'],
    preventive_measures: ['Use healthy seed tubers', 'Hill soil to cover tubers', 'Destroy cull piles'],
    cultural_management: ['Avoid irrigating late in the day'],
    organic_management: [],
    chemical_treatment: [],
    chemical_verified: false,
    consult_expert: ['Symptoms appear on many plants at once'],
    content_language: 'en',
  },
];

const toListItem = (d) => d;

// ---- Router ----
const respond = (config, status, data) => {
  const response = { data, status, statusText: String(status), headers: {}, config, request: {} };
  if (status < 400) return Promise.resolve(response);
  const msg = typeof data?.detail === 'string' ? data.detail : `Request failed with status ${status}`;
  return Promise.reject(new AxiosError(msg, status >= 500 ? 'ERR_BAD_RESPONSE' : 'ERR_BAD_REQUEST', config, {}, response));
};

const parseBody = (config) => {
  if (typeof config.data === 'string') {
    try {
      return JSON.parse(config.data);
    } catch {
      return {};
    }
  }
  return config.data || {};
};

const nameFromEmail = (email) => {
  const local = (email.split('@')[0] || 'Farmer').replace(/[._-]+/g, ' ');
  return local.replace(/\b\w/g, (c) => c.toUpperCase());
};

const handler = async (config) => {
  const method = (config.method || 'get').toLowerCase();
  const url = (config.url || '').replace(/\?.*$/, '');
  await sleep(250 + Math.random() * 350);

  // ---- auth ----
  if (url === '/auth/me' && method === 'get') {
    const user = read(SESSION_KEY, null);
    return user ? respond(config, 200, user) : respond(config, 401, { detail: 'Not authenticated' });
  }
  if (url === '/auth/login' && method === 'post') {
    const { email, password } = parseBody(config);
    if (!email || !password) return respond(config, 422, { detail: 'Email and password are required' });
    const users = read(USERS_KEY, {});
    const key = email.toLowerCase();
    write(SESSION_KEY, { id: 'preview-user', name: users[key] || nameFromEmail(email), email });
    return respond(config, 200, { success: true });
  }
  if (url === '/auth/register' && method === 'post') {
    const { name, email } = parseBody(config);
    const users = read(USERS_KEY, {});
    users[String(email).toLowerCase()] = name;
    write(USERS_KEY, users);
    return respond(config, 201, { success: true }); // no auto-login, so the "please sign in" flow is visible
  }
  if (url === '/auth/logout' && method === 'post') {
    write(SESSION_KEY, null);
    return respond(config, 204, null);
  }

  // everything below needs a session
  if (!read(SESSION_KEY, null)) return respond(config, 401, { detail: 'Not authenticated' });

  // ---- preferences ----
  if (url === '/users/me/preferences') {
    if (method === 'put') {
      const prefs = { ...read('afa.preview.prefs', {}), ...parseBody(config) };
      write('afa.preview.prefs', prefs);
      return respond(config, 200, prefs);
    }
    return respond(config, 200, read('afa.preview.prefs', {}));
  }

  // ---- diseases ----
  if (url === '/diseases' && method === 'get') {
    return respond(config, 200, { items: DISEASES.map(toListItem) });
  }
  const diseaseMatch = url.match(/^\/diseases\/(.+)$/);
  if (diseaseMatch && method === 'get') {
    const found = DISEASES.find((d) => d.disease_code === decodeURIComponent(diseaseMatch[1]));
    return found ? respond(config, 200, found) : respond(config, 404, { detail: 'Disease not found' });
  }

  // ---- predict (SAMPLE OUTPUT - not a model result) ----
  if (url === '/predict' && method === 'post') {
    await sleep(1200);
    const file = config.data?.get?.('image');
    const seed = file?.size || 1;
    const d = DISEASES[seed % DISEASES.length];
    const confidence = Math.round((0.55 + (seed % 43) / 100) * 100) / 100; // 0.55 - 0.97, sometimes low
    const record = {
      analysis_id: `preview-${Date.now()}`,
      crop: d.crop,
      disease_code: d.disease_code,
      disease: d.name,
      confidence,
      created_at: new Date().toISOString(),
      image_url: null,
    };
    write(HISTORY_KEY, [record, ...read(HISTORY_KEY, [])]);
    return respond(config, 200, {
      success: true,
      ...record,
      treatment: {
        summary: d.overview,
        preventive_measures: d.preventive_measures,
        organic_treatment: d.organic_management,
        chemical_treatment: [],
      },
      model_version: 'ui-preview (sample output, not a real prediction)',
    });
  }

  // ---- history ----
  if (url === '/history' && method === 'get') {
    const p = config.params || {};
    let items = read(HISTORY_KEY, []);
    const byDisease = new Map();
    items.forEach((r) => {
      const e = byDisease.get(r.disease_code) || { disease_code: r.disease_code, disease: r.disease, count: 0 };
      e.count += 1;
      byDisease.set(r.disease_code, e);
    });
    const summary = { by_disease: [...byDisease.values()] };
    const q = (p.search || '').toLowerCase();
    if (q) items = items.filter((r) => r.disease.toLowerCase().includes(q));
    if (p.crop) items = items.filter((r) => r.crop === p.crop);
    if (p.date_from) items = items.filter((r) => r.created_at.slice(0, 10) >= p.date_from);
    if (p.date_to) items = items.filter((r) => r.created_at.slice(0, 10) <= p.date_to);
    items = [...items].sort((a, b) => (p.sort === 'oldest' ? 1 : -1) * (new Date(b.created_at) - new Date(a.created_at)));
    const pageSize = Number(p.page_size) || 12;
    const page = Number(p.page) || 1;
    return respond(config, 200, {
      items: items.slice((page - 1) * pageSize, page * pageSize),
      total: items.length,
      page,
      page_size: pageSize,
      summary,
    });
  }

  return respond(config, 404, { detail: `Preview mode has no handler for ${method.toUpperCase()} ${url}` });
};

apiClient.defaults.adapter = handler;
