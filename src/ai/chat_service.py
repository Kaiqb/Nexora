from __future__ import annotations
from typing import Dict, Any, Optional

from .config import settings
from .llm_service import LLMService
from .nlu_service import NLUService

class ChatService:
    """
    Coordinates LLM and NLU services to handle business registration chat flow
    """
    def __init__(self, llm: Optional[LLMService] = None, nlu: Optional[NLUService] = None):
        self.llm = llm or LLMService()
        self.nlu = nlu or NLUService()

    async def process_registration_request(self, user_message: str) -> Dict[str, Any]:
        """Process user message and return structured response with entities and LLM confirmation"""
        
        # Extract entities using NLU
        entities = await self.nlu.extract_entities(user_message)
        
        # Build prompt for LLM confirmation
        prompt = (
            "You are a helpful business registration assistant. "
            "Based on the following request and extracted entities, "
            "generate a single clear confirmation sentence starting with 'I'll help you'.\n\n"
            f"User request: {user_message}\n"
            f"Extracted entities: {entities}\n\n"
            "Response (one sentence):"
        )
        
        # Generate confirmation using LLM
        confirmation = await self.llm.generate(prompt)
        
        # Determine next step based on extracted entities
        if entities.get("business_type") and entities.get("state_code"):
            suggested_next = "proceed_to_registration_form"
        elif not entities.get("business_type"):
            suggested_next = "ask_for_business_type"
        elif not entities.get("state_code"):
            suggested_next = "ask_for_state"
        else:
            suggested_next = "collect_missing_info"
        
        return {
            "original_message": user_message,
            "entities": entities,
            "confirmation": confirmation.strip(),
            "suggested_next": suggested_next
        }