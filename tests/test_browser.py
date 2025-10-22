# test_browser.py
import asyncio
from playwright.async_api import async_playwright

async def test_browser():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto("https://www.google.com")
        print("Browser should be visible now!")
        await asyncio.sleep(5)  # Keep open for 5 seconds
        await browser.close()

asyncio.run(test_browser())