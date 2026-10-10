# AI Farmer Assistant – Web Frontend

React + Vite single-page app for the AI Farmer Assistant. Users sign in, upload a crop leaf photo, get a model prediction with treatment guidance, browse a disease guide and review their analysis history. UI languages: English, Hindi, Marathi.

This repo contains **only the frontend**. It talks to the FastAPI backend over HTTP and contains no mock data, fake predictions or fake sessions.

## Quick start

```bash
npm install
cp .env.example .env     # then edit if your backend is not on localhost:8000
npm run dev              # http://localhost:5173
npm run dev:preview      # UI preview WITHOUT a backend (sample data, dev only)
npm run build            # production build into dist/
npm run preview          # serve the production build locally
```

## UI preview mode (no backend)

`npm run dev:preview` starts the dev server with an in-browser stub (`src/dev/`) in place of the API, so you can click through every page. Any email and password signs you in. Predictions, history and disease content are **simulated sample data**, and an orange banner says so. It is dev-only, off by default, and excluded from production builds. Use plain `npm run dev` to talk to the real backend.

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `VITE_API_BASE_URL` | `http://localhost:8000` | Base URL of the FastAPI backend (no trailing slash) |

`VITE_*` values are bundled into the browser. Never put secrets in them.

## Routes

| Path | Access | Page |
|---|---|---|
| `/login`, `/register` | public | Sign in / create account |
| `/` | protected | Home |
| `/analyse` | protected | Upload + analyse a leaf |
| `/history` | protected | Personal analysis history |
| `/info` | protected | Disease guide |
| `/info/:diseaseCode` | protected | Disease details |

`ProtectedRoute` waits for `GET /auth/me` to confirm the session. Unauthenticated users are redirected to `/login` and returned to the page they asked for. If the backend cannot be reached, a "could not verify your session" screen with Retry is shown – the user is **never** treated as signed in.

## Authentication assumptions

The frontend assumes **cookie-based sessions**:

- The backend sets an `HttpOnly` (ideally `Secure`, `SameSite=Lax`) session cookie on login and clears it on logout.
- All requests use `withCredentials: true`; no token is stored in `localStorage`.
- Backend CORS must allow the frontend origin explicitly with `allow_credentials=True` (a wildcard origin does not work with credentials).
- CSRF: if the backend issues a readable `csrf_token` cookie, the client echoes it in an `X-CSRF-Token` header on non-GET requests. Adjust `CSRF_COOKIE` / `CSRF_HEADER` in `src/services/apiClient.js` if your names differ.
- Any `401` from an authenticated request is treated as an expired session and returns the user to Login.

If you choose token auth instead, only `src/services/apiClient.js` and `src/services/authService.js` need to change.

Only the UI language preference is kept in `localStorage` (key `afa.language`).

## Required backend endpoints

| Method & path | Notes |
|---|---|
| `POST /auth/register` | Body `{ name, email, password }`. May or may not start a session. |
| `POST /auth/login` | Body `{ email, password }`. Sets session cookie. |
| `POST /auth/logout` | Clears session cookie. |
| `GET /auth/me` | Returns `{ id, name, email }` (or `{ user: {...} }`). `401` when not signed in. |
| `GET /users/me/preferences` | Optional. `{ language: "en" \| "hi" \| "mr" }`. Failure is tolerated. |
| `PUT /users/me/preferences` | Optional. Body `{ language }`. Failure is ignored. |
| `POST /predict` | `multipart/form-data`, field `image`. See below. |
| `GET /history` | Authenticated, per-user. See below. |
| `GET /diseases` | Disease catalogue. |
| `GET /diseases/{disease_code}` | Disease detail. |

Validation errors (`400/409/422`) are shown using the backend's `detail` / `message` text. The frontend validates for usability only.

### `POST /predict` response

```json
{
  "success": true,
  "analysis_id": "…",
  "crop": "tomato",
  "disease_code": "Tomato___Early_blight",
  "disease": "Tomato Early Blight",
  "confidence": 0.94,
  "treatment": {
    "summary": "…",
    "preventive_measures": [],
    "organic_treatment": [],
    "chemical_treatment": []
  },
  "model_version": "mobilenetv2-v1"
}
```

