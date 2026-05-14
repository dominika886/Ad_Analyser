import asyncio
import random
from pathlib import Path
from playwright.async_api import async_playwright, Browser, BrowserContext, Page

# Use sandbox pre-installed Chromium if present, otherwise let Playwright find its own.
_SANDBOX_CHROMIUM = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
CHROMIUM_EXECUTABLE = _SANDBOX_CHROMIUM if Path(_SANDBOX_CHROMIUM).exists() else None

USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
)


class BrowserManager:
    """Async context manager for a headless Chromium browser session."""

    async def __aenter__(self) -> BrowserContext:
        self._pw = await async_playwright().start()
        launch_kwargs = dict(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                "--disable-infobars",
            ],
        )
        if CHROMIUM_EXECUTABLE:
            launch_kwargs["executable_path"] = CHROMIUM_EXECUTABLE
        self._browser: Browser = await self._pw.chromium.launch(**launch_kwargs)
        self._context: BrowserContext = await self._browser.new_context(
            user_agent=USER_AGENT,
            viewport={"width": 1440, "height": 900},
            locale="en-GB",
            ignore_https_errors=True,
            extra_http_headers={"Accept-Language": "en-GB,en;q=0.9"},
        )
        # Hide webdriver flag
        await self._context.add_init_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        return self._context

    async def __aexit__(self, *args):
        await self._browser.close()
        await self._pw.stop()


async def take_screenshot(page: Page, output_path: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    await asyncio.sleep(random.uniform(2.0, 3.5))
    await page.screenshot(path=output_path, full_page=False)
