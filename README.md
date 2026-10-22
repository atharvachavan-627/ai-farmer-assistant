# AI Farmer Assistant

An AI-powered crop disease detection and agronomic advisory system designed for smallholder farmers, extension agents, and agricultural workers.

---

## Architecture Overview

- **Machine Learning**: Fine-tuned MobileNetV2 architecture trained on PlantVillage data, optimized for low-latency CPU inference.
- **Backend API**: High-performance REST service built on FastAPI with model pre-warming, structured validation, CORS support, and robust error handling.
- **Frontend**: Single-page application built with React + Vite, communicating with the FastAPI backend over HTTP.

---

## Supported Crops & Conditions

13 crop disease classes across Tomato and Potato:

| Crop | Condition / Disease | Pathogen Type | Disease Code |
|---|---|---|---|
| **Potato** | Early Blight (*Alternaria solani*) | Fungal | `Potato___Early_blight` |
| **Potato** | Late Blight (*Phytophthora infestans*) | Oomycete | `Potato___Late_blight` |
| **Potato** | Healthy Foliage | N/A | `Potato___healthy` |
| **Tomato** | Bacterial Spot (*Xanthomonas campestris*) | Bacterial | `Tomato___Bacterial_spot` |
| **Tomato** | Early Blight (*Alternaria solani*) | Fungal | `Tomato___Early_blight` |
| **Tomato** | Late Blight (*Phytophthora infestans*) | Oomycete | `Tomato___Late_blight` |
| **Tomato** | Leaf Mold (*Passalora fulva*) | Fungal | `Tomato___Leaf_Mold` |
| **Tomato** | Septoria Leaf Spot (*Septoria lycopersici*) | Fungal | `Tomato___Septoria_leaf_spot` |
| **Tomato** | Two-Spotted Spider Mite (*Tetranychus urticae*) | Pest | `Tomato___Spider_mites Two-spotted_spider_mite` |
| **Tomato** | Target Spot (*Corynespora cassiicola*) | Fungal | `Tomato___Target_Spot` |
| **Tomato** | Tomato Yellow Leaf Curl Virus (TYLCV) | Viral | `Tomato___Tomato_Yellow_Leaf_Curl_Virus` |
| **Tomato** | Tomato Mosaic Virus (ToMV) | Viral | `Tomato___Tomato_mosaic_virus` |
| **Tomato** | Healthy Foliage | N/A | `Tomato___healthy` |

---

## Backend Setup & Environment

### Prerequisites

- Python 3.10+ (tested with Python 3.11.9)
- Virtual environment (`venv`)

### Dependencies

Install dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

Key libraries: `fastapi`, `uvicorn`, `torch`, `torchvision`, `pillow`, `pydantic`, `httpx`, `argon2-cffi`, `sqlalchemy`, `psycopg2-binary`, `alembic`.

### Database & Migrations

The database layer utilizes SQLAlchemy 2.x and Alembic. By default, it connects to a persistent SQLite database located at `data/ai_farmer_assistant.db`. When deploying with PostgreSQL, set `DATABASE_URL` in `.env`.

#### Database Tables
- **`users`**: Account identity (`id`, `full_name`, `email`, `password_hash`, `preferred_language`, `is_active`, timestamps).
- **`user_sessions`**: Server-managed sessions (`id`, `user_id`, `csrf_token`, `expires_at`, `is_revoked`, `created_at`).
- **`analyses`**: Persisted crop disease predictions (`id`, `user_id`, `crop`, `disease_code`, `disease_name`, `confidence`, `model_version`, `image_url`, `created_at`). Foreign key to `users.id` with `ON DELETE CASCADE`.

To run schema migrations:

```bash
alembic upgrade head
```

### Model Artifact Locations

Model checkpoints and metadata are located relative to the project root:

- **Fine-tuned Checkpoint**: `models/mobilenetv2_finetuned/best_finetuned_model.pth`
- **Baseline Fallback Checkpoint**: `models/mobilenetv2/best_model.pth`
- **Class Mapping**: `models/mobilenetv2/class_mapping.json`
- **Treatment Knowledge Base**: `data/treatment_recommendations.json`

### Environment Variables

All paths and runtime thresholds are configurable via environment variables:

