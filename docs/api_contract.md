# AI Farmer Assistant — API Contract Specification (MVP)

**Document Version:** 1.0.0  
**Target Consumers:** Web Frontend (Current MVP), Mobile Client (Future iOS / Android / Flutter)  
**Backend Protocol:** REST over HTTP / JSON  
**Base URL:** `/api/v1` (or root `/`)

---

## 1. Architectural Overview & Design Principles

The API contract establishes a clean, decoupled interface between client applications and the backend AI Farmer Assistant services.

1. **Client Agnostic:** Pure REST with standard `multipart/form-data` and JSON responses; easily consumed by browser `fetch`/`axios` as well as native mobile HTTP clients (`URLSession`, `Retrofit`, `Dio`).
2. **Deterministic Schema:** Every response adheres strictly to predictable schemas. Success and error structures never change shapes unexpectedly.
3. **Fail-Safe & Ergonomic:** Client-side user errors (corrupted photos, non-image files, oversized uploads) yield clean, descriptive HTTP 4xx errors with structured error codes rather than 500 server crashes.
4. **Agronomic Safety:** Low-confidence predictions (below 60%) trigger proactive advisory warnings rather than blind pesticide recommendations.

---

## 2. Endpoints Specification

### 2.1 Health & Diagnostics

- **Method:** `GET`
- **Path:** `/health`
- **Description:** Verifies service availability, ML model readiness, hardware execution device, and supported class count.
- **Headers:** None required.
- **Request Body:** None.

