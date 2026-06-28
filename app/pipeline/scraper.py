"""
Scraper: fetches job listings from job boards using Playwright.

Adapted from the original job-search-pipeline scrape_jobs.py.
Configured for multi-user use: each call targets specific title + location.
"""

import logging
import re
from typing import List, Dict
from datetime import datetime

logger = logging.getLogger(__name__)

# Sources to scrape (start with LinkedIn Jobs, expandable)
SOURCES = ["linkedin"]


def scrape_jobs(title: str, location: str, max_results: int = 50) -> List[Dict]:
    """Scrape job listings for a single title + location pair.

    Returns list of dicts with keys: title, company, location, salary, url, description, source, scraped_at.
    """
    results = []

    try:
        linkedin_jobs = _scrape_linkedin(title, location, max_results)
        results.extend(linkedin_jobs)
    except Exception as e:
        logger.error(f"LinkedIn scrape failed: {e}", exc_info=True)

    logger.info(f"Scraped {len(results)} jobs for '{title}' in '{location}'")
    return results


def _scrape_linkedin(title: str, location: str, max_results: int) -> List[Dict]:
    """Scrape LinkedIn Jobs using Playwright (headless)."""
    from playwright.sync_api import sync_playwright

    query = title.replace(" ", "%20")
    loc = location.replace(" ", "%20")
    url = (
        f"https://www.linkedin.com/jobs/search/?keywords={query}"
        f"&location={loc}&f_TPR=r86400"  # last 24 hours
    )

    jobs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url, timeout=30000)
        page.wait_for_timeout(3000)

        # LinkedIn job cards
        cards = page.query_selector_all(".jobs-search__results-list li")
        for card in cards[:max_results]:
            try:
                title_el = card.query_selector("h3")
                company_el = card.query_selector(".base-search-card__subtitle a, h4 a")
                link_el = card.query_selector("a.base-card__full-link, a")
                location_el = card.query_selector(".job-search-card__location")

                job_title = title_el.inner_text().strip() if title_el else "Unknown"
                company = company_el.inner_text().strip() if company_el else "Unknown"
                link = link_el.get_attribute("href") if link_el else ""
                job_location = location_el.inner_text().strip() if location_el else location

                # Clean URL (remove tracking params)
                link = link.split("?")[0] if link else ""

                if job_title and company and link:
                    jobs.append({
                        "title": job_title,
                        "company": company,
                        "location": job_location,
                        "salary": None,
                        "url": link,
                        "description": None,
                        "source": "linkedin",
                        "scraped_at": datetime.utcnow().isoformat(),
                    })
            except Exception as e:
                logger.debug(f"Card parse error: {e}")
                continue

        browser.close()

    return jobs
