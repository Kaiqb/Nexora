from __future__ import annotations
from typing import Dict, Any, Optional

from .config import settings
from .llm_service import LLMService
from .nlu_service import NLUService
from .state_filing_service import StateFilingService

class ChatService:
    """Coordinates LLM, NLU, and state filing services"""
    
    def __init__(self, llm: Optional[LLMService] = None, nlu: Optional[NLUService] = None):
        self.llm = llm or LLMService()
        self.nlu = nlu or NLUService()

    async def process_registration_request(self, user_message: str) -> Dict[str, Any]:
        """Process user message and return structured response"""
        entities = await self.nlu.extract_entities(user_message)
        
        prompt = (
            "You are a helpful business registration assistant. "
            "Based on the following request and extracted entities, "
            "generate a single clear confirmation sentence starting with 'I'll help you'.\n\n"
            f"User request: {user_message}\n"
            f"Extracted entities: {entities}\n\n"
            "Response (one sentence):"
        )
        
        confirmation = await self.llm.generate(prompt)
        
        # Check if state is supported for filing
        state_code = entities.get("state_code")
        filing_available = StateFilingService.is_state_supported(state_code) if state_code else False
        
        if entities.get("business_type") and entities.get("state_code"):
            if filing_available:
                suggested_next = "proceed_to_registration_form"
            else:
                suggested_next = "state_not_supported_for_auto_filing"
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
            "suggested_next": suggested_next,
            "filing_available": filing_available,
            "supported_states": StateFilingService.get_supported_states() if not filing_available else None
        }
    
    async def file_with_state(
        self, 
        entities: Dict[str, Any],
        sos_username: str,
        sos_password: str
    ) -> Dict[str, Any]:
        """
        File business registration with state using extracted entities
        Works with ANY supported state dynamically
        
        Args:
            entities: Extracted entities from NLU (business_name, state_code, etc.)
            sos_username: State's Secretary of State account username
            sos_password: State's Secretary of State account password
            
        Returns:
            Filing status with success/error information
        """
        state_code = entities.get("state_code")
        
        if not state_code:
            return {
                "success": False,
                "error": "No state specified in entities"
            }
        
        # Check if state is supported
        if not StateFilingService.is_state_supported(state_code):
            supported = ", ".join(StateFilingService.get_supported_states())
            return {
                "success": False,
                "error": f"State {state_code} automation not yet supported. Supported states: {supported}"
            }
        
        # Use generic state filing service (automatically handles the specific state)
        async with StateFilingService(state_code) as filing_service:
            # Step 1: Login
            login_success = await filing_service.login(sos_username, sos_password)
            
            if not login_success:
                return {
                    "success": False,
                    "state": state_code,
                    "error": f"Login to {filing_service.state_name} SOS failed. Please check credentials."
                }
            
            # Step 2: Navigate to LLC filing
            nav_success = await filing_service.navigate_to_llc_filing()
            if not nav_success:
                return {
                    "success": False,
                    "state": state_code,
                    "error": "Failed to navigate to LLC filing page"
                }
            
            # Step 3: Fill form with extracted data
            business_data = {
                "business_name": entities.get("business_name"),
                "registered_agent_name": entities.get("owner_name"),
                "registered_agent_address": entities.get("address"),
                "purpose": "All lawful purposes"
            }
            
            fill_success = await filing_service.fill_llc_formation(business_data)
            if not fill_success:
                return {
                    "success": False,
                    "state": state_code,
                    "error": "Failed to fill LLC formation form"
                }
            
            # Step 4: Take screenshot for user review
            screenshot_path = await filing_service.take_screenshot()
            
            # Step 5: Return status (don't auto-submit, let user review)
            return {
                "success": True,
                "state": state_code,
                "state_name": filing_service.state_name,
                "logged_in": True,
                "form_filled": True,
                "ready_to_submit": True,
                "preview_screenshot": screenshot_path,
                "message": f"Form filled successfully for {filing_service.state_name}. Please review the screenshot before submitting."
            }