#### Success Response (`200 OK`)
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_version": "MobileNetV2-FineTuned-v1.0",
  "device": "cpu",
  "supported_classes": 13,
  "environment": "development",
  "timestamp": "2026-10-09T00:20:00Z"
}
```

---

### 2.2 Disease Prediction & Treatment Recommendation

- **Method:** `POST`
- **Path:** `/predict`
- **Description:** Analyzes an uploaded plant leaf photograph, classifies crop and disease using MobileNetV2, and retrieves authoritative agronomic treatment recommendations.
- **Content-Type:** `multipart/form-data`

#### Request Parameters:
| Field | Type | In | Required | Default | Description |
|---|---|---|---|---|---|
| `file` | `binary` (file) | Form Data | **Yes** | — | Leaf image file (`JPEG`, `PNG`, or `WebP`). Max 10 MB. |
| `confidence_threshold` | `float` | Query / Form | No | `0.60` | Minimum confidence score threshold (0.0 to 1.0). |

---

## 3. Response Schemas

### 3.1 Successful Prediction Schema (`200 OK`)

Returned when a valid leaf image is uploaded and processed successfully.

```json
{
  "success": true,
  "crop": "Tomato",
  "disease": "Early Blight",
  "confidence": 0.9786,
  "treatment": {
    "status": "success",
    "disease_key": "Tomato___Early_blight",
    "disease_name": "Early Blight",
    "crop": "Tomato",
    "pathogen_or_cause": "Alternaria linariae / Alternaria solani (Fungal pathogen)",
    "symptoms": [
      "Small brown-black spots on older, lower foliage that enlarge up to 1/2 inch.",
      "Concentric dark ridges producing a pronounced target-pattern appearance.",
      "Extensive yellowing of surrounding tissue and progressive defoliation from ground level upward.",
      "Sunken, leathery dark lesions on stems and fruit calyx ends."
    ],
    "preventive_measures": [
      "3-year crop rotation away from solanaceous plants.",
      "Plant certified disease-free seeds and inspected nursery transplants.",
      "Apply plastic or organic straw mulch around plant bases to block soil-splashed fungal spores.",
      "Choose resistant hybrids with collar rot/early blight resistance genes."
    ],
    "cultural_practices": [
      "Stake, cage, and trellis tomato vines to keep foliage elevated off bare soil.",
      "Prune bottom suckers and lower foliage up to 12-18 inches from the soil line once plants mature.",
      "Irrigate with ground drip lines; water in the morning so foliage dries rapidly.",
      "Clean pruning tools frequently between rows."
    ],
    "organic_treatment": [
      "Copper hydroxide, copper octanoate, or sulfur fungicides applied at the first sign of lower foliar spotting.",
      "Bio-fungicides based on Bacillus amyloliquefaciens or Trichoderma harzianum."
    ],
    "chemical_treatment": [
      "Broad-spectrum protectants (chlorothalonil, mancozeb) applied prior to disease establishment.",
      "Targeted systemic fungicides (e.g., azoxystrobin, pyraclostrobin, difenoconazole, boscalid) applied in rotation across FRAC groups to prevent resistance."
    ],
    "safety_warning": "Wear protective chemical-resistant clothing, gloves, and eye wear. Adhere strictly to label pre-harvest intervals (PHI) to prevent residue on edible tomato fruit.",
    "source": "Clemson Cooperative Extension / Cornell University Vegetable MD Online / UC IPM: Tomato Early Blight"
  },
  "model_version": "MobileNetV2-FineTuned-v1.0"
}
```

#### Field Specifications:
- `success` (`bool`): Always `true` for successful HTTP 200 responses.
- `crop` (`string`): Identified crop (`"Tomato"` or `"Potato"`).
- `disease` (`string`): Identified human-readable disease name (e.g., `"Early Blight"`, `"Late Blight"`, `"Healthy Foliage"`).
- `confidence` (`float`): Softmax prediction probability rounded to 4 decimals (range: `0.0000` to `1.0000`).
- `treatment` (`object`): Decoupled structured treatment recommendation with 9 required agronomic fields.
- `model_version` (`string`): Active model tag (e.g., `"MobileNetV2-FineTuned-v1.0"`).

---

## 4. Low-Confidence Behavior

### Policy & Agronomic Safety Rationale
Plant pathology decisions carry high real-world stakes: misdiagnosing a leaf disease could cause a farmer to spray unnecessary, expensive, or toxic chemicals. 
When the model confidence is below the diagnostic threshold (**`confidence < 0.60`**):

1. **HTTP Status Code:** `200 OK` (so client UI does not treat it as a network or server crash).
2. **Payload Adjustments:**
   - `success`: `true`
   - `is_low_confidence`: `true`
   - `confidence`: Raw probability score (e.g., `0.4215`)
   - `disease`: `"Low Confidence / Unverified"`
   - `crop`: Candidate crop or `"Uncertain"`
   - `treatment`: Contains safe, non-destructive advisory instructions instructing the farmer to retake the photo with better lighting or consult a human extension agent. Synthetic chemical treatments are withheld or flagged as strictly unverified.

#### Low-Confidence Response Example:
```json
{
  "success": true,
  "crop": "Tomato",
  "disease": "Low Confidence / Unverified",
  "confidence": 0.4215,
  "is_low_confidence": true,
  "treatment": {
    "status": "low_confidence",
    "disease_key": "unverified",
    "disease_name": "Low Confidence Prediction",
    "crop": "Tomato",
    "pathogen_or_cause": "Visual features insufficient for confident diagnosis (confidence: 42.15% < threshold 60.0%)",
    "symptoms": [
      "The uploaded photograph does not exhibit sufficiently distinct disease hallmarks.",
      "Image may be out of focus, taken in poor lighting, or displaying non-pathogenic leaf stress."
    ],
    "preventive_measures": [
      "Retake the photo in natural daylight, capturing an individual leaf flat against a neutral background.",
      "Ensure the camera is focused directly on the suspicious lesion or discoloration."
    ],
    "cultural_practices": [
      "Inspect both upper and lower leaf surfaces with a 10x hand lens.",
      "Check adjacent plants to determine whether symptoms are localized or widespread across the plot."
    ],
    "organic_treatment": [
      "Do not apply remedial treatments until symptoms can be clearly confirmed."
    ],
    "chemical_treatment": [
      "Do NOT apply chemical pesticides on unconfirmed diagnoses. Misapplication can harm healthy foliage and beneficial organisms."
    ],
    "safety_warning": "Applying pesticides without a positive identification can lead to unnecessary chemical exposure, crop injury, and regulatory non-compliance.",
    "source": "AI Farmer Assistant Diagnostic Confidence Safety Protocol"
  },
  "model_version": "MobileNetV2-FineTuned-v1.0"
}
```

---

## 5. Error Schema & Handling Matrix

All error responses return a standardized, machine-readable JSON structure:

```json
{
  "success": false,
  "error": {
    "code": "ERROR_CODE_STRING",
    "message": "Human-readable description for end-user display.",
    "details": "Technical explanation or validation failure details.",
    "timestamp": "2026-10-09T00:20:00Z"
  }
}
```

### Complete Error Matrix:

| Condition | HTTP Status | Error Code (`code`) | Message (`message`) |
|---|---|---|---|
| No file uploaded in request | `400 Bad Request` | `MISSING_FILE` | "No image file was provided in the request." |
| File has 0 bytes | `400 Bad Request` | `EMPTY_FILE` | "The uploaded file is empty (0 bytes)." |
| File exceeds 10 MB limit | `413 Payload Too Large` | `FILE_TOO_LARGE` | "Uploaded file exceeds maximum allowed limit of 10 MB." |
| Non-image file (`.pdf`, `.txt`, `.exe`) | `415 Unsupported Media Type` | `UNSUPPORTED_MEDIA_TYPE` | "Unsupported file format. Please upload a JPEG, PNG, or WebP image." |
| Corrupted or unreadable image bytes | `422 Unprocessable Entity` | `CORRUPTED_IMAGE` | "The uploaded file cannot be decoded as a valid image." |
| Image dimensions <= 0 pixels | `422 Unprocessable Entity` | `INVALID_IMAGE_DIMENSIONS` | "Image dimensions must be greater than zero." |
| Unhandled server exception | `500 Internal Server Error` | `INTERNAL_SERVER_ERROR` | "An unexpected server error occurred during inference." |
| Model weights missing / uninitialized | `503 Service Unavailable` | `SERVICE_UNAVAILABLE` | "Classification service is currently initializing. Please retry in a moment." |

---

## 6. Technical Specifications

### 6.1 Maximum Upload Size
- **Limit:** **10 MB (10,485,760 bytes)**.
- **Client Recommendation:** Client web browsers can optionally downscale images to max 1920x1080 before upload to conserve mobile bandwidth, but the API will reliably accept raw camera images up to 10 MB.

### 6.2 Supported Image Formats
- MIME types: `image/jpeg`, `image/png`, `image/webp`
- File extensions: `.jpg`, `.jpeg`, `.png`, `.webp`

### 6.3 CORS (Cross-Origin Resource Sharing) Requirements
- **Allowed Origins:**
  - Local Web Development: `http://localhost:3000`, `http://localhost:5173`, `http://127.0.0.1:3000`, `http://127.0.0.1:5173`
  - Production Origin: Configurable via `CORS_ORIGINS` environment variable (comma-separated list)
