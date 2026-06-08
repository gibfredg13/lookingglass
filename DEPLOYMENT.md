# Deployment Guide: The Analyst Lens

Complete instructions for containerizing and deploying to a remote machine.

---

## Prerequisites

- **Docker & Docker Compose** installed on remote machine
- **Git** for version control
- Remote machine with **2GB+ RAM** (4GB+ recommended)
- **Port 8000** (API), **8501** (Frontend), **5432** (Database) available

---

## 🚀 Quick Start Deployment (Docker Compose)

### 1. Clone Repository on Remote Machine

```bash
# SSH into your remote machine
ssh user@your-remote-host

# Clone the repository
git clone <your-repo-url> analyst-lens
cd analyst-lens
```

### 2. Configure Environment

```bash
# Copy and edit the environment file
cp .env.example .env

# Edit with your settings
nano .env
```

**Production .env Example:**
```dotenv
# Database Configuration (PostgreSQL)
AL_DATABASE_URL=postgresql://analyst:secure_password_here@db:5432/analyst_lens

# JWT Secret (generate with: openssl rand -base64 32)
AL_SECRET_KEY=your_generated_secret_key_here

# Session timeout (minutes)
AL_ACCESS_TOKEN_EXPIRE_MINUTES=120

# Optional: OpenAI API for AI features
OPENAI_API_KEY=sk-your-api-key-here
```

### 3. Build & Start Containers

```bash
# Build images and start all services
docker compose up -d

# Verify services are running
docker compose ps

# Check logs
docker compose logs -f
```

### 4. Initialize Database (First Time Only)

```bash
# Run migrations in the API container
docker compose exec api alembic upgrade head

# (Optional) Seed demo data
docker compose exec api python scripts/seed_demo.py
```

### 5. Access the Application

- **API**: `http://your-remote-host:8000`
  - Swagger docs: `http://your-remote-host:8000/docs`
- **Frontend**: `http://your-remote-host:8501`

**Demo Login:**
- Email: `demo@analyst-lens.local`
- Password: `demo123`

---

## 📦 Manual Docker Build (For CI/CD or Custom Registries)

### Build Images Locally

```bash
# Build API image
docker build -t analyst-lens-api:1.0.0 .

# Build Frontend image
docker build -t analyst-lens-frontend:1.0.0 ./frontend

# Tag for registry (e.g., Docker Hub)
docker tag analyst-lens-api:1.0.0 your-registry/analyst-lens-api:1.0.0
docker tag analyst-lens-frontend:1.0.0 your-registry/analyst-lens-frontend:1.0.0

# Push to registry
docker push your-registry/analyst-lens-api:1.0.0
docker push your-registry/analyst-lens-frontend:1.0.0
```

### Run with Pre-built Images

Create a `docker-compose.prod.yml`:

```yaml
services:
  db:
    image: postgres:16-alpine
    container_name: analyst_lens_db
    environment:
      POSTGRES_USER: analyst
      POSTGRES_PASSWORD: ${DB_PASSWORD:-analyst}
      POSTGRES_DB: analyst_lens
    ports:
      - "5432:5432"
    volumes:
      - /data/pgdata:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U analyst"]
      interval: 5s
      timeout: 5s
      retries: 5

  api:
    image: your-registry/analyst-lens-api:1.0.0
    container_name: analyst_lens_api
    environment:
      AL_DATABASE_URL: postgresql://analyst:${DB_PASSWORD:-analyst}@db:5432/analyst_lens
      AL_SECRET_KEY: ${AL_SECRET_KEY}
      AL_ACCESS_TOKEN_EXPIRE_MINUTES: ${ACCESS_TOKEN_EXPIRE:-120}
      OPENAI_API_KEY: ${OPENAI_API_KEY:-}
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy
    restart: unless-stopped

  frontend:
    image: your-registry/analyst-lens-frontend:1.0.0
    container_name: analyst_lens_frontend
    environment:
      API_BASE_URL: http://api:8000
    ports:
      - "8501:8501"
    depends_on:
      - api
    restart: unless-stopped

volumes:
  pgdata:
```

Then deploy:
```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d
```

---

## ☁️ Cloud Deployments

### AWS (ECS + RDS)

1. **Create RDS PostgreSQL instance** (skip Docker/Compose database)
2. **Update docker-compose**:
   ```yaml
   # Remove 'db' service, keep only 'api' and 'frontend'
   environment:
     AL_DATABASE_URL: postgresql://analyst:password@your-rds-endpoint:5432/analyst_lens
   ```
3. **Push to ECR**:
   ```bash
   aws ecr get-login-password | docker login --username AWS --password-stdin your-account.dkr.ecr.region.amazonaws.com
   docker tag analyst-lens-api:1.0.0 your-account.dkr.ecr.region.amazonaws.com/analyst-lens-api:latest
   docker push your-account.dkr.ecr.region.amazonaws.com/analyst-lens-api:latest
   ```
4. **Deploy via CloudFormation or CDK** pointing to ECR images

### Google Cloud (Cloud Run + Cloud SQL)

