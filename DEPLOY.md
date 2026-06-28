# Deploying Job Search App to VPS

## Prerequisites

- Docker and Docker Compose installed on the VPS
- Domain DNS configured: `jobs.vaughanashe.ai` A record pointing to `191.101.81.160`
- SSH access as `vaughan`

## Steps

### 1. DNS Setup

Add an A record:
```
jobs.vaughanashe.ai  →  191.101.81.160
```

### 2. Deploy on the VPS

```bash
ssh vaughan@191.101.81.160

# Clone the repo
cd /opt
git clone https://github.com/VaughanAshe/job-search-app.git
cd job-search-app

# Create .env
cp .env.example .env
# Edit .env: set SECRET_KEY, ADMIN_EMAIL, ADMIN_PASSWORD
nano .env

# Build and start
docker compose up -d --build

# Check it's running
docker compose logs -f
curl http://localhost:8001/health
```

### 3. Configure Caddy (reverse proxy with auto-SSL)

The VPS uses Caddy for vaughanashe.ai. Add this site to the Caddyfile:

```bash
sudo nano /etc/caddy/Caddyfile
```

Add:
```
jobs.vaughanashe.ai {
    reverse_proxy localhost:8001
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        X-Content-Type-Options nosniff
        X-Frame-Options DENY
    }
}
```

Reload Caddy:
```bash
sudo systemctl reload caddy
```

### 4. Verify

```bash
curl https://jobs.vaughanashe.ai/health
```

Should return `{"status":"ok","environment":"production"}`.

### 5. First login

Go to https://jobs.vaughanashe.ai/login and sign in with the admin credentials from `.env`.

## Maintenance

```bash
# View logs
docker compose logs -f

# Restart
docker compose restart

# Update (after pushing new code to GitHub)
cd /opt/job-search-app
git pull
docker compose up -d --build

# Stop
docker compose down
```

## Backup

The SQLite database lives in `./data/jobs.db`. Back up:
```bash
cp data/jobs.db data/jobs-backup-$(date +%Y%m%d).db
```
