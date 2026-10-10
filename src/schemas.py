"""
Pydantic Schemas for AI Farmer Assistant API.

Aligns strictly with the approved API Contract Specification.
"""

from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class HealthResponse(BaseModel):
    """Health and readiness diagnostics response."""
    status: str = Field(..., description="Service status", example="healthy")
    model_loaded: bool = Field(..., description="Whether model is loaded in memory", example=True)
    model_version: Optional[str] = Field(None, description="Active ML model version string", example="MobileNetV2-FineTuned-v1.0")
    device: Optional[str] = Field(None, description="Hardware execution device", example="cpu")
    supported_classes: Optional[int] = Field(None, description="Number of supported crop disease classes", example=13)
    environment: str = Field(..., description="Active server environment", example="development")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp", example="2026-10-09T00:20:00Z")


class TreatmentDetails(BaseModel):
    """Structured agronomic treatment information."""
    status: str = Field("success", description="Treatment lookup status", example="success")
    disease_key: str = Field("", description="Internal class key", example="Tomato___Early_blight")
    disease_name: str = Field("", description="Agronomic disease name", example="Early Blight")
    crop: str = Field("", description="Target crop", example="Tomato")
    pathogen_or_cause: str = Field("", description="Pathogen or causal agent", example="Alternaria linariae / Alternaria solani")
    summary: str = Field("", description="Agronomic summary of disease and recommendations", example="Tomato affected by Early Blight...")
    symptoms: List[str] = Field(default_factory=list, description="Diagnostic visual symptoms")
    preventive_measures: List[str] = Field(default_factory=list, description="Field-level preventative measures")
    cultural_practices: List[str] = Field(default_factory=list, description="Agronomic sanitation and cultural practices")
    organic_treatment: List[str] = Field(default_factory=list, description="Organic / OMRI-listed treatment strategies")
    chemical_treatment: List[str] = Field(default_factory=list, description="Evidence-backed chemical treatments without invented dosages")
    safety_warning: str = Field("", description="Mandatory safety, PPE, and environmental warning")
    source: str = Field("", description="Authoritative agricultural extension source")


class PredictionResponse(BaseModel):
    """Successful disease prediction and recommendation response."""
    success: bool = Field(True, description="Request success status", example=True)
    analysis_id: Optional[str] = Field(None, description="Analysis persistence identifier (null in current phase)", example=None)
    crop: str = Field(..., description="Identified crop", example="Tomato")
    disease_code: str = Field(..., description="Internal disease code identifier", example="Tomato___Early_blight")
    disease: str = Field(..., description="Identified disease or condition", example="Early Blight")
    confidence: float = Field(..., description="Prediction confidence probability [0, 1]", example=0.9786)
    treatment: TreatmentDetails = Field(..., description="Structured agronomic treatment data")
    model_version: str = Field(..., description="Active model version tag", example="MobileNetV2-FineTuned-v1.0")
    low_confidence: bool = Field(False, description="Flag indicating confidence below threshold (frontend compatible)", example=False)
    is_low_confidence: bool = Field(False, description="Flag indicating confidence below threshold (backward compatible)", example=False)
    created_at: Optional[str] = Field(None, description="ISO timestamp", example="2026-10-09T00:20:00Z")
    image_url: Optional[str] = Field(None, description="Image URL if stored", example=None)


class ErrorDetails(BaseModel):
    """Standardized error details."""
    code: str = Field(..., description="Machine-readable error code", example="INVALID_IMAGE_FILE")
    message: str = Field(..., description="Human-readable error description", example="The uploaded file cannot be decoded as an image.")
    details: Optional[str] = Field(None, description="Technical diagnostics or validation details")
    timestamp: str = Field(..., description="ISO 8601 UTC timestamp", example="2026-10-09T00:20:00Z")