1. **Create Cloud SQL PostgreSQL instance**
2. **Deploy API to Cloud Run**:
   ```bash
   gcloud run deploy analyst-lens-api \
     --image gcr.io/YOUR_PROJECT/analyst-lens-api:1.0.0 \
     --set-env-vars AL_DATABASE_URL=postgresql://... \
     --allow-unauthenticated
   ```
3. **Deploy Frontend similarly**

### Azure (Container Instances + PostgreSQL)

1. **Create Azure Database for PostgreSQL**
2. **Push to Azure Container Registry**:
   ```bash
   az login
   az acr build --registry myregistry --image analyst-lens-api:1.0.0 .
   ```
3. **Deploy Container Instances** with the ACR image

---

## 🔒 Security Considerations

### Before Production Deployment

1. **Generate Strong Secret**:
   ```bash
   openssl rand -base64 32
   ```
   Use this as `AL_SECRET_KEY` in `.env`

2. **Change Database Password**:
   ```bash
   # Update in .env before first docker compose up
   DB_PASSWORD=your_very_strong_password_here
   ```

3. **Enable HTTPS**:
   - Use **nginx reverse proxy** or **Caddy** in front of Streamlit/FastAPI
   - Add SSL certificates (Let's Encrypt)

4. **Network Security**:
   - Restrict ports with firewall (only 80, 443 publicly)
   - Use VPC/Private networks for database

5. **Environment Variables**:
   - Never commit `.env` to Git
   - Use secrets management (AWS Secrets Manager, Vault, etc.)
   - Rotate `AL_SECRET_KEY` periodically

Example nginx config:
```nginx
server {
    listen 443 ssl http2;
    server_name analyst-lens.yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/analyst-lens.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/analyst-lens.yourdomain.com/privkey.pem;

    location / {
        proxy_pass http://localhost:8501;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
    }
}
```

---

## 🛠️ Common Management Tasks

### View Logs

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f api
docker compose logs -f frontend
docker compose logs -f db
```

### Restart Services

```bash
# Restart all
docker compose restart

# Restart specific
docker compose restart api
```

### Stop Services

```bash
docker compose down

# Keep data volumes
docker compose down --volumes false
```

### Scale API (with load balancer)

```bash
# Run 3 API instances
docker compose up -d --scale api=3
```

### Database Backup

```bash
# Backup PostgreSQL
docker compose exec db pg_dump \
  -U analyst analyst_lens > backup_$(date +%s).sql

# Restore from backup
docker compose exec -T db psql \
  -U analyst analyst_lens < backup_1717939200.sql
```

### Check Database Connection

```bash
docker compose exec db psql -U analyst -d analyst_lens -c "\dt"
```

---

## ✅ Health Checks & Monitoring

### Check Service Health

```bash
# API health
curl http://your-remote-host:8000/health || curl http://your-remote-host:8000/docs

# Frontend access
curl http://your-remote-host:8501

# Database health
docker compose exec db pg_isready -U analyst
```

### Enable Container Restart Policy

Already configured in `docker-compose.yml`:
```yaml
services:
  api:
    restart: unless-stopped
  frontend:
    restart: unless-stopped
```

### Monitor Disk & Memory

```bash
docker stats

docker system df

# Cleanup unused images/containers (caution!)
docker system prune -a
```

---

## 🔄 Updating the Application

```bash
# Pull latest code
git pull origin main

# Rebuild images
docker compose build

# Restart services with new images
docker compose up -d

# Check migrations ran
docker compose logs api | grep "alembic"
```

---

## 🚨 Troubleshooting

### Port Already in Use

```bash
# Find process using port 8000
lsof -i :8000

# Kill it
kill -9 <PID>

# Or change port in docker-compose.yml
```

### Database Connection Issues

```bash
# Check if DB is healthy
docker compose ps

# Manually test connection
docker compose exec api python -c "from app.db import engine; print(engine.connect())"
```

### Frontend Can't Connect to API

```bash
# Check if API is running
docker compose exec frontend curl http://api:8000/docs

# Review frontend config
docker compose logs frontend
```

### Out of Disk Space

```bash
# Check usage
df -h

# Clean Docker
docker system prune -a --volumes
```

---

## 📋 Deployment Checklist

- [ ] Reserve static IP or domain name
- [ ] Install Docker and Docker Compose
- [ ] Clone repository
- [ ] Create `.env` with strong secrets
- [ ] Build/pull Docker images
- [ ] Run `docker compose up -d`
- [ ] Run database migrations
- [ ] Verify all services running: `docker compose ps`
- [ ] Test API: `curl http://host:8000/docs`
- [ ] Test Frontend: Navigate to `http://host:8501`
- [ ] Setup firewall rules (allow 80, 443 if using HTTPS)
- [ ] Setup SSL certificates
- [ ] Configure backup strategy
- [ ] Setup monitoring/alerting
- [ ] Document access credentials securely

---

## 📚 Additional Resources

- [Docker Compose Documentation](https://docs.docker.com/compose/)
- [FastAPI Deployment Guide](https://fastapi.tiangolo.com/deployment/)
- [Streamlit Deployment Guide](https://docs.streamlit.io/deploy)
- [PostgreSQL Docker Image](https://hub.docker.com/_/postgres)

---

For questions or issues, check logs with `docker compose logs -f` and review the main project AGENTS.md guide.