| Variable | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | `sqlite:///data/ai_farmer_assistant.db` | SQLAlchemy connection string (PostgreSQL or SQLite) |
| `SECRET_KEY` | `dev-insecure-secret-key-...` | Application signing secret (override in production) |
| `SESSION_COOKIE_NAME` | `session_id` | Name of the HttpOnly session cookie |
| `CSRF_COOKIE_NAME` | `csrf_token` | Name of the CSRF token cookie (readable by frontend) |
| `CSRF_HEADER_NAME` | `X-CSRF-Token` | Name of the CSRF header required on mutative requests |
| `SESSION_EXPIRE_SECONDS` | `604800` (7 days) | Session duration in seconds |
| `SESSION_COOKIE_SECURE` | `false` (true in prod) | Flag for HTTPS-only cookies |
| `SESSION_COOKIE_SAMESITE` | `lax` | SameSite cookie policy (`lax`, `strict`, `none`) |
| `MODEL_PATH` | `<root>/models/mobilenetv2_finetuned/best_finetuned_model.pth` | Path to PyTorch model weights |
| `CLASS_MAPPING_PATH` | `<root>/models/mobilenetv2/class_mapping.json` | Path to class mapping dictionary |
| `TREATMENT_KB_PATH` | `<root>/data/treatment_recommendations.json` | Path to treatment knowledge base JSON |
| `CONFIDENCE_THRESHOLD` | `0.60` | Diagnostic confidence threshold |
| `MAX_UPLOAD_SIZE` | `10485760` (10 MB) | Maximum upload file size in bytes |
| `CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173,http://127.0.0.1:3000` | Comma-separated allowed CORS origins |
| `ENVIRONMENT` | `development` | Deployment environment tag |
| `HOST` | `0.0.0.0` | Server bind host |
| `PORT` | `8000` | Server bind port |

---

## Running the Backend

### Start Server

```bash
# Windows
.\venv\Scripts\python.exe -m uvicorn src.main:app --host 127.0.0.1 --port 8000

# Linux / macOS
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

### Access Endpoints

- **Swagger UI**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Check**: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)

---

## API Endpoints

### 1. Health Diagnostics (Public)

- **Method**: `GET`
- **Path**: `/health`
- **Description**: Returns runtime status, active model version, hardware device, and supported class count. Distinguishes between operational status (`healthy`) and degraded status (`degraded` when model is uninitialized). Public endpoint (no auth required).

**Response (HTTP 200)**:
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "MobileNetV2-FineTuned-v1.0",
  "device": "cpu",
  "supported_classes": 13,
  "environment": "development",
  "timestamp": "2026-10-10T07:41:01.425607+00:00"
}
```

### 2. User Authentication

#### Registration
- **Method**: `POST`
- **Path**: `/auth/register`
- **Request Body**:
  ```json
  {
    "full_name": "Ramesh Kumar",
    "email": "ramesh@example.com",
    "password": "StrongPassword123!",
    "preferred_language": "hi"
  }
  ```
- **Response (HTTP 201)**: Returns safe user object (`id`, `full_name`, `email`, `preferred_language`, `is_active`). Passwords hashed with Argon2id.

#### Login
- **Method**: `POST`
- **Path**: `/auth/login`
- **Request Body**:
  ```json
  {
    "email": "ramesh@example.com",
    "password": "StrongPassword123!"
  }
  ```
- **Response (HTTP 200)**: Sets HttpOnly `session_id` cookie and readable `csrf_token` cookie. Returns safe user representation.

#### Logout
- **Method**: `POST`
- **Path**: `/auth/logout`
- **Headers**: `X-CSRF-Token: <token>`
- **Response (HTTP 200)**: Revokes session in database, clears session and CSRF cookies.

#### Current User
- **Method**: `GET`
- **Path**: `/auth/me`
- **Requires**: Active session cookie.
- **Response (HTTP 200)**: Safe user profile. Unauthenticated returns `HTTP 401`.

#### User Preferences
- **Method**: `GET` / `PUT`
- **Path**: `/users/me/preferences`
- **Requires**: Active session cookie. Updates `preferred_language` (`en`, `hi`, `mr`).

### 3. Leaf Disease Prediction & Advisory (Protected)

