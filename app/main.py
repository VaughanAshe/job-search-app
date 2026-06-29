"""Main FastAPI application: routes, middleware, startup."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

from app.config import SECRET_KEY, BASE_DIR, ADMIN_EMAIL, ADMIN_PASSWORD, ENVIRONMENT
from app.db import Base, engine, get_db, SessionLocal, User, SearchConfig, Job, RunLog
from app.auth import (
    hash_password, verify_password, create_session, clear_session,
    get_current_user, require_user,
)
from app.scheduler import init_scheduler, run_user_pipeline

TEMPLATES_DIR = BASE_DIR / "app" / "templates"
STATIC_DIR = BASE_DIR / "app" / "static"

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))
STATIC_DIR.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables and start scheduler on startup."""
    Base.metadata.create_all(bind=engine)
    _create_admin_if_needed()
    init_scheduler()
    yield


app = FastAPI(title="Job Search App", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


def _create_admin_if_needed():
    """Seed an admin user from env vars if no users exist."""
    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            admin = User(
                email=ADMIN_EMAIL,
                name="Admin",
                hashed_password=hash_password(ADMIN_PASSWORD),
                is_admin=True,
            )
            db.add(admin)
            db.commit()
            print(f"Created admin user: {ADMIN_EMAIL}")
    finally:
        db.close()


# ============================
# ROUTES
# ============================

@app.api_route("/", methods=["GET", "HEAD"])
async def index(request: Request, db=Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return RedirectResponse(url="/login", status_code=303)


# --- Auth routes ---

@app.get("/register")
async def register_page(request: Request, db=Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@app.post("/register")
async def register_submit(
    request: Request,
    email: str = Form(...),
    name: str = Form(...),
    password: str = Form(...),
    db=Depends(get_db),
):
    existing = db.query(User).filter(User.email == email).first()
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "An account with this email already exists."},
        )
    user = User(email=email, name=name, hashed_password=hash_password(password))
    db.add(user)
    db.commit()
    db.refresh(user)

    # Create default search config
    config = SearchConfig(user_id=user.id)
    db.add(config)
    db.commit()

    create_session(request, user)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.get("/login")
async def login_page(request: Request, db=Depends(get_db)):
    user = get_current_user(request, db)
    if user:
        return RedirectResponse(url="/dashboard", status_code=303)
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@app.post("/login")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db=Depends(get_db),
):
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Invalid email or password."},
        )
    create_session(request, user)
    return RedirectResponse(url="/dashboard", status_code=303)


@app.post("/logout")
async def logout(request: Request):
    clear_session(request)
    return RedirectResponse(url="/login", status_code=303)


# --- Dashboard ---

@app.get("/dashboard")
async def dashboard(
    request: Request,
    db=Depends(get_db),
    user: User = Depends(require_user),
):
    # Get user's jobs, newest first, not excluded
    jobs = (
        db.query(Job)
        .filter(Job.user_id == user.id, Job.is_excluded == False)
        .order_by(Job.scraped_at.desc(), Job.score.desc())
        .limit(200)
        .all()
    )

    # Group by date
    today_jobs = [j for j in jobs if _is_today(j.scraped_at)]
    older_jobs = [j for j in jobs if not _is_today(j.scraped_at)]

    # Last run info
    last_run = (
        db.query(RunLog)
        .filter(RunLog.user_id == user.id)
        .order_by(RunLog.started_at.desc())
        .first()
    )

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": user,
            "today_jobs": today_jobs,
            "older_jobs": older_jobs[:50],
            "last_run": last_run,
            "total_jobs": len(jobs),
        },
    )


@app.post("/jobs/{job_id}/favourite")
async def toggle_favourite(
    job_id: int,
    db=Depends(get_db),
    user: User = Depends(require_user),
):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404)
    job.is_favourite = not job.is_favourite
    db.commit()
    return {"is_favourite": job.is_favourite}


@app.post("/jobs/{job_id}/exclude")
async def exclude_job(
    job_id: int,
    db=Depends(get_db),
    user: User = Depends(require_user),
):
    job = db.query(Job).filter(Job.id == job_id, Job.user_id == user.id).first()
    if not job:
        raise HTTPException(status_code=404)
    job.is_excluded = True
    db.commit()
    return {"status": "excluded"}


# --- Config ---

@app.get("/config")
async def config_page(
    request: Request,
    db=Depends(get_db),
    user: User = Depends(require_user),
):
    config = db.query(SearchConfig).filter(SearchConfig.user_id == user.id).first()
    if not config:
        config = SearchConfig(user_id=user.id)
        db.add(config)
        db.commit()
        db.refresh(config)
    return templates.TemplateResponse("config.html", {"request": request, "user": user, "config": config, "saved": False})


@app.post("/config")
async def config_save(
    request: Request,
    db=Depends(get_db),
    user: User = Depends(require_user),
    job_titles: str = Form(...),
    locations: str = Form(...),
    salary_min: int = Form(150000),
    salary_max: int = Form(0),
    exclusions: str = Form(""),
    telegram_enabled: bool = Form(False),
    telegram_chat_id: str = Form(""),
    telegram_bot_token: str = Form(""),
    run_hour: int = Form(7),
    is_active: bool = Form(False),
):
    config = db.query(SearchConfig).filter(SearchConfig.user_id == user.id).first()
    if not config:
        config = SearchConfig(user_id=user.id)
        db.add(config)

    config.job_titles = job_titles
    config.locations = locations
    config.salary_min = salary_min
    config.salary_max = salary_max if salary_max > 0 else None
    config.exclusions = exclusions
    config.telegram_enabled = telegram_enabled
    config.telegram_chat_id = telegram_chat_id or None
    config.telegram_bot_token = telegram_bot_token or None
    config.run_hour = run_hour
    config.is_active = is_active

    db.commit()
    return templates.TemplateResponse("config.html", {"request": request, "user": user, "config": config, "saved": True})


# --- Manual run trigger ---

@app.post("/run-now")
async def run_now(
    db=Depends(get_db),
    user: User = Depends(require_user),
):
    """Trigger an immediate pipeline run for this user."""
    import threading
    thread = threading.Thread(target=run_user_pipeline, args=(user.id,), daemon=True)
    thread.start()
    return RedirectResponse(url="/dashboard?refresh=1", status_code=303)


# --- Health check ---

@app.get("/health")
async def health():
    return {"status": "ok", "environment": ENVIRONMENT}


# --- Helpers ---

def _is_today(dt) -> bool:
    from datetime import datetime
    return dt.date() == datetime.utcnow().date() if dt else False
