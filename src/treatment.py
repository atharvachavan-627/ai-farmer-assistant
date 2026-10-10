"""
Treatment recommendation module for AI Farmer Assistant.

Decouples agricultural treatment knowledge base from application logic.
Maps (crop + disease) class keys to structured agronomic guidance.
"""

from pathlib import Path
from typing import Dict, Any, List, Optional
import json

# Project root path resolution
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_KB_PATH = PROJECT_ROOT / "data" / "treatment_recommendations.json"


class TreatmentAdvisor:
    """
    Authoritative treatment recommendation service.
    """
    def __init__(self, knowledge_base_path: Optional[Path] = None):
        self.kb_path = Path(knowledge_base_path) if knowledge_base_path else DEFAULT_KB_PATH
        if not self.kb_path.exists():
            raise FileNotFoundError(f"Treatment knowledge base file not found at: {self.kb_path}")
        
        with open(self.kb_path, "r", encoding="utf-8") as f:
            self._knowledge_base: Dict[str, Dict[str, Any]] = json.load(f)

    def list_supported_diseases(self) -> List[str]:
        """Returns the list of all supported disease class identifiers."""
        return sorted(list(self._knowledge_base.keys()))

    def _resolve_entry(self, crop_or_key: Optional[str], disease: Optional[str] = None) -> Optional[str]:
        """Resolves inputs (either 'Crop___Disease' key or separate crop + disease) to a valid KB key."""
        if crop_or_key is None and disease is None:
            return None

        clean_key = str(crop_or_key).strip() if crop_or_key is not None else ""
        clean_disease = str(disease).strip() if disease is not None else ""

        # 1. Direct key match (e.g. 'Potato___Early_blight')
        if not clean_disease and clean_key in self._knowledge_base:
            return clean_key

        # 2. Combined key string formed from crop and disease
        if clean_disease:
            candidate_key = f"{clean_key}___{clean_disease}"
            if candidate_key in self._knowledge_base:
                return candidate_key

            # Normalize and search entries
            crop_lower = clean_key.lower()
            disease_norm = clean_disease.lower().replace(" ", "_").replace("-", "_")

            for key, entry in self._knowledge_base.items():
                entry_crop = entry["crop"].lower()
                entry_name_norm = entry["disease_name"].lower().replace(" ", "_").replace("-", "_")
                key_norm = key.lower().replace("-", "_")

                if entry_crop == crop_lower:
                    if (disease_norm in entry_name_norm or
                        entry_name_norm in disease_norm or
                        disease_norm in key_norm):
                        return key
        return None

    def get_treatment(self, disease_or_crop: Optional[str] = None, disease: Optional[str] = None) -> Dict[str, Any]:
        """
        Retrieves treatment recommendation for a given disease class key or (crop, disease) pair.
        
        Guarantees consistent schema for both supported and unknown/malformed inputs.
        Never crashes on invalid input.
        """
        resolved_key = self._resolve_entry(disease_or_crop, disease)

        # Case 1: Known supported disease in knowledge base
        if resolved_key and resolved_key in self._knowledge_base:
            entry = self._knowledge_base[resolved_key]
            if "healthy" in resolved_key.lower():
                summary = f"{entry['crop']} foliage shows no visible signs of pathogen infection and appears healthy."
            else:
                summary = f"{entry['crop']} affected by {entry['disease_name']} ({entry['pathogen_or_cause']})."
            return {
                "status": "success",
                "disease_key": resolved_key,
                "disease_name": entry["disease_name"],
                "crop": entry["crop"],
                "pathogen_or_cause": entry["pathogen_or_cause"],
                "summary": summary,
                "symptoms": list(entry["symptoms"]),
                "preventive_measures": list(entry["preventive_measures"]),
                "cultural_practices": list(entry["cultural_practices"]),
                "organic_treatment": list(entry["organic_treatment"]),
                "chemical_treatment": list(entry["chemical_treatment"]),
                "safety_warning": entry["safety_warning"],
                "source": entry["source"]
            }

        # Case 2: Unknown or malformed disease key (safe fallback response)
        raw_repr = f"{disease_or_crop} + {disease}" if (disease_or_crop and disease) else str(disease_or_crop or "unknown").strip()
        crop_hint = "Tomato" if "tomato" in raw_repr.lower() else ("Potato" if "potato" in raw_repr.lower() else "Unknown")
        return {
            "status": "unknown_disease",
            "disease_key": raw_repr or "unknown",
            "disease_name": "Unidentified Condition",
            "crop": crop_hint,
            "pathogen_or_cause": "Unconfirmed or unsupported disease category",
            "summary": "Unidentified condition or unsupported crop disease class. Professional agronomic inspection recommended.",
            "symptoms": [
                "Symptoms could not be verified against the 13 supported crop disease classes.",
                "Leaf may exhibit non-target biotic stress, abiotic nutrient deficiency, or physical damage."
            ],
            "preventive_measures": [
                "Submit physical leaf samples to a local university plant pathology diagnostic laboratory.",
                "Consult certified agricultural extension agents before taking remedial action."
            ],
            "cultural_practices": [
                "Isolate affected plants if transmissible disease is suspected.",
                "Avoid overhead irrigation to minimize leaf moisture.",
                "Sanitize pruning tools and wash hands before handling healthy rows."
            ],
            "organic_treatment": [
                "Do not apply unverified organic formulations without a positive diagnosis."
            ],
            "chemical_treatment": [
                "No chemical treatment recommended without verified diagnostic confirmation.",
                "Avoid unguided pesticide application to protect beneficial insects and crop health."
            ],
            "safety_warning": "Improper chemical pesticide applications can cause phytotoxicity, destroy beneficial pollinators, and contaminate soil and water. Always obtain verified agronomist diagnosis and follow product labels strictly.",
            "source": "AI Farmer Assistant Expert Agricultural Advisory Protocol"
        }

    def get_treatment_by_crop_and_disease(self, crop: Optional[str], disease: Optional[str]) -> Dict[str, Any]:
        """
        Maps (crop, disease) explicitly to structured treatment information.
        Accepts crop name (e.g., 'Tomato', 'Potato') and disease identifier or name.
        """
        return self.get_treatment(crop, disease)


# Global singleton instance for clean imports
_default_advisor: Optional[TreatmentAdvisor] = None


def get_advisor() -> TreatmentAdvisor:
    """Returns a cached global TreatmentAdvisor instance."""
    global _default_advisor
    if _default_advisor is None:
        _default_advisor = TreatmentAdvisor()
    return _default_advisor


def get_treatment_recommendation(disease_or_crop: Optional[str] = None, disease: Optional[str] = None) -> Dict[str, Any]:
    """Convenience helper function to retrieve treatment recommendation by key or crop+disease."""
    return get_advisor().get_treatment(disease_or_crop, disease)