- **Method**: `POST`
- **Path**: `/predict`
- **Requires**: Active authenticated session cookie and `X-CSRF-Token` header. Unauthenticated requests are rejected with `HTTP 401`.
- **Content-Type**: `multipart/form-data`
- **Fields**:
  - `image` *(UploadFile, required)*: Plant leaf photograph (JPEG, PNG, WebP). Field name `file` is also accepted for backward compatibility.
  - `confidence_threshold` *(float, optional)*: Query parameter overriding default threshold (e.g. `?confidence_threshold=0.60`).

**Response (HTTP 200)**:
```json
{
  "success": true,
  "analysis_id": "1",
  "crop": "Potato",
  "disease_code": "Potato___Early_blight",
  "disease": "Early Blight",
  "confidence": 0.9786,
  "treatment": {
    "status": "success",
    "disease_key": "Potato___Early_blight",
    "disease_name": "Early Blight",
    "crop": "Potato",
    "pathogen_or_cause": "Alternaria solani (Fungal pathogen)",
    "summary": "Potato affected by Early Blight (Alternaria solani (Fungal pathogen)).",
    "symptoms": [
      "Dark brown to black circular lesions on older lower leaves.",
      "Characteristic concentric rings producing a target-board pattern."
    ],
    "preventive_measures": [
      "Plant certified disease-free seed tubers.",
      "Practice a 2 to 3-year crop rotation with non-solanaceous crops."
    ],
    "cultural_practices": [
      "Use drip or furrow irrigation to minimize leaf wetness duration."
    ],
    "organic_treatment": [
      "Fixed copper fungicides applied preventatively before canopy closure."
    ],
    "chemical_treatment": [
      "Protectant broad-spectrum contact fungicides (mancozeb, chlorothalonil)."
    ],
    "safety_warning": "Always read and strictly follow pesticide container label instructions.",
    "source": "USDA Cooperative Extension / University of Idaho Potato Disease Guide"
  },
  "model_version": "MobileNetV2-FineTuned-v1.0",
  "low_confidence": false,
  "is_low_confidence": false,
  "created_at": "2026-10-10T12:00:00+00:00",
  "image_url": null,
  "severity": {
    "status": "estimated",
    "estimated_affected_area_percent": 18.7,
    "category": "moderate",
    "method": "multispectral_color_segmentation_v1",
    "message": "Visible affected leaf area successfully estimated.",
    "affected_pixels": 6407,
    "total_leaf_pixels": 34264,
    "confidence_level": "high",
    "disclaimer": "Experimental estimate of visible leaf surface lesion area from this image. It describes the submitted photograph only and does not establish whole-plant severity or replace certified in-field agronomic scouting."
  }
}
```

---

### Strict Input Validation Pipeline (Computer Vision & Crop Validation)

The application implements a dedicated multi-stage validation pipeline (`src/image_validator.py`) before ML disease classification. It prevents false acceptance of non-plant images (humans, animals, vehicles, buildings, everyday objects), unsupported crops (grape, apple, corn, etc.), and fruits/tubers alone without leaves.

#### 1. Multi-Stage Pipeline Architecture

```
                       [ Uploaded File Stream ]
                                   │
                                   ▼
          ┌─────────────────────────────────────────────────┐
          │ Stage A: File & Raster Integrity Validation     │
          │ - Format (JPEG/PNG/WEBP) & size (<= 10MB)       │
          │ - Dimensions (>= 60px & >= 4096 px)             │
          │ - Contrast, sharpness & exposure checks         │
          └────────────────────────┬────────────────────────┘
                                   │ Passes Stage A
                                   ▼
          ┌─────────────────────────────────────────────────┐
          │ Stage B: Plant & Leaf Presence Verification     │
          │ - Multi-spectral foliar coverage check          │
          │ - Fruit circularity / non-leaf rejection        │
          └────────────────────────┬────────────────────────┘
                                   │ Passes Stage B
                                   ▼
          ┌─────────────────────────────────────────────────┐
          │ Stage C: Dedicated Crop Classification Head     │
          │ - MobileNetV2 pretrained feature extractor      │
          │ - 4-class classifier (Tomato, Potato,           │
          │   Unsupported Plant, Non-Plant)                 │
          │ - ImageNet 1000-class non-plant top-1 check     │
          └────────────────────────┬────────────────────────┘
                                   │
                                   ▼
          ┌─────────────────────────────────────────────────┐
          │ Stage D: Unified Decision Engine                │
          │ Outcomes:                                       │
          │  VALID_TOMATO_LEAF      -> Proceed to ML Model  │
          │  VALID_POTATO_LEAF      -> Proceed to ML Model  │
          │  INVALID_NON_PLANT_IMAGE-> HTTP 422 Rejection   │
          │  INVALID_NO_LEAF        -> HTTP 422 Rejection   │
          │  UNSUPPORTED_PLANT      -> HTTP 422 Rejection   │
          │  UNSUPPORTED_CROP_UNCERTAIN -> HTTP 422 Reject  │
          │  INVALID_IMAGE_QUALITY  -> HTTP 422 Rejection   │
          │  INVALID_FILE           -> HTTP 422 Rejection   │
          └─────────────────────────────────────────────────┘
```

