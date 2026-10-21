"""
FastAPI application for AI Farmer Assistant.

Implements approved API contract:
- GET /health
- POST /predict
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
import io
import logging

from fastapi import FastAPI, File, UploadFile, Query, Request, Response, Depends, status
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from PIL import Image
from sqlalchemy.orm import Session

from src.config import get_settings
from src.database import get_db, init_db
from src.models import User, Analysis, utcnow
from src.auth import (
    AuthException,
    hash_password,
    verify_password,
    create_user_session,
    revoke_user_session,
    set_auth_cookies,
    clear_auth_cookies,
    extract_session_token,
    get_current_active_user,
    get_current_user
)
from src.inference import DiseaseClassifier, get_classifier
from src.treatment import TreatmentAdvisor, get_advisor
from src.disease_catalog import DiseaseCatalogService, get_catalog_service
from src.schemas import (
    HealthResponse,
    PredictionResponse,
    TreatmentDetails,
    ErrorResponse,
    ErrorDetails,
    UserRegisterRequest,
    UserLoginRequest,
    UserPublic,
    AuthResponse,
    UserPreferencesRequest,
    UserPreferencesResponse,
    HistoryItem,
    HistoryListResponse,
    HistoryDeleteResponse,
    DiseaseItem,
    DiseaseCatalogueResponse
)

# Configure logging
settings = get_settings()
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ai_farmer_assistant.api")


class APIError(Exception):
    """Custom API exception with structured error code and message."""
    def __init__(self, status_code: int, code: str, message: str, details: Optional[str] = None):
        self.status_code = status_code
        self.code = code
        self.message = message
        self.details = details
        super().__init__(message)


def get_current_timestamp() -> str:
    """Returns ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Pre-loads ML model and knowledge base into memory on startup for zero per-request initialization lag.
    """
    logger.info("Initializing AI Farmer Assistant services...")
    
    # 0. Initialize database tables
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization warning: {e}")

    # 1. Warm up DiseaseClassifier singleton
    try:
        classifier = get_classifier()
        logger.info(
            f"DiseaseClassifier initialized successfully. Model: {classifier.model_version}, "
            f"Device: {classifier.device}, Classes: {classifier.num_classes}"
        )
    except Exception as e:
        logger.warning(f"DiseaseClassifier initialization warning (will run in degraded mode if unready): {e}")

    # 2. Warm up TreatmentAdvisor singleton
    try:
        advisor = get_advisor()
        logger.info(
            f"TreatmentAdvisor initialized successfully. Supported entries: {len(advisor.list_supported_diseases())}"
        )
    except Exception as e:
        logger.warning(f"TreatmentAdvisor initialization warning: {e}")

    # 3. Warm up DiseaseCatalogService singleton
    try:
        catalog_svc = get_catalog_service()
        logger.info(
            f"DiseaseCatalogService initialized successfully. Supported classes: {len(catalog_svc.list_supported_codes())}"
        )
    except Exception as e:
        logger.warning(f"DiseaseCatalogService initialization warning: {e}")

    logger.info("AI Farmer Assistant backend is ready to accept requests.")
    yield
    logger.info("Shutting down AI Farmer Assistant services.")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Disease Classification and Agronomic Recommendation API for Tomatoes and Potatoes.",
    lifespan=lifespan
)

# Mount frontend static files (CSS, JS)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static")

# Mount public images directory (disease catalogue photos, fallbacks)
PUBLIC_IMAGES_DIR = FRONTEND_DIR / "public" / "images"
DIST_IMAGES_DIR = FRONTEND_DIR / "dist" / "images"
STATIC_IMAGES_DIR = PUBLIC_IMAGES_DIR if PUBLIC_IMAGES_DIR.exists() else DIST_IMAGES_DIR
if STATIC_IMAGES_DIR.exists():
    app.mount("/images", StaticFiles(directory=str(STATIC_IMAGES_DIR)), name="images")

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=["Content-Length", "X-Process-Time"]
)


# Exception Handlers
@app.exception_handler(AuthException)
async def auth_exception_handler(request: Request, exc: AuthException):
    """Handles authentication and session exceptions."""
    logger.warning(f"AuthException [{exc.code}] {exc.status_code}: {exc.message}")
    payload = ErrorResponse(
        success=False,
        message=exc.message,
        detail=exc.message,
        error=ErrorDetails(
            code=exc.code,
            message=exc.message,
            details=None,
            timestamp=get_current_timestamp()
        )
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError):
    """Handles controlled API exceptions."""
    logger.warning(f"APIError [{exc.code}] {exc.status_code}: {exc.message}")
    payload = ErrorResponse(
        success=False,
        message=exc.message,
        detail=exc.message,
        error=ErrorDetails(
            code=exc.code,
            message=exc.message,
            details=exc.details,
            timestamp=get_current_timestamp()
        )
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    """Handles request validation errors (e.g., missing form fields)."""
    errors_str = str(exc.errors())
    logger.warning(f"Request validation error: {errors_str}")
    
    # Check if missing file or image upload
    is_missing_file = any("image" in str(err.get("loc", [])) or "file" in str(err.get("loc", [])) for err in exc.errors())
    code = "MISSING_FILE" if is_missing_file else "INVALID_REQUEST"
    msg = "No image file was provided in the request." if is_missing_file else "The request parameters failed validation."

    payload = ErrorResponse(
        success=False,
        message=msg,
        detail=msg,
        error=ErrorDetails(
            code=code,
            message=msg,
            details=errors_str,
            timestamp=get_current_timestamp()
        )
    )
    return JSONResponse(status_code=status.HTTP_400_BAD_REQUEST, content=payload.model_dump())


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handles general Starlette / FastAPI HTTPExceptions."""
    logger.warning(f"HTTPException {exc.status_code}: {exc.detail}")
    code = "NOT_FOUND" if exc.status_code == 404 else ("METHOD_NOT_ALLOWED" if exc.status_code == 405 else "HTTP_ERROR")
    payload = ErrorResponse(
        success=False,
        message=str(exc.detail),
        detail=str(exc.detail),
        error=ErrorDetails(
            code=code,
            message=str(exc.detail),
            details=None,
            timestamp=get_current_timestamp()
        )
    )
    return JSONResponse(status_code=exc.status_code, content=payload.model_dump())


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Fallback handler for unhandled internal errors."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    msg = "An unexpected server error occurred during inference."
    payload = ErrorResponse(
        success=False,
        message=msg,
        detail=msg,
        error=ErrorDetails(
            code="INTERNAL_SERVER_ERROR",
            message=msg,
            details=str(exc) if settings.ENVIRONMENT == "development" else None,
            timestamp=get_current_timestamp()
        )
    )
    return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content=payload.model_dump())