class ErrorResponse(BaseModel):
    """Unified error response schema."""
    success: bool = Field(False, description="Request success status", example=False)
    message: Optional[str] = Field(None, description="Human-readable error message for frontend clients", example="No image file was provided in the request.")
    detail: Optional[str] = Field(None, description="Standard FastAPI detail for frontend clients", example="No image file was provided in the request.")
    error: ErrorDetails = Field(..., description="Error details payload")


import re

EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$")


class UserRegisterRequest(BaseModel):
    """User registration payload supporting both 'full_name' and 'name'."""
    full_name: Optional[str] = Field(None, description="User full name", example="Ramesh Patel")
    name: Optional[str] = Field(None, description="Frontend alias for full_name", example="Ramesh Patel")
    email: str = Field(..., description="User email address", example="ramesh@example.com")
    password: str = Field(..., min_length=8, description="Account password (min 8 characters)")
    preferred_language: Optional[str] = Field("en", description="Preferred language code ('en', 'hi', 'mr')")

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        clean = (v or "").strip().lower()
        if not EMAIL_REGEX.match(clean):
            raise ValueError("Invalid email address format.")
        return clean

    def get_clean_name(self) -> str:
        clean = (self.full_name or self.name or "").strip()
        if len(clean) < 2:
            raise ValueError("Full name must be at least 2 characters long.")
        return clean


class UserLoginRequest(BaseModel):
    """User login credentials."""
    email: str = Field(..., description="Registered email address", example="ramesh@example.com")
    password: str = Field(..., description="Account password")


class UserPublic(BaseModel):
    """Safe public user entity representation (never includes password or hashes)."""
    id: int = Field(..., description="Unique user identifier", example=1)
    full_name: str = Field(..., description="User full name", example="Ramesh Patel")
    name: Optional[str] = Field(None, description="User full name alias for frontend", example="Ramesh Patel")
    email: str = Field(..., description="Registered user email", example="ramesh@example.com")
    preferred_language: str = Field("en", description="Preferred UI language", example="en")
    is_active: bool = Field(True, description="Account active status")

    @model_validator(mode="after")
    def populate_name(self) -> "UserPublic":
        if not self.name and self.full_name:
            self.name = self.full_name
        return self

    class Config:
        from_attributes = True


class AuthResponse(BaseModel):
    """Standard authentication response."""
    success: bool = Field(True, description="Operation success status")
    message: Optional[str] = Field(None, description="Operation status description")
    user: UserPublic = Field(..., description="User profile details")


class UserPreferencesRequest(BaseModel):
    """User preference update payload."""
    language: str = Field(..., description="Preferred language ('en', 'hi', 'mr')", example="en")


class UserPreferencesResponse(BaseModel):
    """User preference response."""
    language: str = Field(..., description="Preferred language code", example="en")


class HistoryItem(BaseModel):
    """Historical disease analysis item."""
    analysis_id: str = Field(..., description="Unique analysis record identifier", example="1")
    id: Optional[int] = Field(None, description="Integer ID alias", example=1)
    crop: str = Field(..., description="Crop identified", example="Tomato")
    disease_code: str = Field(..., description="Internal disease code", example="Tomato___Early_blight")
    disease: str = Field(..., description="Disease display name", example="Early Blight")
    disease_name: Optional[str] = Field(None, description="Disease name alias", example="Early Blight")
    confidence: float = Field(..., description="Confidence score [0, 1]", example=0.9786)
    created_at: str = Field(..., description="ISO 8601 UTC timestamp", example="2026-10-10T12:00:00Z")
    model_version: str = Field(..., description="Model version used", example="MobileNetV2-FineTuned-v1.0")
    image_url: Optional[str] = Field(None, description="Image URL if persisted", example=None)


class HistoryDiseaseSummary(BaseModel):
    """Disease frequency summary."""
    disease_code: str
    disease: str
    count: int


class HistorySummary(BaseModel):
    """Optional summary metrics for history."""
    by_disease: List[HistoryDiseaseSummary] = Field(default_factory=list)