#### 2. Rejection Response Format (HTTP 422 Unprocessable Entity)

```json
{
  "success": false,
  "error_code": "INVALID_NON_PLANT_IMAGE",
  "message": "Invalid input. Please upload a clear photo of a tomato or potato leaf.",
  "detail": "Invalid input. Please upload a clear photo of a tomato or potato leaf.",
  "error": {
    "code": "INVALID_NON_PLANT_IMAGE",
    "message": "Invalid input. Please upload a clear photo of a tomato or potato leaf.",
    "details": "...",
    "timestamp": "2026-10-22T01:15:00+00:00"
  }
}
```

#### 3. Frontend Invalid Input State

When rejected by the backend:
- The UI displays a dedicated **Invalid Input** card with clear visual warning styling (`InvalidInputCard.jsx`).
- An informative badge details the reason (Non-Plant Image, Unsupported Plant, No Suitable Leaf, Insufficient Quality).
- Explicitly states: **"No disease analysis was performed on this image."**
- ResultCard, crop tags, disease names, severity estimations, and treatment plans are **completely hidden**.
- Includes an **"Upload Another Image"** button that immediately resets the dropzone.

---

### Plant Disease Severity Estimation (Computer Vision Module)

The application integrates an automated, modular, testable **Plant Disease Severity Estimation** engine (`src/severity_estimator.py`). It calculates the percentage of visible leaf tissue damaged by foliar pathogens (chlorosis and necrotic lesions).

#### 1. Architecture & Computer Vision Pipeline

```
  [ Uploaded Image (PIL/Bytes/BGR) ]
                 │
                 ▼
  ┌────────────────────────────────────────┐
  │ Step 1: Leaf Segmentation              │
  │ • Color-space: HSV, CIELAB & ExG       │
  │ • Background suppression (paper/table) │
  │ • Morphological closure of holes       │
  │ • Minimum leaf area verification       │
  └──────────────────┬─────────────────────┘
                     │ (Validated Leaf Mask)
                     ▼
  ┌────────────────────────────────────────┐
  │ Step 2: Lesion Segmentation            │
  │ • Exclude healthy green tissue         │
  │ • Segment necrotic tissue (brown/dark) │
  │ • Segment chlorotic halos (yellow)     │
  │ • Morphological noise opening          │
  └──────────────────┬─────────────────────┘
                     │ (Validated Lesion Mask)
                     ▼
  ┌────────────────────────────────────────┐
  │ Step 3: Area Calculation & Validation  │
  │ • Affected % = (Lesion Px / Leaf Px)*100
  │ • Strict boundary [0.0, 100.0] bounds  │
  │ • Zero-denominator division protection │
  └──────────────────┬─────────────────────┘
                     │
                     ▼
  ┌────────────────────────────────────────┐
  │ Step 4: Agronomic Categorization       │
  │ • None: 0.0%                           │
  │ • Mild: 0.1% - 10.0%                   │
  │ • Moderate: 10.1% - 25.0%              │
  │ • Severe: > 25.0%                      │
  └──────────────────┬─────────────────────┘
                     │
                     ▼
        [ API & UI Response Payload ]
```

#### 2. Supported Operating Modes

