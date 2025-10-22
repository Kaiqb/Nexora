from __future__ import annotations
from typing import Dict, Any, Optional
import logging

from .config import settings
from .llm_service import LLMService
from .nlu_service import NLUService
from .state_filing_service import StateFilingService

class ChatService:
    """Coordinates LLM, NLU, and state filing services for business registration"""
    
    def __init__(self, llm: Optional[LLMService] = None, nlu: Optional[NLUService] = None):
        self.llm = llm or LLMService()
        self.nlu = nlu or NLUService()

    async def process_registration_request(self, user_message: str) -> Dict[str, Any]:
        """Process user message and return structured response with filing availability"""
        try:
            # Extract entities from user message
            entities = await self.nlu.extract_entities(user_message)
            
            # Generate confirmation message using LLM
            prompt = (
                "You are a helpful business registration assistant. "
                "Based on the following request and extracted entities, "
                "generate a single clear confirmation sentence starting with 'I'll help you'.\n\n"
                f"User request: {user_message}\n"
                f"Extracted entities: {entities}\n\n"
                "Response (one sentence):"
            )
            
            confirmation = await self.llm.generate(prompt)
            
            # Check if state is supported for filing (now ALL US states are supported via AI)
            state_code = entities.get("state_code")
            filing_available = StateFilingService.is_state_supported(state_code) if state_code else False
            
            # Determine next action based on extracted information
            if entities.get("business_type") and entities.get("state_code"):
                if filing_available:
                    suggested_next = "proceed_to_registration_form"
                else:
                    suggested_next = "invalid_state_code"
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
            
        except Exception as e:
            logging.error(f"Error processing registration request: {e}")
            return {
                "original_message": user_message,
                "entities": {},
                "confirmation": "I apologize, but I encountered an error processing your request.",
                "suggested_next": "error_occurred",
                "filing_available": False,
                "error": str(e)
            }

    async def file_with_state(
        self, 
        entities: Dict[str, Any],
        sos_username: str,
        sos_password: str
    ) -> Dict[str, Any]:
        """File business registration with state using extracted entities"""
        state_code = entities.get("state_code")
        
        if not state_code:
            logging.warning("No state code found in entities")
            return {"success": False, "error": "No state specified in entities"}
        
        if not StateFilingService.is_state_supported(state_code):
            return {
                "success": False,
                "error": f"Invalid state code: {state_code}. Must be valid US state code."
            }
        
        try:
            # Use AI-powered state filing service
            async with StateFilingService(state_code, headless=False) as filing_service:
                logging.info(f"Starting filing process for {filing_service.state_name}")
                
                # Login to state SOS system
                print(f"🔐 Attempting login to {filing_service.state_name} SOS...")
                login_success = await filing_service.login(sos_username, sos_password)
                if not login_success:
                    return {
                        "success": False,
                        "state": state_code,
                        "state_name": filing_service.state_name,
                        "error": f"Login to {filing_service.state_name} SOS failed. Please check credentials."
                    }
                
                # Navigate to LLC filing form
                print(f"🧭 Navigating to LLC filing form...")
                nav_success = await filing_service.navigate_to_llc_filing()
                if not nav_success:
                    return {
                        "success": False,
                        "state": state_code,
                        "state_name": filing_service.state_name,
                        "error": "Failed to navigate to LLC filing page"
                    }
                
                # Fill form with extracted business data
                business_data = {
                    "business_name": entities.get("business_name"),
                    "registered_agent_name": entities.get("owner_name"),
                    "registered_agent_address": entities.get("address"),
                    "purpose": entities.get("purpose", "All lawful purposes")
                }
                
                print(f"📝 Filling form with business data...")
                fill_success = await filing_service.fill_llc_formation(business_data)
                if not fill_success:
                    return {
                        "success": False,
                        "state": state_code,
                        "state_name": filing_service.state_name,
                        "error": "Failed to fill LLC formation form"
                    }
                
                # Take screenshot for user review
                screenshot_path = await filing_service.take_screenshot()
                
                return {
                    "success": True,
                    "state": state_code,
                    "state_name": filing_service.state_name,
                    "logged_in": True,
                    "form_filled": True,
                    "ready_to_submit": True,
                    "preview_screenshot": screenshot_path,
                    "business_data": business_data,
                    "research_config": filing_service.config,
                    "message": f"Form filled successfully for {filing_service.state_name}. Review screenshot before submitting."
                }
                
        except Exception as e:
            logging.error(f"Filing service error for {state_code}: {e}")
            return {
                "success": False,
                "state": state_code,
                "error": f"Filing service error: {str(e)}"
            }

    async def submit_filing(
        self,
        entities: Dict[str, Any],
        sos_username: str,
        sos_password: str
    ) -> Dict[str, Any]:
        """Submit the LLC filing form after user confirmation"""
        state_code = entities.get("state_code")
        
        if not state_code:
            return {"success": False, "error": "No state specified"}
        
        try:
            async with StateFilingService(state_code, headless=False) as filing_service:
                # Re-login and navigate (in case session expired)
                await filing_service.login(sos_username, sos_password)
                await filing_service.navigate_to_llc_filing()
                
                # Re-fill form
                business_data = {
                    "business_name": entities.get("business_name"),
                    "registered_agent_name": entities.get("owner_name"),
                    "registered_agent_address": entities.get("address"),
                    "purpose": entities.get("purpose", "All lawful purposes")
                }
                await filing_service.fill_llc_formation(business_data)
                
                # Submit the form
                print(f"📤 Submitting LLC formation to {filing_service.state_name}...")
                result = await filing_service.submit_form()
                
                return {
                    **result,
                    "business_data": business_data,
                    "submission_timestamp": result.get("url", "Unknown")
                }
                
        except Exception as e:
            logging.error(f"Submission error for {state_code}: {e}")
            return {
                "success": False,
                "state": state_code,
                "error": f"Submission failed: {str(e)}"
            }

    async def get_filing_status(self, state_code: str, confirmation_number: str = None) -> Dict[str, Any]:
        """Check the status of a filed business registration"""
        if not StateFilingService.is_state_supported(state_code):
            return {"success": False, "error": f"State {state_code} not supported"}
        
        # This would need to be implemented per state
        return {
            "success": True,
            "state": state_code,
            "status": "submitted",
            "confirmation_number": confirmation_number,
            "note": "Status checking not yet implemented for all states - check state website manually"
        }

    async def research_state_requirements(self, state_code: str) -> Dict[str, Any]:
        """Research state-specific LLC requirements using AI"""
        if not StateFilingService.is_state_supported(state_code):
            return {"success": False, "error": f"Invalid state code: {state_code}"}
        
        try:
            # Create a temporary filing service just for research
            async with StateFilingService(state_code, headless=False) as filing_service:
                return {
                    "success": True,
                    "state": state_code,
                    "state_name": filing_service.state_name,
                    "research_results": filing_service.config,
                    "requirements": filing_service.config.get("typical_requirements", []),
                    "estimated_cost": filing_service.config.get("estimated_cost", "Unknown"),
                    "online_filing_available": filing_service.config.get("online_filing_available", False),
                    "notes": filing_service.config.get("notes", "")
                }
        except Exception as e:
            logging.error(f"Research error for {state_code}: {e}")
            return {
                "success": False,
                "state": state_code,
                "error": f"Research failed: {str(e)}"
            }

    def get_supported_states(self) -> list[str]:
        """Get list of all supported states (now all US states via AI)"""
        return StateFilingService.get_supported_states()

    def is_filing_available(self, state_code: str) -> bool:
        """Check if automated filing is available for a state"""
        return StateFilingService.is_state_supported(state_code)

    async def validate_business_data(self, entities: Dict[str, Any]) -> Dict[str, Any]:
        """Validate business data before filing"""
        errors = []
        warnings = []
        
        # Required fields
        if not entities.get("business_name"):
            errors.append("Business name is required")
        
        if not entities.get("state_code"):
            errors.append("State code is required")
        elif not self.is_filing_available(entities["state_code"]):
            errors.append(f"State {entities['state_code']} is not a valid US state")
        
        # Optional but recommended fields
        if not entities.get("owner_name"):
            warnings.append("Registered agent name not specified - may be required by state")
        
        if not entities.get("address"):
            warnings.append("Registered agent address not specified - required by most states")
        
        # Business name validation
        business_name = entities.get("business_name", "")
        if business_name:
            if len(business_name) < 3:
                warnings.append("Business name seems very short")
            if not any(suffix in business_name.upper() for suffix in ["LLC", "L.L.C.", "LIMITED LIABILITY COMPANY"]):
                warnings.append("Business name should include 'LLC' or 'Limited Liability Company'")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "warnings": warnings,
            "entities": entities
        }

    async def generate_business_suggestions(self, partial_request: str) -> Dict[str, Any]:
        """Generate business name and structure suggestions"""
        prompt = f"""
Based on this business request: "{partial_request}"

Suggest:
1. 3 professional LLC business names (must include LLC)
2. Appropriate business purpose statement
3. Recommended business structure (LLC, Corporation, etc.)

Return as JSON:
{{
    "suggested_names": ["Name 1 LLC", "Name 2 LLC", "Name 3 LLC"],
    "purpose": "business purpose statement",
    "recommended_structure": "LLC",
    "reasoning": "why this structure is recommended"
}}
"""
        
        try:
            suggestions_json = await self.llm.generate(prompt)
            import json
            suggestions = json.loads(suggestions_json.strip())
            return {"success": True, **suggestions}
        except Exception as e:
            logging.error(f"Error generating suggestions: {e}")
            return {
                "success": False,
                "error": "Could not generate suggestions",
                "suggested_names": ["Your Business LLC", "Professional Services LLC", "Consulting Group LLC"],
                "purpose": "All lawful purposes",
                "recommended_structure": "LLC"
            }