Optional extras the UI uses when present: `created_at`, `low_confidence` (boolean). Without `low_confidence`, confidence below 70% (`LOW_CONFIDENCE_THRESHOLD` in `src/utils/format.js`) triggers a low-confidence warning. If your schema differs, adapt `normalisePrediction` in `src/services/analysisService.js` – nothing else.

### `GET /history`

Query params sent: `page`, `page_size`, `search`, `crop`, `date_from`, `date_to` (YYYY-MM-DD), `sort` (`newest` | `oldest`). Empty params are omitted.

```json
{
  "items": [
    { "analysis_id": "…", "crop": "tomato", "disease_code": "…", "disease": "…",
      "confidence": 0.91, "created_at": "2026-10-01T10:00:00Z", "image_url": "/media/…" }
  ],
  "total": 42, "page": 1, "page_size": 12,
  "summary": { "by_disease": [ { "disease_code": "…", "disease": "…", "count": 7 } ] }
}
```

A bare array is accepted too. `summary` is optional; without it, the frequency chart is derived from the records currently loaded. `image_url` is optional (relative URLs are resolved against `VITE_API_BASE_URL`). The backend must scope records to the signed-in user.

### `GET /diseases` and `GET /diseases/{disease_code}`

The frontend sends `Accept-Language` (`en`/`hi`/`mr`) so the backend can localise content. List items (array or `{ items }`) and detail share these fields:

`disease_code`, `name`, `crop`, `category`, `image_url`, `created_at`, `symptoms_summary`, `prevention_summary`, `overview`, `symptoms[]`, `favourable_conditions[]`, `preventive_measures[]`, `cultural_management[]`, `organic_management[]`, `chemical_treatment[]`, `chemical_verified` (boolean), `consult_expert[]`, `content_language`.

- Chemical treatment is shown **only** when `chemical_verified` is `true`. It is displayed exactly as returned and never auto-translated.
- If `content_language` differs from the selected language, a notice says the content is shown in the fallback language.
- "Recently added" on Home uses `created_at` when every entry has it, otherwise the backend's order (first 3).

### Database-related backend requirements

- Persist each prediction per user (analysis id, crop, disease code, confidence, timestamp, optional image) so `/history` can serve it.
- Enforce ownership on every history query.
- Store the user's language preference if you implement the preferences endpoints.

## Multilingual support

- `i18next` + `react-i18next`; files in `src/i18n/locales/{en,hi,mr}/translation.json`.
- Language switches instantly (no reload), is saved in `localStorage`, sets `<html lang>`, and is synced to `PUT /users/me/preferences` when signed in. Saved preference is applied after login.
- Missing keys fall back to English; empty strings are not rendered.
- Disease codes and API identifiers are never translated. Disease and treatment text comes from the backend.
- Fonts: Plus Jakarta Sans with Noto Sans Devanagari (loaded from Google Fonts in `index.html`).

**Add a language:** create `src/i18n/locales/<code>/translation.json` (copy `en`), import it and add it to `resources` in `src/i18n/index.js`, and add an entry to `SUPPORTED_LANGUAGES`. Add the locale to `LOCALES` in `src/utils/format.js` for dates and numbers.
**Add a string:** add the key to all three files; use `t('your.key')`.

## Project structure

```
src/
  auth/        AuthProvider, ProtectedRoute, useAuth
  services/    apiClient + auth / analysis / history / disease / preference services
  i18n/        i18n setup and locale files
  components/  layout, common, auth, analysis, history, disease
  pages/       Login, Register, Home, Analyse, History, DiseaseInfo, DiseaseDetails, NotFound
  hooks/       useFetch, useDebounce, useDropdown, useDocumentTitle
  utils/       errors, format, constants
```

## Tuning

- Upload limits (client-side only; backend is authoritative): `src/utils/constants.js`.
- Supported crops shown in the UI: tomato and potato (`History.jsx` filter, `Analyse.jsx` info panel).

## Known limitations

- Not tested against a real backend; the API contracts above are assumptions to confirm with the backend team.
- Password recovery is not implemented; the "Forgot password?" link only explains that it is unavailable.
- No automated test suite yet.
- The history frequency chart is partial when the backend sends no `summary`.
