from datetime import date
from typing import List, Optional, Tuple

from .models import CompanyProfile, SearchResult


def _ad_section(result: SearchResult, platform: str = "LinkedIn") -> str:
    count_str = str(result.total_ads) if result.total_ads else "Unknown"
    if result.error and result.total_ads == 0:
        count_str = f"N/A ({result.error})"

    lines = [f"**{platform} Ads** ({count_str} active ads found)"]

    if result.screenshot_path:
        lines.append(f"![{platform} Ads]({result.screenshot_path})")

    if result.ads:
        themes = [ad.headline for ad in result.ads if ad.headline][:5]
        if themes:
            lines.append("\nKey ad headlines observed:")
            for t in themes:
                lines.append(f"- {t}")

    return "\n".join(lines)


def _profile_section(profile: CompanyProfile) -> str:
    lines = []
    if profile.title:
        lines.append(f"**Page title:** {profile.title}")
    if profile.meta_description:
        lines.append(f"**Meta description:** {profile.meta_description}")
    if profile.headings:
        lines.append("\n**Key headings:**")
        for h in profile.headings[:8]:
            lines.append(f"- {h}")
    if profile.ctas:
        lines.append("\n**CTAs observed:**")
        for c in profile.ctas[:6]:
            lines.append(f"- {c}")
    if profile.pricing_notes:
        lines.append(f"\n**Pricing signals:** {profile.pricing_notes}")
    return "\n".join(lines)


def generate_report(
    target_profile: CompanyProfile,
    target_ads: SearchResult,
    competitors: List[Tuple[CompanyProfile, SearchResult]],
    output_path: str,
) -> None:
    today = date.today().strftime("%d %B %Y")

    # Executive summary bullets
    exec_bullets = [
        f"reviews.io has **{target_ads.total_ads}** active LinkedIn ads at time of analysis.",
    ]
    if target_profile.meta_description:
        exec_bullets.append(f"Core positioning: \"{target_profile.meta_description}\"")
    if competitors:
        top = sorted(competitors, key=lambda x: x[1].total_ads, reverse=True)
        exec_bullets.append(
            f"Largest competitor by LinkedIn ad volume: **{top[0][0].name}** "
            f"({top[0][1].total_ads} ads)"
        )
    exec_bullets.append(
        "See competitor sections and insights table for full breakdown."
    )

    lines = [
        f"# Competitive Intelligence Report: reviews.io",
        f"",
        f"**Date:** {today}",
        f"",
        f"---",
        f"",
        f"## Executive Summary",
        f"",
    ]
    for b in exec_bullets:
        lines.append(f"- {b}")

    lines += [
        "",
        "---",
        "",
        "## Target Company Analysis: reviews.io",
        "",
        "### Website & Positioning",
        "",
        _profile_section(target_profile),
        "",
        "### Active Advertising",
        "",
        _ad_section(target_ads),
        "",
        "---",
        "",
        "## Competitor Analysis",
        "",
    ]

    for prof, ads in competitors:
        lines += [
            f"### {prof.name}",
            f"",
            f"**Website:** {prof.url}",
            f"",
            _profile_section(prof),
            f"",
            "**Ad Activity:**",
            f"",
            _ad_section(ads),
            f"",
        ]

    # Insights table
    lines += [
        "---",
        "",
        "## Competitive Insights",
        "",
        "### Ad Platform Activity",
        "",
        "| Company | LinkedIn Ads |",
        "|---------|-------------|",
    ]
    lines.append(f"| reviews.io | {target_ads.total_ads} |")
    for prof, ads in competitors:
        lines.append(f"| {prof.name} | {ads.total_ads} |")

    lines += [
        "",
        "### Messaging Opportunities",
        "",
        "_(Based on heading and CTA analysis above — review screenshots for full creative context.)_",
        "",
        "---",
        "",
        "## Recommendations",
        "",
        "1. Compare ad volumes against competitors to gauge relative LinkedIn investment.",
        "2. Review screenshot for ad creative themes, offers, and CTAs in use.",
        "3. Identify messaging angles competitors are not covering.",
        "4. Monitor competitor ad counts weekly for campaign ramp-up signals.",
        "5. Use heading/CTA data from competitor sites to spot positioning gaps.",
        "",
        "---",
        "",
        "## Appendix: Ad Screenshots",
        "",
        "| Company | Platform | Screenshot | Ad Count |",
        "|---------|----------|------------|----------|",
        f"| reviews.io | LinkedIn | {target_ads.screenshot_path or 'N/A'} | {target_ads.total_ads} |",
    ]
    for prof, ads in competitors:
        lines.append(
            f"| {prof.name} | LinkedIn | {ads.screenshot_path or 'N/A'} | {ads.total_ads} |"
        )

    report_text = "\n".join(lines) + "\n"

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(report_text)

    print(f"\nReport saved to: {output_path}")