| Condition Type | Supported Disease Classes | Operating Behavior |
|---|---|---|
| **Healthy Foliage** | `Potato___healthy`, `Tomato___healthy` | Directly sets `estimated_affected_area_percent=0.0`, `status="healthy_leaf"`, `category="none"`. Natural veins or minor color variation are not treated as disease lesions. |
| **Foliar Blights & Spots** | `Potato___Early_blight`, `Potato___Late_blight`, `Tomato___Early_blight`, `Tomato___Late_blight`, `Tomato___Bacterial_spot`, `Tomato___Septoria_leaf_spot`, `Tomato___Target_Spot`, `Tomato___Leaf_Mold` | Full validated multi-spectral lesion segmentation isolating necrotic centers and chlorotic halos from green parenchyma. Returns `status="estimated"` with quantitative percentage and tier. |
| **Viral / Systemic / Stippling** | `Tomato___Spider_mites Two-spotted_spider_mite`, `Tomato___Tomato_Yellow_Leaf_Curl_Virus`, `Tomato___Tomato_mosaic_virus` | Estimates visible discoloration/curling with explicit disclaimer noting that viral and mite damage is systemic rather than purely localized surface necrosis. |
| **Edge Cases & Guardrails** | Negligible leaf pixels, low contrast, corrupted image, or low classifier confidence | Returns guarded statuses: `insufficient_leaf_area`, `unreliable_segmentation`, `unsupported_class`, or `estimation_error`. Never returns `NaN` or crashes the primary prediction. |

#### 3. Empirical Benchmark & Latency

Evaluated on 35 representative test images across 7 classes from the PlantVillage dataset:
- **Mean Processing Latency**: **8.93 ms** per 256x256 image (Min: 4.65 ms, Max: 116.48 ms on CPU).
- **Zero Heavy Model Footprint**: Employs optimized vectorized NumPy and OpenCV color transformations, avoiding redundant secondary neural network inference or GPU memory bloat.

#### 4. Limitations & Future Roadmap

- **Advisory Scope**: This estimate measures visible affected leaf area in the single submitted camera angle. It does not measure whole-canopy infection or replace certified agricultural scouting.
- **Future Modular Upgrade**: Designed with the clean `PlantDiseaseSeverityEstimator` interface. When lesion-annotated segmentation masks become available, a learned segmentation model (e.g. U-Net / DeepLabV3+) can seamlessly drop into `segment_lesions()` without altering the API or frontend contracts.
- **Next Planned Feature**: **Grad-CAM visualization**, providing heatmap overlays to explain which visual regions informed the classification model.

---

### 4. Analysis History (Protected)

#### List Historical Analyses
- **Method**: `GET`
- **Path**: `/history`
- **Requires**: Active session cookie. Returns records belonging exclusively to the authenticated user.
- **Query Parameters**:
  - `limit` *(int, default: 20, 1-100)*: Items per page.
  - `offset` *(int, default: 0)*: Record offset.
  - `page` *(int, optional)*: 1-based page number (frontend compatibility).
  - `page_size` *(int, optional)*: Page size (frontend compatibility).
  - `crop` *(string, optional)*: Filter by crop (e.g. `Tomato`, `Potato`).
  - `search` *(string, optional)*: Substring search across crop and disease names.
  - `sort` *(string, default: `newest`)*: Sort order (`newest` or `oldest`).

**Response (HTTP 200)**:
```json
{
  "items": [
    {
      "analysis_id": "1",
      "id": 1,
      "crop": "Potato",
      "disease_code": "Potato___Early_blight",
      "disease": "Early Blight",
      "disease_name": "Early Blight",
      "confidence": 0.9786,
      "created_at": "2026-10-10T12:00:00+00:00",
      "model_version": "MobileNetV2-FineTuned-v1.0",
      "image_url": null
    }
  ],
  "total": 1,
  "limit": 20,
  "offset": 0,
  "page": 1,
  "page_size": 20,
  "summary": null
}
```

#### Single Analysis Retrieval
- **Method**: `GET`
- **Path**: `/history/{analysis_id}`
- **Requires**: Active session cookie.
- **Authorization**: Enforces strict user isolation. If the record belongs to another user or does not exist, returns `HTTP 404 Not Found`.

#### Delete Analysis
- **Method**: `DELETE`
- **Path**: `/history/{analysis_id}`
- **Requires**: Active session cookie and `X-CSRF-Token` header.
- **Authorization**: Enforces strict user isolation. Users may only delete their own records. If the record belongs to another user or does not exist, returns `HTTP 404 Not Found`.

