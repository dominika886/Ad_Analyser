import asyncio
import json
import logging
import random
import re
from typing import Optional

from playwright.async_api import BrowserContext, Page

from .browser import take_screenshot
from .models import Ad, SearchResult

logger = logging.getLogger(__name__)

AD_LIBRARY_SEARCH = "https://www.linkedin.com/ad-library/search"

# Patterns that match LinkedIn's internal ad library API responses
API_PATTERNS = [
    re.compile(r"linkedin\.com/ad-library/api/v\d+/ads"),
    re.compile(r"linkedin\.com/voyager/api/ads/adLibrary"),
    re.compile(r"linkedin\.com/ad-library/api/v\d+/search"),
]


def _slug(company_name: str) -> str:
    """Convert a company name to a likely LinkedIn slug."""
    return re.sub(r"[^a-z0-9]+", "-", company_name.lower()).strip("-")


async def _wait_and_capture_api_response(page: Page, timeout_s: float = 20.0) -> Optional[dict]:
    """
    Wait for the first LinkedIn ad library API response and return its JSON body.
    Must be called BEFORE page.goto() so the listener is registered first.
    """
    loop = asyncio.get_event_loop()
    future: asyncio.Future = loop.create_future()

    async def on_response(response):
        if future.done():
            return
        url = response.url
        if not any(p.search(url) for p in API_PATTERNS):
            return
        try:
            body = await response.json()
            if not future.done():
                future.set_result(body)
        except Exception:
            pass

    page.on("response", on_response)
    try:
        return await asyncio.wait_for(future, timeout=timeout_s)
    except asyncio.TimeoutError:
        logger.warning("Timed out waiting for LinkedIn ad API response")
        return None
    finally:
        try:
            page.remove_listener("response", on_response)
        except Exception:
            pass


def _extract_total(data: dict) -> int:
    """Try multiple known paths for the total ad count."""
    candidates = [
        data.get("paging", {}).get("total"),
        data.get("metadata", {}).get("total"),
        data.get("data", {}).get("paging", {}).get("total"),
    ]
    for c in candidates:
        if isinstance(c, int):
            return c
    elements = data.get("elements", data.get("data", {}).get("elements", []))
    return len(elements) if isinstance(elements, list) else 0


def _parse_elements(data: dict, company_name: str) -> list[Ad]:
    elements = data.get("elements") or data.get("data", {}).get("elements") or []
    ads = []
    for el in elements:
        content = el.get("content") or el.get("adContent") or {}
        ads.append(Ad(
            ad_id=str(el.get("id", el.get("adId", ""))),
            advertiser_name=el.get("advertiserName", company_name),
            headline=content.get("headline") or content.get("title"),
            ad_type=el.get("adType") or content.get("type"),
            status=el.get("status"),
            start_date=str(el.get("campaignDateRange", {}).get("start", "")),
            end_date=str(el.get("campaignDateRange", {}).get("end", "")),
        ))
    return ads


class LinkedInAdLibraryScraper:

    def __init__(self, context: BrowserContext):
        self._context = context

    async def search(self, company_name: str, output_dir: str) -> SearchResult:
        slug = _slug(company_name)
        url = f"{AD_LIBRARY_SEARCH}?accountOwner={slug}"
        logger.info("Fetching LinkedIn ads for %s → %s", company_name, url)

        page: Page = await self._context.new_page()
        try:
            capture_task = asyncio.ensure_future(_wait_and_capture_api_response(page))

            await page.goto(url, wait_until="domcontentloaded", timeout=30_000)

            # Detect login wall
            if "/login" in page.url or "/checkpoint" in page.url:
                logger.warning("LinkedIn redirected to login page — cannot access ad library")
                capture_task.cancel()
                screenshot_path = f"{output_dir}/{slug}-linkedin-ads.png"
                await take_screenshot(page, screenshot_path)
                return SearchResult(
                    company_name=company_name,
                    company_slug=slug,
                    total_ads=0,
                    screenshot_path=screenshot_path,
                    error="LinkedIn requires login to view ads",
                )

            # Simulate human scrolling to trigger lazy-loaded XHR
            await asyncio.sleep(random.uniform(1.5, 2.5))
            await page.mouse.wheel(0, 600)
            await asyncio.sleep(random.uniform(0.5, 1.0))

            data = await capture_task

            screenshot_path = f"{output_dir}/{slug}-linkedin-ads.png"
            await take_screenshot(page, screenshot_path)

            if data is None:
                logger.debug("No API response captured; attempting count from page text")
                total = await _count_from_page(page)
                return SearchResult(
                    company_name=company_name,
                    company_slug=slug,
                    total_ads=total,
                    screenshot_path=screenshot_path,
                    error="API response not captured; count estimated from page" if total == 0 else None,
                )

            logger.debug("API response keys: %s", list(data.keys()))
            total = _extract_total(data)
            ads = _parse_elements(data, company_name)
            logger.info("Found %d total ads for %s", total, company_name)

            return SearchResult(
                company_name=company_name,
                company_slug=slug,
                total_ads=total,
                screenshot_path=screenshot_path,
                ads=ads,
            )

        except Exception as exc:
            logger.error("Error scraping %s: %s", company_name, exc)
            return SearchResult(
                company_name=company_name,
                company_slug=slug,
                total_ads=0,
                error=str(exc),
            )
        finally:
            await page.close()


async def _count_from_page(page: Page) -> int:
    """Last-resort: try to read a count from visible page text."""
    try:
        text = await page.inner_text("body")
        m = re.search(r"(\d[\d,]*)\s+(?:active\s+)?ads?", text, re.IGNORECASE)
        if m:
            return int(m.group(1).replace(",", ""))
    except Exception:
        pass
    return 0