# Routes

@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_frontend():
    """Serve the web frontend index.html."""
    index_path = FRONTEND_DIR / "index.html"
    if index_path.exists():
        return FileResponse(str(index_path), media_type="text/html")
    return HTMLResponse("<h1>AI Farmer Assistant</h1><p>Frontend not found.</p>", status_code=200)

@app.get(
    "/health",
    response_model=HealthResponse,
    summary="Health and Service Diagnostics",
    description="Returns runtime status, loaded model version, execution device, and supported class count."
)
async def health_check():
    """Health check endpoint. Distinguishes between server running and model loaded."""
    try:
        classifier = get_classifier()
        model_loaded = classifier is not None and getattr(classifier, "model", None) is not None
    except Exception:
        classifier = None
        model_loaded = False

    if model_loaded and classifier is not None:
        return HealthResponse(
            status="healthy",
            model_loaded=True,
            model_version=classifier.model_version,
            device=str(classifier.device),
            supported_classes=classifier.num_classes,
            environment=settings.ENVIRONMENT,
            timestamp=get_current_timestamp()
        )
    return HealthResponse(
        status="degraded",
        model_loaded=False,
        model_version=None,
        device=None,
        supported_classes=None,
        environment=settings.ENVIRONMENT,
        timestamp=get_current_timestamp()
    )