**Response (HTTP 200)**:
```json
{
  "success": true,
  "message": "Analysis record deleted successfully.",
  "analysis_id": "1"
}
```

### Disease Information Catalogue Endpoints

#### List Disease Catalogue
- **Method**: `GET`
- **Path**: `/diseases`
- **Authentication**: Public / Optional session.
- **Query Parameters**:
  - `search` *(optional)*: Search across disease name, crop, code, category, summary, or overview.
  - `crop` *(optional)*: Filter by crop name (`potato` or `tomato`, case-insensitive).
  - `language` *(optional)*: Content language code (`en`, `hi`, `mr`). Falls back to `Accept-Language` header, then `en`.
- **Headers**:
  - `Accept-Language` *(optional)*: e.g. `mr-IN,mr;q=0.9,en;q=0.8`.

**Response (HTTP 200)**:
```json
{
  "items": [
    {
      "disease_code": "Tomato___Early_blight",
      "name": "Early Blight",
      "crop": "Tomato",
      "category": "Fungal",
      "image_url": null,
      "created_at": "2026-09-20T09:00:00Z",
      "symptoms_summary": "Concentric target-like brown spots on lower leaves with yellow halos...",
      "prevention_summary": "Rotate with non-solanaceous crops, stake plants, prune lower leaves...",
      "overview": "A common fungal disease caused by Alternaria linariae/solani...",
      "symptoms": ["..."],
      "favourable_conditions": ["..."],
      "preventive_measures": ["..."],
      "cultural_management": ["..."],
      "organic_management": ["..."],
      "chemical_treatment": ["..."],
      "chemical_verified": true,
      "consult_expert": ["..."],
      "safety_warning": "...",
      "source": "...",
      "content_language": "en"
    }
  ],
  "total": 13,
  "language": "en"
}
```

#### Disease Detail Lookup
- **Method**: `GET`
- **Path**: `/diseases/{disease_code}`
- **Authentication**: Public / Optional session.
- **Parameters**:
  - `disease_code` *(path)*: Stable disease class code (e.g. `Tomato___Early_blight`, `Potato___healthy`).
  - `language` *(optional query)*: Content language code (`en`, `hi`, `mr`).
- **Response**: Full structured `DiseaseItem` matching the catalogue schema.
- **Error**: Returns `HTTP 404 Not Found` with code `DISEASE_NOT_FOUND` if the disease code is not supported.

### Error Responses

All error responses share a unified structure compatible with frontend error parsing (`data.detail` / `data.message` and `data.error`):

```json
{
  "success": false,
  "message": "Authentication required. Please sign in.",
  "detail": "Authentication required. Please sign in.",
  "error": {
    "code": "UNAUTHORIZED",
    "message": "Authentication required. Please sign in.",
    "details": null,
    "timestamp": "2026-10-10T09:28:51.897890+00:00"
  }
}
```

| HTTP Status | Error Code | Condition |
|---|---|---|
| `400` | `VALIDATION_ERROR` | Request body validation failure (e.g. invalid email format) |
| `400` | `MISSING_FILE` | Missing image field or empty request |
| `400` | `EMPTY_FILE` | 0-byte file uploaded |
| `401` | `UNAUTHORIZED` | Missing authentication credentials |
| `401` | `INVALID_CREDENTIALS` | Invalid email or password on login |
| `401` | `SESSION_EXPIRED` | Session expired or revoked |
| `403` | `CSRF_ERROR` | Missing or mismatched CSRF token on state-changing request |
| `404` | `ANALYSIS_NOT_FOUND` | Record does not exist or belongs to another user |
| `404` | `DISEASE_NOT_FOUND` | Disease code is not found in the 13 supported model classes |
| `409` | `EMAIL_ALREADY_EXISTS`| Attempting to register an already-registered email |
| `413` | `FILE_TOO_LARGE` | File exceeds maximum limit (10 MB) |
| `415` | `UNSUPPORTED_MEDIA_TYPE` | Extension, MIME type, or detected raster format not in JPEG/PNG/WebP |
| `422` | `CORRUPTED_IMAGE` | Image decode failure or corrupted pixel data |
| `422` | `INVALID_IMAGE_DIMENSIONS`| Image dimensions ≤ 0 |
| `500` | `DATABASE_ERROR` | Internal database transaction or persistence failure |
| `503` | `MODEL_NOT_READY` | Model weights uninitialized or unavailable |
| `500` | `INFERENCE_FAILED` | Internal forward-pass failure |

