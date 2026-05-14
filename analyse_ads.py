#!/usr/bin/env python3
"""
analyse_ads.py — Competitive intelligence: LinkedIn ad count + website analysis.

Usage:
    python3 analyse_ads.py
    python3 analyse_ads.py --company reviews.io --url https://www.reviews.io --debug
"""
import argparse
import asyncio
import logging
import os
import sys

from scraper.browser import BrowserManager
from scraper.linkedin_ad_library import LinkedInAdLibraryScraper
from scraper.models import CompanyProfile
from scraper.report import generate_report
from scraper.website_analyser import analyse_website

# Known competitors for reviews.io in the review/reputation management space
DEFAULT_COMPETITORS = [
    ("Trustpilot", "https://www.trustpilot.com", "trustpilot"),
    ("Feefo", "https://www.feefo.com", "feefo"),
    ("Yotpo", "https://www.yotpo.com", "yotpo"),
    ("Birdeye", "https://birdeye.com", "birdeye"),
    ("Judge.me", "https://judge.me", "judge-me"),
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "CI_reviewsio")


def parse_args():
    p = argparse.ArgumentParser(description="LinkedIn competitive intelligence for reviews.io")
    p.add_argument("--company", default="reviews.io")
    p.add_argument("--url", default="https://www.reviews.io")
    p.add_argument("--output-dir", default=OUTPUT_DIR)
    p.add_argument("--skip-competitors", action="store_true",
                   help="Only analyse target company, skip competitors")
    p.add_argument("--debug", action="store_true")
    return p.parse_args()


async def run(args):
    os.makedirs(args.output_dir, exist_ok=True)

    # Website analysis (sync, no browser needed)
    print(f"\n[1/3] Analysing {args.company} website...")
    target_profile = analyse_website(args.company, args.url)

    # LinkedIn ad analysis (browser needed)
    print(f"[2/3] Fetching LinkedIn ads for {args.company}...")
    async with BrowserManager() as context:
        scraper = LinkedInAdLibraryScraper(context)
        target_ads = await scraper.search(args.company, args.output_dir)

        competitors = []
        if not args.skip_competitors:
            print(f"[3/3] Analysing {len(DEFAULT_COMPETITORS)} competitors...")
            for name, url, slug in DEFAULT_COMPETITORS:
                print(f"  → {name}")
                prof = analyse_website(name, url)
                ads = await scraper.search(name, args.output_dir)
                competitors.append((prof, ads))

    # Print summary
    print(f"\n{'='*55}")
    print(f"  Company:      {target_ads.company_name}")
    print(f"  LinkedIn Ads: {target_ads.total_ads}")
    if target_ads.error:
        print(f"  Note:         {target_ads.error}")
    if competitors:
        print(f"\n  Competitor LinkedIn ad counts:")
        for prof, ads in competitors:
            note = f"  [{ads.error}]" if ads.error else ""
            print(f"    {prof.name:<20} {ads.total_ads}{note}")
    print(f"{'='*55}\n")

    # Generate report
    report_path = os.path.join(args.output_dir, "report.md")
    generate_report(target_profile, target_ads, competitors, report_path)


def main():
    args = parse_args()
    logging.basicConfig(
        level=logging.DEBUG if args.debug else logging.WARNING,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    asyncio.run(run(args))


if __name__ == "__main__":
    main()