# Authentication Routes

@app.post(
    "/auth/register",
    response_model=AuthResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account"
)
async def register_user(
    payload: UserRegisterRequest,
    db: Session = Depends(get_db)
):
    """
    Registers a new user account with secure Argon2id password hashing.
    Normalizes email and validates credentials without creating an automatic session.
    """
    clean_email = payload.email.strip().lower()
    clean_name = payload.get_clean_name()

    # 1. Reject duplicate email addresses
    existing_user = db.query(User).filter(User.email == clean_email).first()
    if existing_user:
        raise APIError(
            status_code=status.HTTP_409_CONFLICT,
            code="EMAIL_ALREADY_EXISTS",
            message="An account with this email address already exists."
        )

    # 2. Hash password securely
    pwd_hash = hash_password(payload.password)

    # 3. Create user in database
    new_user = User(
        full_name=clean_name,
        email=clean_email,
        password_hash=pwd_hash,
        preferred_language=payload.preferred_language or "en",
        is_active=True
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return AuthResponse(
        success=True,
        message="Account registered successfully. Please sign in.",
        user=UserPublic.model_validate(new_user)
    )


@app.post(
    "/auth/login",
    response_model=AuthResponse,
    summary="User login with session cookie creation"
)
async def login_user(
    payload: UserLoginRequest,
    response: Response,
    db: Session = Depends(get_db)
):
    """
    Authenticates user credentials, sets an HttpOnly session cookie,
    and returns a safe user profile.
    """
    clean_email = payload.email.strip().lower()

    # 1. Fetch user by email
    user = db.query(User).filter(User.email == clean_email).first()
    if not user or not verify_password(payload.password, user.password_hash):
        # Generic message avoids user enumeration
        raise APIError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="INVALID_CREDENTIALS",
            message="Invalid email or password."
        )

    # 2. Reject inactive accounts
    if not user.is_active:
        raise APIError(
            status_code=status.HTTP_401_UNAUTHORIZED,
            code="USER_INACTIVE",
            message="Account is deactivated. Please contact support."
        )

    # 3. Create persistent server session
    session = create_user_session(db, user)

    # 4. Attach HttpOnly session cookie and CSRF cookie
    set_auth_cookies(response, session)

    return AuthResponse(
        success=True,
        message="Login successful.",
        user=UserPublic.model_validate(user)
    )


