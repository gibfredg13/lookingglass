# SCP to Remote Server - File Manifest

Complete list of files you need to copy to your remote server and the exact SCP commands.

---

## 📋 Files Needed on Remote Server

### Minimal Required Files
```
analyst-lens/
├── app/                           # Backend application
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── db.py
│   ├── models.py
│   ├── schemas.py
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── auth.py
│   │   ├── dependencies.py
│   │   ├── ask.py
│   │   ├── events.py
│   │   ├── intelligence.py
│   │   ├── outlooks.py
│   │   ├── scenarios.py
│   │   └── stories.py
│   └── services/
│       ├── __init__.py
│       ├── auth.py
│       ├── intelligence.py
│       ├── ask_anything.py
│       └── outlook_engine.py
│
├── frontend/                      # Streamlit frontend
│   ├── app.py
│   ├── api_client.py
│   ├── config.py
│   ├── requirements.txt
│   └── Dockerfile
│
├── alembic/                       # Database migrations
│   ├── versions/
│   │   ├── 0001_initial.py
│   │   ├── 0002_phase3_features.py
│   │   └── 0003_ai_intelligence.py
│   ├── env.py
│   ├── script.py.mako
│   └── ini (see below)
│
├── scripts/                       # Utility scripts
│   └── seed_demo.py
│
├── docker-compose.yml             # Development compose
├── docker-compose.prod.yml        # ✨ Production compose (NEEDED!)
├── Dockerfile                     # API Dockerfile
├── pyproject.toml                 # Python dependencies
├── alembic.ini                    # Alembic configuration
├── .env.production                # ✨ Production env template (NEEDED!)
├── .env.example                   # Dev env (optional)
├── deploy.sh                      # ✨ Deployment script (NEEDED!)
├── README.md
├── AGENTS.md
├── DEPLOYMENT.md                  # ✨ Reference guide (optional but recommended)
├── QUICK_DEPLOY_REFERENCE.md      # ✨ Command reference (optional but recommended)
└── .gitignore
```

### What You Absolutely Need ✅
- `app/` - entire directory
- `frontend/` - entire directory (with Dockerfile, requirements.txt)
- `alembic/` - entire directory with migrations
- `scripts/` - entire directory
- `pyproject.toml` - dependencies
- `alembic.ini` - alembic config
- `Dockerfile` - API container
- `docker-compose.prod.yml` - production setup **KEY FILE**
- `.env.production` or `.env` - environment config **KEY FILE**
- `deploy.sh` - deployment script (optional but recommended)

### What You CAN Skip
- `.git/` - don't copy (use git clone instead)
- `venv/` - don't copy (will be rebuilt in container)
- `data/` - SQLite database (will be created)
- `__pycache__/` - don't copy
- `.egg-info/` - don't copy
- Development docs (optional, but helpful)

---

## 🚀 Quick SCP Commands

### Option A: Copy Individual Files (Minimal)

```bash
# Set variables for your server
REMOTE_USER="your_username"
REMOTE_HOST="your-server.com"
REMOTE_PATH="/home/$REMOTE_USER/analyst-lens"

# Create remote directory
ssh $REMOTE_USER@$REMOTE_HOST "mkdir -p $REMOTE_PATH"

# Copy essential files and directories
scp -r app $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/
scp -r frontend $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/
scp -r alembic $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/
scp -r scripts $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/

# Copy configuration files
scp pyproject.toml $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/
scp alembic.ini $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/
scp Dockerfile $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/
scp docker-compose.prod.yml $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/
scp docker-compose.yml $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/
scp .env.production $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/.env

# Copy deployment script
scp deploy.sh $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/
ssh $REMOTE_USER@$REMOTE_HOST "chmod +x $REMOTE_PATH/deploy.sh"

# Optional: Copy docs
scp DEPLOYMENT.md $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/
scp QUICK_DEPLOY_REFERENCE.md $REMOTE_USER@$REMOTE_HOST:$REMOTE_PATH/
```

### Option B: Clone from Git (Recommended)

This is better if your repo is on GitHub/GitLab:

```bash
# SSH to remote
ssh your_username@your-server.com

# Clone the repository
git clone https://github.com/your-org/analyst-lens.git
cd analyst-lens

# Copy production env template
cp .env.production .env

# Edit with your settings
nano .env

# Run deployment
chmod +x deploy.sh
./deploy.sh production
```

### Option C: Tar Archive (For Complex Transfers)

```bash
# On your local machine
tar -czf analyst-lens.tar.gz \
  --exclude=venv \
  --exclude=__pycache__ \
  --exclude=.git \
  --exclude=.env \
  --exclude=data \
  --exclude=*.egg-info \
  app/ frontend/ alembic/ scripts/ \
  pyproject.toml alembic.ini Dockerfile \
  docker-compose.yml docker-compose.prod.yml \
  .env.production deploy.sh

# Copy to remote
scp analyst-lens.tar.gz your_username@your-server.com:~/

# On remote server
tar -xzf analyst-lens.tar.gz
cd analyst-lens
cp .env.production .env
nano .env  # Edit settings
./deploy.sh production
```