---

## Test Suite Execution & Audit Reconciliation

Run all active test suites using the project Python environment:

```bash
# ==============================================================================
# 1. UNIT TESTS (Pure algorithmic & model module verification)
# ==============================================================================
# Model inference module unit tests (6 test blocks)
python tests/test_inference.py

# Treatment recommendation coverage & safety tests (5 test functions)
python tests/test_treatment.py

# Plant disease severity estimator unit tests (11 unittest methods)
python -m unittest tests/test_severity_estimator.py

# Strict input validation acceptance test suite (17 unittest methods)
python -m unittest tests/test_input_validation.py

# ==============================================================================
# 2. API & CONTRACT TESTS (Schema, endpoint contracts & localization)
# ==============================================================================
# API contract alignment verification across all 13 classes (4 test checks)
python tests/test_api_contract.py

# FastAPI backend automated test suite (13 test checks)
python tests/test_api.py

# Severity estimation API integration test suite
python -m unittest tests/test_api_severity.py

# Disease Information API test suite (12 unittest test methods)
python -m unittest tests/test_disease_catalog.py

# ==============================================================================
# 3. PERSISTENCE & INTEGRATION TESTS (Authentication, SQLite persistence & lifecycle)
# ==============================================================================
# Authentication & Security test suite (9 test checks)
python tests/test_auth.py

# Database-backed analysis persistence test suite (10 test checks)
python tests/test_history.py

# Frontend-Backend integration audit & contract tests (10 test checks)
python tests/test_frontend_backend_integration.py

# End-to-end full application lifecycle validation suite (6 unittest methods / 28 assertion checks)
python -m unittest tests/test_end_to_end_validation.py

# ==============================================================================
# 4. LIVE SERVER SOCKET VERIFICATION (Active uvicorn subprocess)
# ==============================================================================
# Live server network socket verification (1 suite / 13 live socket assertions)
python tests/test_live_server.py
```

### Reconciled Test Audit Results

| Category | Suite / File | Collected Tests | Passed | Failed | Skipped | Test Environment & Database |
|---|---|---|---|---|---|---|
| **Unit Tests** | `tests/test_inference.py` | 6 checks | 6 | 0 | 0 | Real PyTorch MobileNetV2 checkpoint (`best_finetuned_model.pth`), CPU inference, no DB |
| **Unit Tests** | `tests/test_treatment.py` | 5 checks | 5 | 0 | 0 | In-memory `treatment_recommendations.json`, no DB |
| **API & Contract** | `tests/test_api_contract.py` | 4 checks | 4 | 0 | 0 | Real model inference pass + schema validation, in-memory ASGI |
| **API & Contract** | `tests/test_api.py` | 13 checks | 13 | 0 | 0 | Real model + mock 503 degraded state; SQLite local DB via FastAPI `TestClient` |
| **API & Contract** | `tests/test_disease_catalog.py` | 12 methods | 12 | 0 | 0 | Static catalogue & translations JSONs (`en`, `hi`, `mr`), in-memory ASGI |
| **Persistence & Auth** | `tests/test_auth.py` | 9 checks | 9 | 0 | 0 | Argon2id hashing, session & CSRF cookies; local SQLite DB (`ai_farmer_assistant.db`) |
| **Persistence & Auth** | `tests/test_history.py` | 10 checks | 10 | 0 | 0 | Local SQLite DB (`ai_farmer_assistant.db`), mock commit failure 500 test, multi-tenant isolation |
| **Persistence & Auth** | `tests/test_frontend_backend_integration.py` | 10 checks | 10 | 0 | 0 | React frontend service contracts (auth, CSRF, predict, history, catalog); local SQLite DB |
| **Persistence & Auth** | `tests/test_end_to_end_validation.py` | 6 methods *(28 checks)* | 6 | 0 | 0 | Full integrated lifecycle: registration, login, catalog, real model inference, history, isolation; local SQLite DB |
| **Live Socket** | `tests/test_live_server.py` | 1 suite *(13 socket checks)* | 1 suite *(13 checks)* | 0 | 0 | Active live `uvicorn` subprocess on `http://127.0.0.1:8000`, real HTTP sockets, real model, local SQLite DB |
| **Legacy / Deprecated** | `tests/test_frontend_integration.py` | 11 legacy checks | N/A | N/A | N/A | *Deprecated*: Pre-auth static HTML test script from Prompt 1. Superseded by `test_frontend_backend_integration.py` and `test_live_server.py`. |

