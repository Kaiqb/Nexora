from __future__ import annotations
import re
import asyncio
from typing import Dict, Any, Optional
from functools import lru_cache

import spacy
from spacy.pipeline import EntityRuler

from .config import settings

# US states mapping for normalization
US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT",
    "nebraska": "NE", "nevada": "NV", "new hampshire": "NH",
    "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH",
    "oklahoma": "OK", "oregon": "OR", "pennsylvania": "PA",
    "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT",
    "virginia": "VA", "washington": "WA", "west virginia": "WV",
    "wisconsin": "WI", "wyoming": "WY", "district of columbia": "DC"
}

@lru_cache(maxsize=1)
def _compile_regexes():
    """Compile and cache regex patterns"""
    return {
        "ein": re.compile(r"\b\d{2}-\d{7}\b"),
        "phone": re.compile(r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b"),
        "email": re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
    }

class NLUService:
    """NLU service to extract business-registration-specific entities"""

    def __init__(self, spacy_model: Optional[str] = None):
        self.spacy_model_name = spacy_model or settings.SPACY_MODEL
        self._nlp = None
        self._ruler_added = False
        self._regex = _compile_regexes()

    def _ensure_nlp(self):
        """Lazy load spaCy model and add custom entity patterns"""
        if self._nlp is not None:
            return

        self._nlp = spacy.load(self.spacy_model_name)

        # Add entity ruler if not present
        if "entity_ruler" not in self._nlp.pipe_names:
            ruler = self._nlp.add_pipe("entity_ruler", before="ner")
        else:
            ruler = self._nlp.get_pipe("entity_ruler")

        if not self._ruler_added:
            patterns = [
                {"label": "BUSINESS_TYPE", "pattern": [{"LOWER": "llc"}]},
                {"label": "BUSINESS_TYPE", "pattern": [{"LOWER": "limited"}, {"LOWER": "liability"}, {"LOWER": "company"}]},
                {"label": "BUSINESS_TYPE", "pattern": [{"LOWER": "corporation"}]},
                {"label": "BUSINESS_TYPE", "pattern": [{"LOWER": "inc"}]},
                {"label": "BUSINESS_TYPE", "pattern": [{"LOWER": "partnership"}]},
                {"label": "BUSINESS_TYPE", "pattern": [{"LOWER": "sole"}, {"LOWER": "proprietor"}]},
            ]
            ruler.add_patterns(patterns)
            self._ruler_added = True

    async def extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract structured entities from free text"""
        await asyncio.to_thread(self._ensure_nlp)
        doc = await asyncio.to_thread(self._nlp, text)

        result = {
            "business_type": None,
            "business_name": None,
            "owner_name": None,
            "address": None,
            "state": None,
            "state_code": None,
            "ein": None,
            "email": None,
            "phone": None,
            "formation_date": None,
            "raw_entities": []
        }

        # Process spaCy entities
        for ent in doc.ents:
            label = ent.label_
            text_val = ent.text.strip()
            result["raw_entities"].append({"text": text_val, "label": label})

            if label == "BUSINESS_TYPE" or (
                label == "ORG" and 
                result["business_type"] is None and 
                any(k in text_val.lower() for k in ("llc", "corporation", "inc", "corp"))
            ):
                if "llc" in text_val.lower():
                    result["business_type"] = "LLC"
                elif any(x in text_val.lower() for x in ("corporation", "corp", "inc")):
                    result["business_type"] = "Corporation"
                else:
                    result["business_type"] = text_val
            elif label == "ORG" and result["business_name"] is None:
                result["business_name"] = text_val
            elif label == "PERSON" and result["owner_name"] is None:
                result["owner_name"] = text_val
            elif label in ("GPE", "LOC") and result["state"] is None:
                # Try to identify state
                normalized = self._normalize_state(text_val)
                if normalized:
                    result["state"], result["state_code"] = normalized

        # Apply regex extractors
        for field, pattern in self._regex.items():
            if result[field] is None:  # Don't override if already found
                match = pattern.search(text)
                if match:
                    result[field] = match.group(0)

        return result

    def _normalize_state(self, text: str) -> Optional[tuple[str, str]]:
        """Convert state name/abbreviation to (full_name, code) tuple"""
        if not text:
            return None
        
        text = text.strip().lower()
        
        # Direct code match
        if len(text) == 2 and text.upper() in US_STATES.values():
            code = text.upper()
            full = next((name.title() for name, c in US_STATES.items() if c == code), code)
            return (full, code)
            
        # Full name match
        if text in US_STATES:
            return (text.title(), US_STATES[text])
            
        return None