- **Allowed Methods:** `GET`, `POST`, `OPTIONS`
- **Allowed Headers:** `Content-Type`, `Authorization`, `Accept`, `X-Requested-With`
- **Exposed Headers:** `Content-Length`, `X-Process-Time`
- **Preflight Cache (Max-Age):** 86400 seconds (24 hours)

---

## 7. Client Integration Reference

### 7.1 Web Frontend (JavaScript / TypeScript Fetch Example)
```typescript
interface TreatmentDetails {
  status: string;
  disease_key: string;
  disease_name: string;
  crop: string;
  pathogen_or_cause: string;
  symptoms: string[];
  preventive_measures: string[];
  cultural_practices: string[];
  organic_treatment: string[];
  chemical_treatment: string[];
  safety_warning: string;
  source: string;
}

interface PredictionResponse {
  success: boolean;
  crop: string;
  disease: string;
  confidence: number;
  treatment: TreatmentDetails;
  model_version: string;
  is_low_confidence?: boolean;
}

async function predictPlantDisease(imageFile: File): Promise<PredictionResponse> {
  const formData = new FormData();
  formData.append("file", imageFile);

  const response = await fetch("/api/v1/predict", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const errorData = await response.json();
    throw new Error(errorData.error?.message || "Failed to analyze image");
  }

  return response.json();
}
```

### 7.2 Future Mobile Client Compatibility
Because standard `multipart/form-data` and JSON primitives are used without web-specific session cookies, a mobile client (React Native, Flutter, Swift/iOS, Kotlin/Android) can consume this exact API directly with zero modifications:
- React Native: `formData.append('file', { uri, name: 'leaf.jpg', type: 'image/jpeg' })`
- Flutter: `http.MultipartFile.fromPath('file', filePath)`
- Android (Retrofit): `@Multipart @POST("predict") Call<PredictionResponse> predict(@Part MultipartBody.Part file)`
- iOS (URLSession): Standard multipart body builder