@app.post(
    "/auth/logout",
    summary="User logout and session invalidation"
)
async def logout_user(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    """Invalidates the authenticated session and clears session cookies."""
    token = extract_session_token(request)
    if token:
        revoke_user_session(db, token)
    clear_auth_cookies(response)
    return {"success": True, "message": "Logged out successfully."}


@app.get(
    "/auth/me",
    response_model=UserPublic,
    summary="Get current authenticated user profile"
)
async def get_me(current_user: User = Depends(get_current_active_user)):
    """Returns safe user object for current authenticated session."""
    return UserPublic.model_validate(current_user)


@app.get(
    "/users/me/preferences",
    response_model=UserPreferencesResponse,
    summary="Get user UI preferences"
)
async def get_preferences(current_user: User = Depends(get_current_active_user)):
    """Returns user's saved UI preferences."""
    return UserPreferencesResponse(language=current_user.preferred_language)


@app.put(
    "/users/me/preferences",
    response_model=UserPreferencesResponse,
    summary="Update user UI preferences"
)
async def update_preferences(
    payload: UserPreferencesRequest,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Updates user's preferred language in database."""
    current_user.preferred_language = payload.language
    db.commit()
    return UserPreferencesResponse(language=current_user.preferred_language)


@app.post(
    "/predict",
    response_model=PredictionResponse,
    responses={
        400: {"model": ErrorResponse, "description": "Missing or empty image file"},
        401: {"model": ErrorResponse, "description": "Authentication required or session expired"},
        403: {"model": ErrorResponse, "description": "CSRF validation failed"},
        413: {"model": ErrorResponse, "description": "File exceeds maximum upload size (10 MB)"},
        415: {"model": ErrorResponse, "description": "Unsupported media format"},
        422: {"model": ErrorResponse, "description": "Corrupted or invalid image bytes"},
        500: {"model": ErrorResponse, "description": "Internal server fault"},
        503: {"model": ErrorResponse, "description": "Model unavailable or uninitialized"}
    },
    summary="Plant Leaf Disease Prediction & Treatment Advisory (Protected)",
    description="Accepts a leaf photograph via multipart/form-data (field 'image' or 'file'), classifies crop and disease, and returns treatment recommendations. Requires authentication."
)
async def predict_crop_disease(
    image: Optional[UploadFile] = File(None, description="Plant leaf photograph (field 'image' per frontend contract)"),
    file: Optional[UploadFile] = File(None, description="Plant leaf photograph (field 'file' for backward compatibility)"),
    confidence_threshold: Optional[float] = Query(
        None,
        ge=0.0,
        le=1.0,
        description="Optional confidence threshold override (default: 0.60)"
    ),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Main prediction and recommendation endpoint.
    Requires a valid authenticated session.
    Accepts image under field 'image' (frontend) or 'file' (compatibility).
    """
    # 1. Validate file presence
    upload_file = image or file
    if not upload_file or not upload_file.filename:
        raise APIError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="MISSING_FILE",
            message="No image file was provided in the request."
        )

    # 2. Check file extension
    file_ext = Path(upload_file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise APIError(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            code="UNSUPPORTED_MEDIA_TYPE",
            message="Unsupported file format. Please upload a JPEG, PNG, or WebP image.",
            details=f"Received file extension: '{file_ext}'"
        )

    # 3. Check content type (if supplied)
    if upload_file.content_type and upload_file.content_type != "application/octet-stream":
        content_type_clean = upload_file.content_type.split(";")[0].strip().lower()
        if content_type_clean not in settings.ALLOWED_MIME_TYPES:
            raise APIError(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                code="UNSUPPORTED_MEDIA_TYPE",
                message="Unsupported file format. Please upload a JPEG, PNG, or WebP image.",
                details=f"Received MIME type: '{upload_file.content_type}'"
            )

    # 4. Read file content safely
    try:
        contents = await upload_file.read()
    except Exception as e:
        raise APIError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="READ_ERROR",
            message="Failed to read uploaded file stream.",
            details=str(e)
        )

    # 5. Check empty file (0 bytes)
    if len(contents) == 0:
        raise APIError(
            status_code=status.HTTP_400_BAD_REQUEST,
            code="EMPTY_FILE",
            message="The uploaded file is empty (0 bytes)."
        )

    # 6. Check maximum upload size (10 MB)
    if len(contents) > settings.MAX_UPLOAD_SIZE:
        max_mb = settings.MAX_UPLOAD_SIZE / (1024 * 1024)
        raise APIError(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            code="FILE_TOO_LARGE",
            message=f"Uploaded file exceeds maximum allowed limit of {int(max_mb)} MB.",
            details=f"Uploaded size: {len(contents)} bytes"
        )

    # 7. Validate image raster and decode PIL Image
    try:
        # Step A: integrity verify and format detection
        stream = io.BytesIO(contents)
        verify_img = Image.open(stream)
        detected_format = verify_img.format
        verify_img.verify()

        if detected_format not in ("JPEG", "PNG", "WEBP"):
            raise APIError(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                code="UNSUPPORTED_MEDIA_TYPE",
                message="Unsupported image content format. Please upload a JPEG, PNG, or WebP image.",
                details=f"Detected image format: '{detected_format}'"
            )

        # Step B: load pixel data
        stream.seek(0)
        pil_img = Image.open(stream)
        pil_img.load()
    except APIError:
        raise
    except Exception as e:
        raise APIError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="CORRUPTED_IMAGE",
            message="The uploaded file cannot be decoded as a valid image.",
            details=str(e)
        )

    # 8. Check image dimensions
    if pil_img.width <= 0 or pil_img.height <= 0:
        raise APIError(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            code="INVALID_IMAGE_DIMENSIONS",
            message="Image dimensions must be greater than zero.",
            details=f"Dimensions: {pil_img.size}"
        )

    # 9. Verify model availability & execute ML Inference
    try:
        classifier = get_classifier()
        if classifier is None or getattr(classifier, "model", None) is None:
            raise RuntimeError("Model classifier is not loaded.")
    except Exception as e:
        logger.error(f"Model unavailable: {e}", exc_info=True)
        raise APIError(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            code="MODEL_NOT_READY",
            message="Machine learning model is currently not loaded or unavailable.",
            details=str(e)
        )

    try:
        inference_result = classifier.predict(pil_img, raise_on_error=True)
    except Exception as e:
        logger.error(f"Inference failure: {e}", exc_info=True)
        raise APIError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="INFERENCE_FAILED",
            message="Failed to execute machine learning model inference.",
            details=str(e)
        )

    confidence = inference_result["confidence"]
    raw_disease = inference_result["disease"]
    model_version = inference_result["model_version"]

    # 10. Query Authoritative Treatment Knowledge Base
    advisor = get_advisor()
    treatment_raw = advisor.get_treatment(raw_disease)

    # 11. Low-Confidence Evaluation (< threshold)
    active_threshold = confidence_threshold if confidence_threshold is not None else settings.CONFIDENCE_THRESHOLD
    is_low_confidence = confidence < active_threshold

    if is_low_confidence:
        display_disease = "Low Confidence / Unverified"
        display_crop = treatment_raw.get("crop", "Tomato")
        treatment_payload = TreatmentDetails(
            status="low_confidence",
            disease_key=raw_disease,
            disease_name=f"Low Confidence ({treatment_raw.get('disease_name', 'Unidentified')})",
            crop=display_crop,
            pathogen_or_cause=f"Prediction probability ({round(confidence * 100, 1)}%) below diagnostic threshold ({round(active_threshold * 100, 1)}%).",
            summary=treatment_raw.get("summary", "Prediction confidence is below the diagnostic threshold. Retake photo with clear lighting."),
            symptoms=[
                "The photograph does not exhibit sufficiently clear hallmark disease symptoms.",
                "Image may be out of focus, taken in poor lighting, or displaying non-pathogenic abiotic stress."
            ],
            preventive_measures=[
                "Retake the photo in bright, natural daylight against a neutral background.",
                "Capture an individual leaf filling at least 60% of the frame."
            ],
            cultural_practices=[
                "Inspect both upper and lower leaf surfaces with a 10x hand lens.",
                "Consult local agricultural extension agents before taking corrective action."
            ],
            organic_treatment=[
                "Do not apply remedial treatments without confirmed diagnosis."
            ],
            chemical_treatment=[
                "Do NOT apply chemical pesticides on unconfirmed diagnoses. Misapplication can harm crops and beneficial insects."
            ],
            safety_warning="Applying pesticides without positive identification risks phytotoxicity, wasted input costs, and pollinator damage.",
            source="AI Farmer Assistant Diagnostic Confidence Safety Protocol"
        )
    else:
        display_disease = treatment_raw["disease_name"]
        display_crop = treatment_raw["crop"]
        treatment_payload = TreatmentDetails(**treatment_raw)

    # 12. Persist analysis record to database for authenticated user
    analysis_record = Analysis(
        user_id=current_user.id,
        crop=display_crop,
        disease_code=raw_disease,
        disease_name=display_disease,
        confidence=round(confidence, 4),
        model_version=model_version,
        image_url=None,
        created_at=utcnow()
    )
    try:
        db.add(analysis_record)
        db.commit()
        db.refresh(analysis_record)
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to persist analysis record: {e}", exc_info=True)
        raise APIError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="DATABASE_ERROR",
            message="Failed to save analysis record.",
            details="Internal database error while saving prediction record."
        )

    created_iso = analysis_record.created_at.isoformat() if hasattr(analysis_record.created_at, "isoformat") else get_current_timestamp()

    return PredictionResponse(
        success=True,
        analysis_id=str(analysis_record.id),
        crop=display_crop,
        disease_code=raw_disease,
        disease=display_disease,
        confidence=round(confidence, 4),
        treatment=treatment_payload,
        model_version=model_version,
        low_confidence=is_low_confidence,
        is_low_confidence=is_low_confidence,
        created_at=created_iso,
        image_url=None
    )


# =====================================================================
# Analysis History Endpoints
# =====================================================================

@app.get(
    "/history",
    response_model=HistoryListResponse,
    tags=["Analysis History"],
    summary="Retrieve paginated history of user crop disease analyses"
)
async def list_user_history(
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    offset: int = Query(0, ge=0, description="Pagination offset"),
    page: Optional[int] = Query(None, ge=1, description="Page number (1-based, frontend compatibility)"),
    page_size: Optional[int] = Query(None, ge=1, le=100, description="Page size (frontend compatibility)"),
    crop: Optional[str] = Query(None, description="Filter by crop name"),
    search: Optional[str] = Query(None, description="Search query across disease name or crop"),
    sort: Optional[str] = Query("newest", description="Sort order: 'newest' or 'oldest'"),
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Returns historical crop disease analyses for the authenticated user.
    Enforces user isolation: users can only view their own history records.
    """
    # Calculate effective pagination (supports both limit/offset and page/page_size)
    if page is not None and page_size is not None:
        effective_limit = page_size
        effective_offset = (page - 1) * page_size
    elif page_size is not None:
        effective_limit = page_size
        effective_offset = offset
    elif page is not None:
        effective_limit = limit
        effective_offset = (page - 1) * limit
    else:
        effective_limit = limit
        effective_offset = offset

    # Base query restricted strictly to current authenticated user
    query = db.query(Analysis).filter(Analysis.user_id == current_user.id)

    # Optional crop filter
    if crop and crop.strip():
        query = query.filter(Analysis.crop.ilike(f"%{crop.strip()}%"))

    # Optional search filter
    if search and search.strip():
        s = f"%{search.strip()}%"
        query = query.filter((Analysis.disease_name.ilike(s)) | (Analysis.crop.ilike(s)) | (Analysis.disease_code.ilike(s)))

    # Total matching records
    total_count = query.count()

    # Sorting
    if sort == "oldest":
        query = query.order_by(Analysis.created_at.asc(), Analysis.id.asc())
    else:
        query = query.order_by(Analysis.created_at.desc(), Analysis.id.desc())

    records = query.offset(effective_offset).limit(effective_limit).all()

    items = []
    for r in records:
        created_str = r.created_at.isoformat() if hasattr(r.created_at, "isoformat") else str(r.created_at)
        items.append(
            HistoryItem(
                analysis_id=str(r.id),
                id=r.id,
                crop=r.crop,
                disease_code=r.disease_code,
                disease=r.disease_name,
                disease_name=r.disease_name,
                confidence=r.confidence,
                created_at=created_str,
                model_version=r.model_version,
                image_url=r.image_url
            )
        )

    computed_page = (effective_offset // effective_limit) + 1 if effective_limit > 0 else 1

    return HistoryListResponse(
        items=items,
        total=total_count,
        limit=effective_limit,
        offset=effective_offset,
        page=computed_page,
        page_size=effective_limit
    )


@app.get(
    "/history/{analysis_id}",
    response_model=HistoryItem,
    tags=["Analysis History"],
    summary="Retrieve a single analysis record by ID"
)
async def get_single_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Returns a single analysis record by ID.
    Enforces authorization: returns 404 if record doesn't exist or belongs to another user.
    """
    record = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()

    if not record:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ANALYSIS_NOT_FOUND",
            message="Analysis record not found."
        )

    created_str = record.created_at.isoformat() if hasattr(record.created_at, "isoformat") else str(record.created_at)
    return HistoryItem(
        analysis_id=str(record.id),
        id=record.id,
        crop=record.crop,
        disease_code=record.disease_code,
        disease=record.disease_name,
        disease_name=record.disease_name,
        confidence=record.confidence,
        created_at=created_str,
        model_version=record.model_version,
        image_url=record.image_url
    )


@app.delete(
    "/history/{analysis_id}",
    response_model=HistoryDeleteResponse,
    tags=["Analysis History"],
    summary="Delete a single analysis record by ID"
)
async def delete_single_analysis(
    analysis_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """
    Deletes a single analysis record by ID.
    Enforces authorization & CSRF protection: returns 404 if record doesn't exist or belongs to another user.
    """
    record = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()

    if not record:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="ANALYSIS_NOT_FOUND",
            message="Analysis record not found."
        )

    try:
        db.delete(record)
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete analysis record: {e}", exc_info=True)
        raise APIError(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            code="DATABASE_ERROR",
            message="Failed to delete analysis record.",
            details="Internal database error while deleting analysis record."
        )

    return HistoryDeleteResponse(
        success=True,
        message="Analysis record deleted successfully.",
        analysis_id=str(analysis_id)
    )


# =====================================================================
# Disease Information Catalogue Endpoints
# =====================================================================

@app.get(
    "/diseases",
    response_model=DiseaseCatalogueResponse,
    tags=["Disease Information"],
    summary="Retrieve supported crop disease and condition catalogue",
    description="Returns catalogue of all 13 supported crop diseases and healthy conditions with search, crop filtering, and multilingual support (en, hi, mr)."
)
async def list_diseases(
    request: Request,
    search: Optional[str] = Query(None, description="Search across disease name, crop, category, or symptoms"),
    crop: Optional[str] = Query(None, description="Filter by crop name ('potato' or 'tomato')"),
    language: Optional[str] = Query(None, description="Language code ('en', 'hi', 'mr')")
):
    """
    Returns the catalogue of all 13 supported crop diseases and conditions.
    Supports search, crop filtering, and multilingual content (en, hi, mr).
    """
    catalog_svc = get_catalog_service()
    effective_lang = catalog_svc.resolve_language(language, request.headers.get("accept-language"))
    items = catalog_svc.list_diseases(
        language=effective_lang,
        search=search,
        crop=crop
    )
    return DiseaseCatalogueResponse(
        items=[DiseaseItem(**item) for item in items],
        total=len(items),
        language=effective_lang
    )


@app.get(
    "/diseases/{disease_code}",
    response_model=DiseaseItem,
    responses={
        404: {"model": ErrorResponse, "description": "Disease not found in catalogue"}
    },
    tags=["Disease Information"],
    summary="Retrieve detailed information for a specific disease or condition",
    description="Returns detailed diagnostic, preventative, cultural, and management guidance for a supported disease code."
)
async def get_disease_detail(
    disease_code: str,
    request: Request,
    language: Optional[str] = Query(None, description="Language code ('en', 'hi', 'mr')")
):
    """
    Retrieves full details for a supported disease or healthy leaf condition by code.
    Returns 404 for unknown codes.
    """
    catalog_svc = get_catalog_service()
    effective_lang = catalog_svc.resolve_language(language, request.headers.get("accept-language"))
    item = catalog_svc.get_disease(disease_code, language=effective_lang)

    if not item:
        raise APIError(
            status_code=status.HTTP_404_NOT_FOUND,
            code="DISEASE_NOT_FOUND",
            message=f"Disease '{disease_code}' was not found in the catalogue.",
            details=f"Supported disease codes: {', '.join(catalog_svc.list_supported_codes())}"
        )

    return DiseaseItem(**item)


