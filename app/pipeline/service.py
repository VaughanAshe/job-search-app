"""
Pipeline service: bridges the existing job-search-pipeline code into the web app.

This module adapts the standalone scripts (scrape_jobs.py, job_scorer.py,
enrich_jobs.py) into a service layer that writes results to the app's database
instead of files/Telegram.

The actual scraping and scoring logic lives in app/pipeline/scraper.py and
app/pipeline/scorer.py, which are adapted versions of the original scripts.
"""

import logging
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.db import Job

logger = logging.getLogger(__name__)


def scrape_and_score(
    db: Session,
    user_id: int,
    job_titles: List[str],
    locations: List[str],
    salary_min: int = 0,
    salary_max: Optional[int] = None,
    exclusions: Optional[List[str]] = None,
) -> tuple:
    """Run the full pipeline: scrape -> score -> store in DB.

    Returns (total_found, total_filtered, new_jobs_stored).
    """
    from app.pipeline.scraper import scrape_jobs
    from app.pipeline.scorer import score_jobs

    exclusions = exclusions or []
    total_found = 0
    total_filtered = 0
    new_count = 0

    for title in job_titles:
        for location in locations:
            logger.info(f"Scraping: {title} in {location}")
            try:
                raw_jobs = scrape_jobs(title=title, location=location)
                total_found += len(raw_jobs)

                # Score and filter
                scored = score_jobs(
                    jobs=raw_jobs,
                    target_titles=job_titles,
                    salary_min=salary_min,
                    salary_max=salary_max,
                    exclusions=exclusions,
                )

                for job_data in scored:
                    if not job_data.get("pass"):
                        total_filtered += 1
                        continue

                    # Dedup: check if this job already exists for this user
                    existing = (
                        db.query(Job)
                        .filter(
                            Job.user_id == user_id,
                            Job.title == job_data["title"],
                            Job.company == job_data["company"],
                        )
                        .first()
                    )
                    if existing:
                        continue

                    # Store new job
                    job = Job(
                        user_id=user_id,
                        title=job_data["title"],
                        company=job_data["company"],
                        location=job_data.get("location"),
                        salary=job_data.get("salary"),
                        url=job_data["url"],
                        description=job_data.get("description"),
                        score=job_data.get("score", 0.0),
                        fit_notes=job_data.get("fit_notes", ""),
                        source=job_data.get("source"),
                        scraped_at=datetime.utcnow(),
                    )
                    db.add(job)
                    new_count += 1

                db.commit()

            except Exception as e:
                logger.error(f"Scrape error for {title} in {location}: {e}", exc_info=True)

    return total_found, total_filtered, new_count
