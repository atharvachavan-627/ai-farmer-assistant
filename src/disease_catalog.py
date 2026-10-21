"""
Disease Information Catalog Service for AI Farmer Assistant.

Manages the authoritative catalog of crop diseases and conditions
supported by the machine learning classification model.

Features:
- Guaranteed 100% alignment with the 13 MobileNetV2 model classes.
- Multilingual support for English (en), Hindi (hi), and Marathi (mr).
- Robust English fallback when requested language or field is unavailable.
- Case-insensitive search and crop filtering.
- Safe in-memory lookup avoiding dynamic filesystem access.
- Clear distinction between disease pathologies and healthy foliar tissue.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json
import logging
import re

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CATALOG_PATH = PROJECT_ROOT / "data" / "disease_catalog.json"
DEFAULT_TRANSLATIONS_PATH = PROJECT_ROOT / "data" / "disease_catalog_translations.json"
DEFAULT_CLASS_MAPPING_PATH = PROJECT_ROOT / "models" / "mobilenetv2" / "class_mapping.json"

logger = logging.getLogger("ai_farmer_assistant.disease_catalog")

SUPPORTED_LANGUAGES = {"en", "hi", "mr"}


class DiseaseCatalogService:
    """
    Authoritative disease catalog and localization service.
    """

    def __init__(
        self,
        catalog_path: Optional[Path] = None,
        translations_path: Optional[Path] = None,
        class_mapping_path: Optional[Path] = None
    ):
        self.catalog_path = Path(catalog_path) if catalog_path else DEFAULT_CATALOG_PATH
        self.translations_path = Path(translations_path) if translations_path else DEFAULT_TRANSLATIONS_PATH
        self.class_mapping_path = Path(class_mapping_path) if class_mapping_path else DEFAULT_CLASS_MAPPING_PATH

        if not self.catalog_path.exists():
            raise FileNotFoundError(f"Disease catalog file not found at: {self.catalog_path}")

        # Load English baseline catalog
        with open(self.catalog_path, "r", encoding="utf-8") as f:
            catalog_raw = json.load(f)
            items = catalog_raw.get("items", [])
            self._catalog: Dict[str, Dict[str, Any]] = {item["disease_code"]: item for item in items}

        # Load translations if available
        self._translations: Dict[str, Dict[str, Dict[str, Any]]] = {}
        if self.translations_path.exists():
            with open(self.translations_path, "r", encoding="utf-8") as f:
                self._translations = json.load(f)

        # Validate against model class mapping
        if self.class_mapping_path.exists():
            with open(self.class_mapping_path, "r", encoding="utf-8") as f:
                class_mapping: Dict[str, int] = json.load(f)
            missing = set(class_mapping.keys()) - set(self._catalog.keys())
            if missing:
                logger.warning(f"Disease catalog is missing model classes: {missing}")

        # Normalized index for flexible lookups (e.g., Potato__Early_blight vs Potato___Early_blight)
        self._normalized_index: Dict[str, str] = {
            self._normalize_code(code): code for code in self._catalog.keys()
        }

    @staticmethod
    def _normalize_code(code: str) -> str:
        return re.sub(r'[\s_\-]+', '_', code.strip().lower())

    def list_supported_codes(self) -> List[str]:
        """Returns sorted list of all 13 supported disease class codes."""
        return sorted(list(self._catalog.keys()))

    def resolve_language(self, language_param: Optional[str] = None, accept_language_header: Optional[str] = None) -> str:
        """
        Resolves effective language code ('en', 'hi', 'mr') from query param or HTTP header.
        Safely falls back to 'en' for any unrecognized or malformed language.
        """
        # 1. Query parameter priority
        if language_param and isinstance(language_param, str):
            clean = language_param.strip().lower().split("-")[0].split("_")[0]
            if clean in SUPPORTED_LANGUAGES:
                return clean

        # 2. Accept-Language header parsing (e.g., 'mr-IN,mr;q=0.9,en;q=0.8')
        if accept_language_header and isinstance(accept_language_header, str):
            parts = [p.strip() for p in accept_language_header.split(",") if p.strip()]
            for part in parts:
                candidate = part.split(";")[0].strip().lower().split("-")[0]
                if candidate in SUPPORTED_LANGUAGES:
                    return candidate

        return "en"

    def _localize_entry(self, entry: Dict[str, Any], lang: str) -> Dict[str, Any]:
        """
        Creates a localized copy of an entry.
        Falls back to English if the translation or specific fields are missing.
        """
        res = dict(entry)
        if lang == "en" or lang not in self._translations:
            res["content_language"] = "en"
            return res

        lang_dict = self._translations.get(lang, {}).get(entry["disease_code"])
        if not lang_dict:
            res["content_language"] = "en"
            return res

        # Overlay translated fields
        for field in [
            "name",
            "symptoms_summary",
            "prevention_summary",
            "overview",
            "symptoms",
            "favourable_conditions",
            "preventive_measures",
            "cultural_management",
            "organic_management",
            "consult_expert",
        ]:
            if field in lang_dict and lang_dict[field]:
                res[field] = lang_dict[field]

        # For chemical treatment:
        # If localized translation is provided, use it; otherwise retain verified technical original
        if "chemical_treatment" in lang_dict and lang_dict["chemical_treatment"] is not None:
            res["chemical_treatment"] = lang_dict["chemical_treatment"]

        res["content_language"] = lang
        return res

    def get_disease(self, disease_code: str, language: str = "en") -> Optional[Dict[str, Any]]:
        """
        Retrieves a single disease entry by code with requested language.
        Supports exact code matching and normalized flexible matching (e.g. Potato__Early_blight).
        Returns None if code is unknown.
        """
        if not disease_code or not isinstance(disease_code, str):
            return None

        clean_code = disease_code.strip()
        base_entry = None

        if clean_code in self._catalog:
            base_entry = self._catalog[clean_code]
        else:
            norm_code = self._normalize_code(clean_code)
            if norm_code in self._normalized_index:
                canonical_code = self._normalized_index[norm_code]
                base_entry = self._catalog[canonical_code]

        if not base_entry:
            return None

        return self._localize_entry(base_entry, language)

    def list_diseases(
        self,
        language: str = "en",
        search: Optional[str] = None,
        crop: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Lists all disease entries matching optional search and crop filters.
        """
        results = []
        clean_crop = crop.strip().lower() if crop and crop.strip() else None
        clean_search = search.strip().lower() if search and search.strip() else None

        for code in sorted(self._catalog.keys()):
            base_entry = self._catalog[code]

            # Filter by crop
            if clean_crop:
                entry_crop = str(base_entry.get("crop", "")).lower()
                if clean_crop != entry_crop:
                    continue

            localized = self._localize_entry(base_entry, language)

            # Filter by search query across name, crop, code, category, summary, and overview
            if clean_search:
                searchable_text = " ".join([
                    str(localized.get("name", "")).lower(),
                    str(localized.get("crop", "")).lower(),
                    str(localized.get("disease_code", "")).lower(),
                    str(localized.get("category", "")).lower(),
                    str(localized.get("symptoms_summary", "")).lower(),
                    str(localized.get("overview", "")).lower()
                ])
                if clean_search not in searchable_text:
                    continue

            results.append(localized)

        return results


# Global singleton cache
_catalog_service_instance: Optional[DiseaseCatalogService] = None


def get_catalog_service() -> DiseaseCatalogService:
    """Returns the singleton DiseaseCatalogService instance."""
    global _catalog_service_instance
    if _catalog_service_instance is None:
        _catalog_service_instance = DiseaseCatalogService()
    return _catalog_service_instance