---

## 📋 Post-SCP Checklist

After copying files to remote server:

```bash
# SSH to remote
ssh your_username@your-server.com

# Go to project directory
cd analyst-lens

# ✅ Verify files are there
ls -la

# ✅ Create/edit .env
cp .env.production .env
nano .env
# Edit: AL_SECRET_KEY, AL_DATABASE_URL password, optional OPENAI_API_KEY

# ✅ Make deploy script executable
chmod +x deploy.sh

# ✅ Install Docker if needed
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
exit && ssh your_username@your-server.com  # Reconnect

# ✅ Run deployment
./deploy.sh production

# ✅ Verify
docker compose ps
docker compose logs -f
curl http://localhost:8000/docs
```

---

## 🔍 Verify Files on Remote

After SCP, verify everything is there:

```bash
# SSH to remote
ssh your_username@your-server.com
cd analyst-lens

# Check essential directories exist
ls -d app frontend alembic scripts

# Check key files exist
ls -l docker-compose*.yml pyproject.toml Dockerfile alembic.ini

# Check size (should be ~50-100MB total, not including data)
du -sh .
```

---

## 📊 File Size Reference

Typical sizes for what you're copying:

```
app/                    ~2 MB
frontend/               ~0.5 MB
alembic/                ~0.1 MB
scripts/                ~0.05 MB
Configuration files     ~0.1 MB
─────────────────────────────
Total (to SCP):         ~2.8 MB

After Docker build:     ~1.5-2 GB
  (includes Python, deps, compiled code)
```

---

## 🔐 Security Notes

### What NOT to Copy to Remote

❌ **Don't SCP these files:**
- `.env` with development secrets (create fresh on remote)
- `venv/` directory (will be rebuilt)
- `.git/` (use `git clone` instead)
- `data/` SQLite database (will be created)
- `__pycache__/` directories
- `.egg-info/` directories

### Safe Practices

✅ **DO:**
- Copy `.env.production` as template
- Let remote `.env` be created and edited by you
- SCP individual files not entire `.git` directories
- Use `chmod 600 .env` on remote to protect it
- Verify file ownership after SCP:
  ```bash
  chown -R $USER:$USER analyst-lens/
  ```

---

## 💾 Example: Complete Deploy Flow

```bash
# Your local machine
cd /path/to/analyst-lens

# 1. Create tar archive
tar -czf analyst-lens.tar.gz \
  --exclude=venv --exclude=__pycache__ \
  --exclude=.git --exclude=.env --exclude=data \
  app/ frontend/ alembic/ scripts/ \
  *.py *.toml *.ini Dockerfile docker-compose* \
  .env.production deploy.sh

# 2. SCP to remote
scp analyst-lens.tar.gz user@server.com:~/

# Your remote server
ssh user@server.com

# 3. Extract
tar -xzf analyst-lens.tar.gz
cd analyst-lens

# 4. Setup
cp .env.production .env
nano .env  # Edit with strong passwords and secrets

# 5. Install Docker (if not already)
curl -fsSL https://get.docker.com | sh && \
sudo usermod -aG docker $USER && \
exit

# Reconnect after adding to docker group
ssh user@server.com
cd analyst-lens

# 6. Deploy
chmod +x deploy.sh
./deploy.sh production

# 7. Verify
docker compose ps
docker compose logs api

# Your app is now running!
# Access at http://server.com:8000 (API)
#           http://server.com:8501 (Frontend)
```

---

## 🎯 If Using Git (Better Option)

If your repo is on GitHub/GitLab:

```bash
# Much simpler!
ssh user@server.com

git clone https://github.com/your-org/analyst-lens.git
cd analyst-lens

cp .env.production .env
nano .env

chmod +x deploy.sh
./deploy.sh production

# Done!
```

---

## ❓ FAQ

**Q: Should I copy .env to remote?**
A: No, copy `.env.production` as template, then create fresh `.env` on remote with your secrets.

**Q: Do I need git?**
A: Not required, but recommended - you can just SCP files.

**Q: What if SCP takes too long?**
A: Use tar archive method (Option C) - faster for large directories.

**Q: How do I know what to SCP?**
A: Everything in "Minimal Required Files" section above.

**Q: Can I SCP just the app/ directory and keep rest?**
A: No, you need all: app/, frontend/, alembic/, configuration files, Dockerfiles.

---

## ✅ TL;DR - Fastest Way

```bash
# Clone from Git (easiest)
ssh user@server.com
git clone https://github.com/your-org/analyst-lens.git && cd analyst-lens

# Or tar archive (if no git)
cd /local/analyst-lens && tar -czf ../al.tar.gz . --exclude=venv && \
scp ../al.tar.gz user@server.com:~ && \
ssh user@server.com 'tar -xzf al.tar.gz && cd analyst-lens'

# Then:
cp .env.production .env && nano .env && chmod +x deploy.sh && ./deploy.sh production
```

Done in 5 minutes! 🚀

