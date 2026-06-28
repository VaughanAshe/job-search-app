# Job Search App

Multi-user web application for AI-assisted job search. Built on top of the
[job-search-pipeline](https://github.com/VaughanAshe/job-search-pipeline).

## Features

- User registration and login (multiple users, each with their own search config)
- Daily automated job scraping, scoring, and enrichment
- Dashboard showing ranked job matches
- Configurable search parameters (titles, locations, salary range, exclusions)
- Optional Telegram delivery
- CV/cover-letter renderer per role

## Tech Stack

- **Backend:** FastAPI (Python 3.12)
- **Database:** SQLite (upgradeable to PostgreSQL)
- **Frontend:** Server-rendered Jinja2 templates + Tailwind CSS (CDN)
- **Scheduling:** APScheduler (daily pipeline runs)
- **Scraping:** Playwright (headless Chromium)
- **Reverse Proxy:** Caddy (auto-SSL)
- **Containerisation:** Docker + Docker Compose

## Local Development

```bash
# Clone with submodules (pulls in the pipeline code)
git clone --recurse-submodules https://github.com/VaughanAshe/job-search-app.git
cd job-search-app

# Create virtualenv and install deps
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium

# Set up environment
cp .env.example .env       # then edit .env with your settings

# Initialise the database
python -m app.db.init_db

# Run the dev server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit http://localhost:8000

## Deployment

See [DEPLOY.md](DEPLOY.md) for VPS deployment instructions.

## License

MIT - free to use, modify, and distribute.