class HistoryListResponse(BaseModel):
    """Paginated list of historical user analyses."""
    items: List[HistoryItem] = Field(default_factory=list, description="List of analysis records")
    total: int = Field(..., description="Total count of matching records", example=1)
    limit: int = Field(..., description="Current page limit", example=20)
    offset: int = Field(..., description="Current offset", example=0)
    page: Optional[int] = Field(None, description="Current page number (1-based)", example=1)
    page_size: Optional[int] = Field(None, description="Page size", example=20)
    summary: Optional[HistorySummary] = Field(None, description="History statistics summary")


class HistoryDeleteResponse(BaseModel):
    """Deletion response for an analysis record."""
    success: bool = Field(True, description="Deletion success status")
    message: str = Field("Analysis record deleted successfully.", description="Status message")
    analysis_id: str = Field(..., description="Deleted analysis ID", example="1")


class DiseaseItem(BaseModel):
    """Authoritative disease or condition catalog item."""
    disease_code: str = Field(..., description="Stable disease class identifier", example="Tomato___Early_blight")
    name: str = Field(..., description="Disease or condition display name", example="Early Blight")
    crop: str = Field(..., description="Target crop", example="Tomato")
    category: str = Field(..., description="Pathogen category ('Fungal', 'Bacterial', 'Viral', 'Pest', 'Oomycete', 'Healthy')", example="Fungal")
    image_url: Optional[str] = Field(None, description="Image illustration URL if available")
    created_at: Optional[str] = Field(None, description="ISO timestamp for sorting", example="2026-09-20T09:00:00Z")
    symptoms_summary: str = Field("", description="Concise symptoms summary for card display")
    prevention_summary: str = Field("", description="Concise prevention summary for card display")
    overview: str = Field("", description="Agronomic overview and pathogen description")
    symptoms: List[str] = Field(default_factory=list, description="Diagnostic symptoms")
    favourable_conditions: List[str] = Field(default_factory=list, description="Environmental conditions favoring disease")
    preventive_measures: List[str] = Field(default_factory=list, description="Field preventative measures")
    cultural_management: List[str] = Field(default_factory=list, description="Cultural and sanitation practices")
    organic_management: List[str] = Field(default_factory=list, description="Organic and biological management options")
    chemical_treatment: List[str] = Field(default_factory=list, description="Verified chemical treatment options")
    chemical_verified: bool = Field(False, description="Whether chemical recommendations are verified")
    consult_expert: List[str] = Field(default_factory=list, description="Indicators for consulting agricultural extension agents")
    safety_warning: Optional[str] = Field("", description="Safety and PPE warning")
    source: Optional[str] = Field("", description="Authoritative agricultural source citation")
    content_language: str = Field("en", description="Content language code ('en', 'hi', 'mr')")

    # Frontend aliases for maximum client compatibility
    code: Optional[str] = Field(None, description="Frontend alias for disease_code")
    disease: Optional[str] = Field(None, description="Frontend alias for name")
    symptoms_short: Optional[str] = Field(None, description="Frontend alias for symptoms_summary")
    cultural_practices: Optional[List[str]] = Field(None, description="Alias for cultural_management")
    organic_treatment: Optional[List[str]] = Field(None, description="Alias for organic_management")

    @model_validator(mode="after")
    def populate_aliases(self) -> "DiseaseItem":
        if not self.code:
            self.code = self.disease_code
        if not self.disease:
            self.disease = self.name
        if not self.symptoms_short:
            self.symptoms_short = self.symptoms_summary
        if self.cultural_practices is None:
            self.cultural_practices = self.cultural_management
        if self.organic_treatment is None:
            self.organic_treatment = self.organic_management
        return self


class DiseaseCatalogueResponse(BaseModel):
    """Complete disease catalogue response."""
    items: List[DiseaseItem] = Field(default_factory=list, description="List of catalog diseases")
    total: int = Field(..., description="Total matching disease count", example=13)
    language: str = Field("en", description="Response content language", example="en")



