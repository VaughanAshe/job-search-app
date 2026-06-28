"""Scheduler: runs the job-search pipeline daily for each active user."""

import logging
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

from app.db import SessionLocal, SearchConfig, User, Job, RunLog

logger = logging.getLogger(__name__)
scheduler = None


def init_scheduler():
    """Initialise the APScheduler and schedule daily runs."""
    global scheduler
    if scheduler:
        return

    scheduler = BackgroundScheduler()
    scheduler.start()
    logger.info("Scheduler started")

    # Hourly check: find users whose run_hour matches current hour and run their pipeline
    scheduler.add_job(
        _check_and_run,
        trigger="cron",
        minute=5,  # 5 past each hour
        id="hourly_check",
        replace_existing=True,
    )


def _check_and_run():
    """Check which users need a pipeline run this hour and execute."""
    db = SessionLocal()
    try:
        current_hour = datetime.utcnow().hour
        active_configs = (
            db.query(SearchConfig)
            .filter(SearchConfig.is_active == True)
            .filter(SearchConfig.run_hour == current_hour)
            .all()
        )
        for config in active_configs:
            # Prevent double-run: check if already ran today
            today = datetime.utcnow().date()
            already_ran = (
                db.query(RunLog)
                .filter(RunLog.user_id == config.user_id)
                .filter(RunLog.started_at >= today)
                .filter(RunLog.status == "completed")
                .first()
            )
            if not already_ran:
                run_user_pipeline(config.user_id)
    except Exception as e:
        logger.error(f"Scheduler error: {e}")
    finally:
        db.close()


def run_user_pipeline(user_id: int):
    """Execute the full pipeline for a single user.

    This wraps the existing pipeline code: scrape -> score -> enrich -> store.
    """
    db = SessionLocal()
    run_log = RunLog(user_id=user_id, status="running")
    db.add(run_log)
    db.commit()
    db.refresh(run_log)

    try:
        config = db.query(SearchConfig).filter(SearchConfig.user_id == user_id).first()
        user = db.query(User).filter(User.id == user_id).first()
        if not config or not user:
            run_log.status = "failed"
            run_log.error = "No config or user found"
            db.commit()
            return

        # Parse config
        job_titles = [t.strip() for t in (config.job_titles or "").split(",") if t.strip()]
        locations = [l.strip() for l in (config.locations or "").split(",") if l.strip()]
        exclusions = [e.strip() for e in (config.exclusions or "").split(",") if e.strip()]

        logger.info(f"Starting pipeline for user {user.email}: titles={job_titles}, locations={locations}")

        # Import pipeline modules (adapted from the original repo)
        from app.pipeline.service import scrape_and_score

        found, filtered, new_jobs = scrape_and_score(
            db=db,
            user_id=user_id,
            job_titles=job_titles,
            locations=locations,
            salary_min=config.salary_min,
            salary_max=config.salary_max,
            exclusions=exclusions,
        )

        run_log.jobs_found = found
        run_log.jobs_filtered = filtered
        run_log.jobs_new = new_jobs
        run_log.status = "completed"
        run_log.finished_at = datetime.utcnow()
        db.commit()

        logger.info(f"Pipeline complete for {user.email}: found={found}, new={new_jobs}")

    except Exception as e:
        logger.error(f"Pipeline failed for user {user_id}: {e}", exc_info=True)
        run_log.status = "failed"
        run_log.error = str(e)
        run_log.finished_at = datetime.utcnow()
        db.commit()
    finally:
        db.close()
