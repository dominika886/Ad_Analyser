import logging
import re
from typing import List

import requests
from bs4 import BeautifulSoup

from .models import CompanyProfile

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-GB,en;q=0.9",
}

PRICING_KEYWORDS = re.compile(
    r"\b(pricing|plans?|per month|\/mo|free trial|starter|growth|enterprise|£|\$)\b",
    re.IGNORECASE,
)


def analyse_website(company_name: str, url: str) -> CompanyProfile:
    logger.info("Fetching website: %s", url)
    profile = CompanyProfile(name=company_name, url=url)

    try:
        resp = requests.get(url, headers=HEADERS, timeout=15, allow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:
        logger.warning("Could not fetch %s: %s", url, exc)
        return profile

    soup = BeautifulSoup(resp.text, "html.parser")

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
            if any(kw in (classes + href + text).lower() for kw in [
                "cta", "btn", "button", "signup", "sign-up", "start", "trial",
                "demo", "get started", "free", "book", "request",
            ]):
                ctas.append(text)
    profile.ctas = list(dict.fromkeys(ctas))[:10]

    # Pricing hints
    pricing_hits = []
    for el in soup.find_all(["h1", "h2", "h3", "p", "li", "span"]):
        text = el.get_text(" ", strip=True)
        if PRICING_KEYWORDS.search(text) and len(text) < 200:
            pricing_hits.append(text)
    if pricing_hits:
        profile.pricing_notes = " | ".join(pricing_hits[:5])

    return profile