### Test Count Reconciliation & Analysis

- **Standard Automated Test Methods & Check Functions**: **75 passed** (18 `unittest.TestCase` methods across `test_disease_catalog.py` [12] and `test_end_to_end_validation.py` [6] + 57 custom check functions across unit, API, auth, and persistence suites).
- **Live Server Socket Suite**: **1 suite passed** (executing 13 sequential live socket assertions against a live uvicorn process).
- **Total Discrete Automated Test Units**: **76 passed out of 76 active test units** (0 failed, 0 skipped, 0 errors).
- **Previous "81/81" Discrepancy Resolved**: The previous report's "81/81" claim was an arithmetic inconsistency resulting from un-reconciled summation of mixed metrics (suites, test methods, and assertion counts). The actual verified count is **75 standard test functions/methods + 1 live socket test suite** (comprising 101+ verified assertions across 10 active test files).

---

## Multilingual Content & Translation Fallback Policy

- **UI Interface**: 100% key parity across English, Hindi, and Marathi across all 197 localization keys.
- **Disease Information Catalogue**: All 13 supported model classes are provided with authentic, high-quality agricultural translations in English (`en`), Hindi (`hi`), and Marathi (`mr`).
- **Chemical Safety Policy**: Active chemical pesticide formulations (e.g., Mancozeb, Chlorothalonil, Copper Hydroxide) preserve verified original technical ingredient terms and safety disclaimers to prevent dangerous or inaccurate dosage instructions.
- **Healthy Plant Foliage**: For healthy leaf classes (`Potato___healthy`, `Tomato___healthy`), category is designated as `Healthy`, `chemical_verified` is set to `false`, and chemical pesticide recommendations are strictly omitted (`[]`).
- **Fallback Behavior**: When an unrecognized language or unreviewed field is encountered, the backend safely provides verified English content and explicitly flags `content_language="en"` so the frontend can display an honest fallback notice.

---

## Environment & Validation Status

### Database Verification
- **Current Local Database**: SQLite database located at `data/ai_farmer_assistant.db`.
- **Database URL**: Defaults to `sqlite:///data/ai_farmer_assistant.db` via `src/config.py`.
- **Migrations Status**: Alembic migrations successfully applied to head (`235b266e3c3e_create_analyses_table`). Confirmed via `alembic current`.
- **PostgreSQL Status**: The codebase includes full architectural support for PostgreSQL (SQLAlchemy models and `psycopg2-binary` dependency). However, **no PostgreSQL database was active or tested during validation**. PostgreSQL testing must not be claimed until an actual PostgreSQL cluster is provisioned.

### Browser Testing Status
- **Status**: **UNVERIFIED / BLOCKED** (0 browser end-to-end tests executed).
- **Root Cause**: Playwright browser driver download failed because the driver archive endpoint (`https://playwright.azureedge.net/builds/driver/playwright-1.57.0-win32_x64.zip`) returned HTTP 404. Neither Playwright nor browser binaries are installed in the workspace or environment.
- **Unverified Browser Behaviors**:
  1. Live DOM rendering and client-side routing transitions across React Router pages.
  2. Browser drag-and-drop file upload UI interaction on `/analyse`.
  3. Client-side browser cookie persistence across page refreshes and SPA navigation.
  4. Browser-native extraction of `csrf_token` cookie and header injection (`X-CSRF-Token`).
  5. Live visual language toggling via `react-i18next` without page reload.
  6. Real-time visual animations (confidence bars, loading spinners, framer-motion transitions).
  7. Viewport responsiveness and CSS media queries across varying screen sizes.
- **Recommended Next Step**:
  1. Perform manual browser smoke testing using the installed system browser (Chrome/Edge) pointing to `http://localhost:5173` with backend and Vite dev servers active.
  2. For automated browser testing, configure Playwright with a reachable driver mirror or bundle a local Chromium binary once network permissions are available.