from __future__ import annotations
import json
import re
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page, Browser

# US States mapping
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "FL": "Florida", "GA": "Georgia",
    "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois", "IN": "Indiana", "IA": "Iowa",
    "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana", "ME": "Maine", "MD": "Maryland",
    "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota", "MS": "Mississippi", "MO": "Missouri",
    "MT": "Montana", "NE": "Nebraska", "NV": "Nevada", "NH": "New Hampshire", "NJ": "New Jersey",
    "NM": "New Mexico", "NY": "New York", "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio",
    "OK": "Oklahoma", "OR": "Oregon", "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina",
    "SD": "South Dakota", "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont",
    "VA": "Virginia", "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"
}

class StateFilingService:
    """AI-powered state filing service that dynamically researches any US state"""
    
    def __init__(self, state_code: str, *, headless: bool = False) -> None:
        self.state_code = state_code.upper()
        if self.state_code not in US_STATES:
            raise ValueError(f"Invalid state code: {state_code}. Must be valid US state code.")
        
        self.state_name = US_STATES[self.state_code]
        self._headless = headless
        self.config: Optional[Dict] = None  # Will be populated by AI research
        self.playwright = None
        self.browser: Optional["Browser"] = None
        self.page: Optional["Page"] = None

    async def __aenter__(self) -> "StateFilingService":
        try:
            from playwright.async_api import async_playwright
        except Exception as e:
            raise RuntimeError(
                "Playwright is required. Install it and Chromium:\n"
                "  python -m pip install playwright\n"
                "  python -m playwright install chromium"
            ) from e
        
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self._headless)
        self.page = await self.browser.new_page()
        
        # AI research phase - discover state filing info
        print(f"🔍 Researching {self.state_name} ({self.state_code}) filing process...")
        self.config = await self.research_state_filing_process()
        print(f"✅ Research complete for {self.state_name}")
        
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if self.browser:
                await self.browser.close()
        finally:
            if self.playwright:
                await self.playwright.stop()

    async def research_state_filing_process(self) -> Dict[str, any]:
        """Use AI to research and discover state filing URLs and process"""
        research_prompt = f"""
You are a business registration research assistant. I need to find the official Secretary of State website and LLC filing process for {self.state_name} ({self.state_code}).

Please provide ONLY a JSON response with this exact structure:
{{
    "name": "{self.state_name}",
    "base_url": "official SOS website URL",
    "login_url": "login/account page URL if online filing available",
    "llc_form_url": "direct URL to LLC formation page or form",
    "online_filing_available": true/false,
    "typical_requirements": ["list", "of", "required", "information"],
    "estimated_cost": "filing fee if known",
    "notes": "any important process notes"
}}

State: {self.state_name} ({self.state_code})
Focus: Limited Liability Company (LLC) formation
Requirement: Must be official government (.gov) websites only
"""
        
        from .llm_service import LLMService
        llm = LLMService()
        research_result = await llm.generate(research_prompt)
        
        try:
            # Parse AI response as JSON
            config = json.loads(research_result.strip())
            print(f"📋 Found: {config.get('base_url', 'Unknown URL')}")
            return config
        except json.JSONDecodeError:
            # Fallback if AI doesn't return proper JSON
            print(f"⚠️ AI research failed for {self.state_name}, using fallback")
            return self._get_fallback_config()

    async def discover_form_selectors(self, target_url: str) -> Dict[str, str]:
        """Use browser + AI to discover form field selectors on the target page"""
        print(f"🕵️ Analyzing form fields on {target_url}...")
        
        try:
            await self.page.goto(target_url, timeout=30000)
            await self.page.wait_for_load_state('networkidle', timeout=10000)
            
            # Get form elements from the page
            page_content = await self.page.content()
            
            # Use AI to analyze HTML and find selectors
            selector_prompt = f"""
Analyze this HTML page content and identify CSS selectors for LLC filing form fields.

HTML Content (first 4000 characters):
{page_content[:4000]}

Find CSS selectors for these common LLC filing fields and return ONLY valid JSON:
{{
    "username": "CSS selector for username/email field",
    "password": "CSS selector for password field", 
    "login_button": "CSS selector for login/submit button",
    "business_name": "CSS selector for entity/business name field",
    "registered_agent_name": "CSS selector for registered agent name",
    "registered_agent_address": "CSS selector for agent address",
    "purpose": "CSS selector for business purpose field",
    "submit_button": "CSS selector for form submit button"
}}

Rules:
- Use specific selectors like input[name="field_name"] or #field_id
- If a field doesn't exist, use null
- Return valid JSON only
"""
            
            from .llm_service import LLMService
            llm = LLMService()
            selectors_response = await llm.generate(selector_prompt)
            
            try:
                selectors = json.loads(selectors_response.strip())
                print(f"✅ Discovered {len([s for s in selectors.values() if s])} form selectors")
                return selectors
            except json.JSONDecodeError:
                print("⚠️ Selector discovery failed, using generic selectors")
                return self._get_generic_selectors()
                
        except Exception as e:
            print(f"❌ Error analyzing page: {e}")
            return self._get_generic_selectors()

    async def login(self, username: str, password: str) -> bool:
        """Login using AI-discovered selectors"""
        try:
            if not self.config or not self.config.get("online_filing_available"):
                print(f"❌ {self.state_name} doesn't support online filing")
                return False
                
            print(f"🔐 Logging into {self.state_name} SOS...")
            
            login_url = self.config.get("login_url")
            if not login_url:
                print("❌ No login URL found")
                return False
            
            # Discover selectors for this specific login page
            selectors = await self.discover_form_selectors(login_url)
            
            if selectors.get("username") and selectors.get("password"):
                await self.page.fill(selectors["username"], username)
                await self.page.fill(selectors["password"], password)
                
                if selectors.get("login_button"):
                    await self.page.click(selectors["login_button"])
                    await self.page.wait_for_load_state("networkidle")
                    
                    # Check if login succeeded
                    current_url = self.page.url.lower()
                    success = not ("login" in current_url or "error" in current_url)
                    print(f"{'✅' if success else '❌'} Login {'successful' if success else 'failed'}")
                    return success
            
            print("❌ Could not find login form fields")
            return False
            
        except Exception as e:
            print(f"❌ Login error: {e}")
            return False

    async def navigate_to_llc_filing(self) -> bool:
        """Navigate to LLC filing form using AI-discovered URL"""
        try:
            llc_url = self.config.get("llc_form_url") if self.config else None
            if not llc_url:
                print("❌ No LLC form URL found")
                return False
                
            print(f"🧭 Navigating to LLC filing form...")
            await self.page.goto(llc_url)
            await self.page.wait_for_load_state("networkidle")
            print("✅ Reached LLC filing page")
            return True
            
        except Exception as e:
            print(f"❌ Navigation error: {e}")
            return False

    async def fill_llc_formation(self, business_data: Dict) -> bool:
        """Fill LLC form using dynamically discovered selectors"""
        try:
            print(f"📝 Filling LLC formation form...")
            
            # Discover selectors for current page
            current_url = self.page.url
            selectors = await self.discover_form_selectors(current_url)
            
            filled_fields = 0
            
            # Fill discovered fields
            for field_name, selector in selectors.items():
                if not selector or field_name in ["username", "password", "login_button"]:
                    continue
                    
                try:
                    if field_name == "business_name" and business_data.get("business_name"):
                        await self.page.fill(selector, business_data["business_name"])
                        filled_fields += 1
                        print(f"  ✓ Business name: {business_data['business_name']}")
                        
                    elif field_name == "registered_agent_name" and business_data.get("registered_agent_name"):
                        await self.page.fill(selector, business_data["registered_agent_name"])
                        filled_fields += 1
                        
                    elif field_name == "registered_agent_address" and business_data.get("registered_agent_address"):
                        await self.page.fill(selector, business_data["registered_agent_address"])
                        filled_fields += 1
                        
                    elif field_name == "purpose":
                        purpose = business_data.get("purpose", "All lawful purposes")
                        await self.page.fill(selector, purpose)
                        filled_fields += 1
                        
                except Exception as field_error:
                    print(f"  ⚠️ Could not fill {field_name}: {field_error}")
            
            print(f"✅ Filled {filled_fields} form fields")
            return filled_fields > 0
            
        except Exception as e:
            print(f"❌ Form filling error: {e}")
            return False

    async def submit_form(self) -> Dict[str, any]:
        """Submit form using AI-discovered submit button"""
        try:
            print(f"📤 Submitting {self.state_name} LLC formation...")
            
            # Find submit button on current page
            current_url = self.page.url
            selectors = await self.discover_form_selectors(current_url)
            
            submit_selector = selectors.get("submit_button")
            if submit_selector:
                await self.page.click(submit_selector)
                await self.page.wait_for_load_state("networkidle")
                
                confirmation_text = await self.page.text_content("body")
                return {
                    "success": True,
                    "state": self.state_name,
                    "confirmation": (confirmation_text or "")[:500],
                    "url": self.page.url,
                }
            else:
                return {"success": False, "state": self.state_name, "error": "No submit button found"}
                
        except Exception as e:
            return {"success": False, "state": self.state_name, "error": str(e)}

    async def take_screenshot(self, filename: Optional[str] = None) -> str:
        """Take screenshot for user review"""
        assert self.page is not None
        filename = filename or f"{self.state_code}_llc_form.png"
        await self.page.screenshot(path=filename)
        print(f"📸 Screenshot saved: {filename}")
        return filename

    def _get_fallback_config(self) -> Dict[str, any]:
        """Fallback config when AI research fails"""
        return {
            "name": self.state_name,
            "base_url": f"https://sos.{self.state_code.lower()}.gov/",
            "login_url": None,
            "llc_form_url": None,
            "online_filing_available": False,
            "typical_requirements": ["business_name", "registered_agent"],
            "notes": "Research failed - manual verification needed"
        }

    def _get_generic_selectors(self) -> Dict[str, str]:
        """Generic selectors when page analysis fails"""
        return {
            "username": 'input[type="text"], input[type="email"], input[name*="user"], input[name*="email"]',
            "password": 'input[type="password"]',
            "login_button": 'button[type="submit"], input[type="submit"], button:contains("Login")',
            "business_name": 'input[name*="name"], input[name*="entity"]',
            "registered_agent_name": 'input[name*="agent"]',
            "registered_agent_address": 'textarea[name*="address"], input[name*="address"]',
            "purpose": 'textarea[name*="purpose"]',
            "submit_button": 'button[type="submit"], input[type="submit"]'
        }

    @staticmethod
    def get_supported_states() -> list[str]:
        """All US states are supported via AI research"""
        return list(US_STATES.keys())

    @staticmethod
    def is_state_supported(state_code: str) -> bool:
        """All valid US states are supported"""
        return state_code.upper() in US_STATES