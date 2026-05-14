from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class Ad:
    ad_id: str
    advertiser_name: str
    headline: Optional[str] = None
    ad_type: Optional[str] = None
    status: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    impressions: Optional[str] = None


@dataclass
class SearchResult:
    company_name: str
    company_slug: str
    total_ads: int
    screenshot_path: Optional[str] = None
    ads: List[Ad] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class CompanyProfile:
    name: str
    url: str
    title: Optional[str] = None
    meta_description: Optional[str] = None
    headings: List[str] = field(default_factory=list)
    ctas: List[str] = field(default_factory=list)
    pricing_notes: Optional[str] = None
