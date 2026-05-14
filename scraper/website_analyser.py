import logging
import re
from typing import List

from bs4 import BeautifulSoup
from playwright.async_api import BrowserContext, Page

from .models import CompanyProfile

logger = logging.getLogger(__name__)

PRICING_KEYWORDS = re.compile(
    r"\b(pricing|plans?|per month|\/mo|free trial|starter|growth|enterprise|£|\$)\b",
    re.IGNORECASE,
)

CTA_KEYWORDS = [
    "cta", "btn", "button", "signup", "sign-up", "start", "trial",
    "demo", "get started", "free", "book", "request",
]


def _parse_html(html: str, profile: CompanyProfile) -> CompanyProfile:
    soup = BeautifulSoup(html, "html.parser")

    profile.title = (soup.title.string or "").strip() if soup.title else None
    meta = soup.find("meta", attrs={"name": "description"}) or soup.find(
        "meta", attrs={"property": "og:description"}
    )
    profile.meta_description = (meta.get("content") or "").strip() if meta else None

    headings: List[str] = []
    for tag in soup.find_all(["h1", "h2", "h3"]):
        text = tag.get_text(" ", strip=True)
        if text and len(text) > 3:
            headings.append(text)
    profile.headings = headings[:20]

    ctas: List[str] = []
    for el in soup.find_all(["a", "button"]):
        text = el.get_text(" ", strip=True)
        if text and 2 < len(text) < 60:
            classes = " ".join(el.get("class", []))
            href = el.get("href", "")
            if any(kw in (classes + href + text).lower() for kw in CTA_KEYWORDS):
                ctas.append(text)
    profile.ctas = list(dict.fromkeys(ctas))[:10]

    pricing_hits = []
    for el in soup.find_all(["h1", "h2", "h3", "p", "li", "span"]):
        text = el.get_text(" ", strip=True)
        if PRICING_KEYWORDS.search(text) and len(text) < 200:
            pricing_hits.append(text)
    if pricing_hits:
        profile.pricing_notes = " | ".join(pricing_hits[:5])

    return profile


async def analyse_website(context: BrowserContext, company_name: str, url: str) -> CompanyProfile:
    logger.info("Fetching website via browser: %s", url)
    profile = CompanyProfile(name=company_name, url=url)
    page: Page = await context.new_page()
    try:
        resp = await page.goto(url, wait_until="domcontentloaded", timeout=20_000)
        if resp and resp.status >= 400:
            logger.warning("Got HTTP %d for %s", resp.status, url)
            return profile
        # Wait briefly for JS-rendered content to settle
        await page.wait_for_timeout(1500)
        html = await page.content()
        return _parse_html(html, profile)
    except Exception as exc:
        logger.warning("Could not fetch %s: %s", url, exc)
        return profile
    finally:
        await page.close()
