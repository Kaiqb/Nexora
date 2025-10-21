from __future__ import annotations
from typing import Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from playwright.async_api import Page, Browser

STATE_CONFIG: Dict[str, Dict] = {
    "TX": {
        "name": "Texas",
        "base_url": "https://direct.sos.state.tx.us/",
        "login_url": "https://direct.sos.state.tx.us/acct/login.asp",
        "llc_form_url": "https://direct.sos.state.tx.us/help/forms.asp",
        "selectors": {
            "username": 'input[name="username"]',
            "password": 'input[name="password"]',
            "login_button": 'input[type="submit"]',
            "llc_link": 'text=Certificate of Formation - Limited Liability Company',
            "business_name": 'input[name="entity_name"]',
            "registered_agent_name": 'input[name="agent_name"]',
            "registered_agent_address": 'textarea[name="agent_address"]',
            "purpose": 'textarea[name="purpose"]',
            "duration": 'input[name="duration"]',
            "submit_button": 'input[value="Submit"]'
        },
    },
    "CA": {
        "name": "California",
        "base_url": "https://bizfileonline.sos.ca.gov/",
        "login_url": "https://bizfileonline.sos.ca.gov/account/login",
        "llc_form_url": "https://bizfileonline.sos.ca.gov/forms/llc",
        "selectors": {
            "username": 'input[name="email"]',
            "password": 'input[name="password"]',
            "login_button": 'button[type="submit"]',
            "llc_link": 'a[href*="llc"]',
            "business_name": 'input[id="entityName"]',
            "registered_agent_name": 'input[id="agentName"]',
            "registered_agent_address": 'textarea[id="agentAddress"]',
            "purpose": 'textarea[id="businessPurpose"]',
            "duration": 'input[id="duration"]',
            "submit_button": 'button[type="submit"]'
        },
    },
    "FL": {
        "name": "Florida",
        "base_url": "https://dos.myflorida.com/sunbiz/",
        "login_url": "https://dos.myflorida.com/sunbiz/login/",
        "llc_form_url": "https://dos.myflorida.com/sunbiz/start-business/efile/",
        "selectors": {
            "username": 'input[name="userId"]',
            "password": 'input[name="password"]',
            "login_button": 'input[value="Login"]',
            "llc_link": 'a:has-text("Limited Liability Company")',
            "business_name": 'input[name="entityName"]',
            "registered_agent_name": 'input[name="agentName"]',
            "registered_agent_address": 'textarea[name="agentAddress"]',
            "purpose": 'textarea[name="purpose"]',
            "duration": 'input[name="duration"]',
            "submit_button": 'input[value="Submit"]'
        },
    },
}

class StateFilingService:
    def __init__(self, state_code: str, *, headless: bool = False) -> None:
        self.state_code = state_code.upper()
        if self.state_code not in STATE_CONFIG:
            raise ValueError(
                f"State {self.state_code} not yet supported. "
                f"Supported states: {', '.join(STATE_CONFIG.keys())}"
            )
        self.config = STATE_CONFIG[self.state_code]
        self.state_name = self.config["name"]
        self._headless = headless
        self.playwright = None
        self.browser: Optional["Browser"] = None
        self.page: Optional["Page"] = None

    async def __aenter__(self) -> "StateFilingService":
        try:
            from playwright.async_api import async_playwright  # lazy import
        except Exception as e:
            raise RuntimeError(
                "Playwright is required. Install it and Chromium:\n"
                "  python -m pip install playwright\n"
                "  python -m playwright install chromium"
            ) from e
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=self._headless)
        self.page = await self.browser.new_page()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        try:
            if self.browser:
                await self.browser.close()
        finally:
            if self.playwright:
                await self.playwright.stop()

    async def login(self, username: str, password: str) -> bool:
        try:
            assert self.page is not None
            await self.page.goto(self.config["login_url"])
            await self.page.fill(self.config["selectors"]["username"], username)
            await self.page.fill(self.config["selectors"]["password"], password)
            await self.page.click(self.config["selectors"]["login_button"])
            await self.page.wait_for_load_state("networkidle")
            url = self.page.url.lower()
            return not ("login" in url or "error" in url)
        except Exception:
            return False

    async def navigate_to_llc_filing(self) -> bool:
        try:
            assert self.page is not None
            await self.page.goto(self.config["llc_form_url"])
            if "llc_link" in self.config["selectors"]:
                try:
                    await self.page.click(self.config["selectors"]["llc_link"])
                except Exception:
                    pass
            await self.page.wait_for_load_state("networkidle")
            return True
        except Exception:
            return False

    async def fill_llc_formation(self, business_data: Dict) -> bool:
        try:
            assert self.page is not None
            s = self.config["selectors"]
            if business_data.get("business_name") and "business_name" in s:
                await self.page.fill(s["business_name"], business_data["business_name"])
            if business_data.get("registered_agent_name") and "registered_agent_name" in s:
                await self.page.fill(s["registered_agent_name"], business_data["registered_agent_name"])
            if business_data.get("registered_agent_address") and "registered_agent_address" in s:
                await self.page.fill(s["registered_agent_address"], business_data["registered_agent_address"])
            if "purpose" in s:
                await self.page.fill(s["purpose"], business_data.get("purpose", "All lawful purposes"))
            if "duration" in s:
                await self.page.fill(s["duration"], business_data.get("duration", "perpetual"))
            return True
        except Exception:
            return False

    async def submit_form(self) -> Dict[str, object]:
        try:
            assert self.page is not None
            await self.page.click(self.config["selectors"]["submit_button"])
            await self.page.wait_for_load_state("networkidle")
            confirmation_text = await self.page.text_content("body")
            return {
                "success": True,
                "state": self.state_name,
                "confirmation": (confirmation_text or "")[:500],
                "url": self.page.url,
            }
        except Exception as e:
            return {"success": False, "state": self.state_name, "error": str(e)}

    async def take_screenshot(self, filename: Optional[str] = None) -> str:
        assert self.page is not None
        filename = filename or f"{self.state_code}_llc_form.png"
        await self.page.screenshot(path=filename)
        return filename

    @staticmethod
    def get_supported_states() -> list[str]:
        return list(STATE_CONFIG.keys())

    @staticmethod
    def is_state_supported(state_code: str) -> bool:
        return state_code.upper() in STATE_CONFIG