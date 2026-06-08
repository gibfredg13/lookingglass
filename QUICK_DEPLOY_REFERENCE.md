# Quick Reference: Deployment Scenarios

## 1. 🚀 Deploy on Same Network (Development/Staging)

**Recommended for:** Testing, QA, internal deployments

```bash
# 1. Clone repo
git clone <your-repo-url>
cd analyst-lens

# 2. Setup environment
cp .env.example .env
# Edit .env with your settings
nano .env

# 3. Deploy with standard compose
docker compose up -d

# 4. Run migrations
docker compose exec api alembic upgrade head

# 5. Access
# API: http://localhost:8000
# Frontend: http://localhost:8501
```

---

## 2. 🔒 Production Deployment (Ubuntu Server)

**Recommended for:** Public deployments, production environments

```bash
# 1. SSH to server
ssh user@your-server.com

# 2. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
newgrp docker

# 3. Clone repo
git clone <your-repo-url>
cd analyst-lens

# 4. Setup production environment
cp .env.production .env

# Edit with strong secrets and database passwords
nano .env

# Generate strong secret (if needed)
openssl rand -base64 32

# 5. Make deploy script executable
chmod +x deploy.sh

# 6. Run deployment
./deploy.sh production

# 7. Setup reverse proxy with Nginx (HTTPS)
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Create nginx config (see DEPLOYMENT.md for full config)
# Then:
sudo certbot certonly --standalone -d analyst-lens.yourdomain.com
```

---

## 3. ☁️ AWS Deployment (ECS Fargate + RDS)

**Recommended for:** Scalable cloud deployments

```bash
# 1. Create RDS PostgreSQL instance in AWS Console
# - Engine: PostgreSQL 16
# - DB Instance: db.t3.micro (free tier eligible)
# - Storage: 20GB
# - VPC: Default or custom VPC
# - Security Group: Allow inbound on 5432 from ECS tasks

# 2. Push images to ECR
aws ecr create-repository --repository-name analyst-lens-api
aws ecr create-repository --repository-name analyst-lens-frontend

aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com

docker tag analyst-lens-api:1.0.0 YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/analyst-lens-api:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/analyst-lens-api:latest

docker tag analyst-lens-frontend:1.0.0 YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/analyst-lens-frontend:latest
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/analyst-lens-frontend:latest

# 3. Create ECS Task Definition (JSON)
# See AWS documentation for detailed parameter setup
# Point DB connection to RDS endpoint

# 4. Create ECS Cluster and Services
# - Create cluster: "analyst-lens-prod"
# - Create service for API Task Definition (1 task, load balancer)
# - Create service for Frontend Task Definition (1 task, load balancer)

# 5. Update Route53/Load Balancer DNS to point to your domain
```

---

## 4. 🟦 Google Cloud Run Deployment

**Recommended for:** Serverless, low-maintenance deployments

```bash
# 1. Setup gcloud CLI
gcloud config set project YOUR_PROJECT_ID

# 2. Create Cloud SQL PostgreSQL
gcloud sql instances create analyst-lens-db \
  --database-version=POSTGRES_16 \
  --tier=db-f1-micro \
  --region=us-central1

gcloud sql databases create analyst_lens --instance=analyst-lens-db

# 3. Create database user
gcloud sql users create analyst --instance=analyst-lens-db --password=YOUR_STRONG_PASSWORD

# 4. Build and push images
gcloud builds submit --tag gcr.io/YOUR_PROJECT/analyst-lens-api:latest .
gcloud builds submit --tag gcr.io/YOUR_PROJECT/analyst-lens-frontend:latest ./frontend

# 5. Deploy API to Cloud Run
gcloud run deploy analyst-lens-api \
  --image gcr.io/YOUR_PROJECT/analyst-lens-api:latest \
  --platform managed \
  --region us-central1 \
  --memory 512Mi \
  --cpu 1 \
  --set-env-vars AL_DATABASE_URL="postgresql://analyst:PASSWORD@CLOUD_SQL_IP/analyst_lens" \
  --set-env-vars AL_SECRET_KEY="YOUR_GENERATED_SECRET" \
  --allow-unauthenticated

# 6. Deploy Frontend to Cloud Run
gcloud run deploy analyst-lens-frontend \
  --image gcr.io/YOUR_PROJECT/analyst-lens-frontend:latest \
  --platform managed \
  --region us-central1 \
  --memory 256Mi \
  --set-env-vars API_BASE_URL="https://analyst-lens-api-XXXX.a.run.app" \
  --allow-unauthenticated

# 7. Setup custom domain via Cloud Run dashboard
```

---

## 5. 🟥 Azure Container Instances Deployment

**Recommended for:** Azure ecosystem, enterprise deployments

```bash
# 1. Login to Azure
az login

# 2. Create resource group
az group create --name analyst-lens-rg --location eastus

# 3. Create Azure Database for PostgreSQL
az postgres server create \
  --resource-group analyst-lens-rg \
  --name analyst-lens-db \
  --location eastus \
  --admin-user analyst \
  --admin-password YOUR_STRONG_PASSWORD \
  --sku-name B_Gen5_1 \
  --storage-size 51200

# 4. Push to Azure Container Registry
az acr create --resource-group analyst-lens-rg --name analysislensacr --sku Basic

az acr build --registry analysislensacr --image analyst-lens-api:1.0.0 .
az acr build --registry analysislensacr --image analyst-lens-frontend:1.0.0 ./frontend

# 5. Deploy Container Instances
az container create \
  --resource-group analyst-lens-rg \
  --name analyst-lens-api \
  --image analysislensacr.azurecr.io/analyst-lens-api:1.0.0 \
  --cpu 1 --memory 1 \
  --port 8000 \
  --environment-variables AL_DATABASE_URL="postgresql://analyst:PASSWORD@analyst-lens-db.postgres.database.azure.com/analyst_lens" \
  --registry-login-server analysislensacr.azurecr.io \
  --registry-username <username> \
  --registry-password <password>
```

---

## 6. 🐧 Linux VPS (DigitalOcean, Linode, etc.)

**Recommended for:** Simple, cost-effective deployments

```bash
# 1. Create new Ubuntu 22.04 droplet/VPS

# 2. SSH and initial setup
sudo apt-get update && sudo apt-get upgrade -y
sudo apt-get install -y curl git

# 3. Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
exit && ssh user@your-vps.com  # Reconnect

# 4. Install Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# 5. Deploy application
git clone <your-repo-url>
cd analyst-lens
cp .env.production .env
nano .env  # Edit with your secrets

chmod +x deploy.sh
./deploy.sh production

# 6. Setup Nginx + SSL
sudo apt-get install -y nginx certbot python3-certbot-nginx

# Copy Nginx config from DEPLOYMENT.md
sudo nano /etc/nginx/sites-available/analyst-lens

sudo ln -s /etc/nginx/sites-available/analyst-lens /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Get SSL certificate
sudo certbot certonly --nginx -d analyst-lens.yourdomain.com

# Auto-renewal
sudo systemctl enable certbot.timer
```

---

## 7. 🔧 Custom Server Requirements

### Minimal Setup
- **CPU:** 1 core
- **RAM:** 1GB (2GB recommended)
- **Disk:** 20GB (for OS + database)
- **OS:** Ubuntu 20.04+, Debian 10+, CentOS 8+

### Recommended Production Setup
- **CPU:** 2+ cores
- **RAM:** 4-8GB
- **Disk:** 50GB+ SSD (can grow with data)
- **OS:** Ubuntu 22.04 LTS
- **Network:** Static IP, domain name, SSL certificate

### Network Ports
- **80** - HTTP (redirect to HTTPS)
- **443** - HTTPS (Nginx reverse proxy)
- **8000** - Internal API (Nginx backend)
- **8501** - Internal Frontend (Nginx backend)
- **5432** - PostgreSQL (internal only, not exposed)

---

## 8. 🔄 Post-Deployment Tasks

### For All Deployments

```bash
# Verify services
docker compose ps
docker compose logs -f

# Test connectivity
curl http://localhost:8000/docs
curl http://localhost:8501

# Setup backups
docker compose exec db pg_dump -U analyst analyst_lens > backup_$(date +%s).sql

# Monitor logs
docker compose logs -f api
docker compose logs -f frontend
docker compose logs -f db
```

### For Production Only

```bash
# Enable automatic restarts
# Already configured in docker-compose.prod.yml

# Setup log rotation
sudo apt-get install -y logrotate
# Create logrotate config for Docker logs

# Monitor system resources
watch -n 2 docker stats

# Setup alerts (CloudWatch, Datadog, etc.)
# Configure based on your monitoring provider

# Schedule database backups
0 2 * * * /home/user/analyst-lens/backup.sh
```

---

## 📞 Common Commands Reference

```bash
# View running containers
docker compose ps

# View logs
docker compose logs -f
docker compose logs -f api

# Execute command in container
docker compose exec api bash
docker compose exec db psql -U analyst

# Restart services
docker compose restart
docker compose restart api

# Stop services
docker compose stop
docker compose down

# Database operations
docker compose exec db pg_dump -U analyst analyst_lens > backup.sql
docker compose exec -T db psql -U analyst analyst_lens < backup.sql

# Update application
git pull
docker compose build
docker compose up -d

# View resource usage
docker stats
```

---

## ⚠️ Important Security Notes

✅ **Always:**
- Generate strong `AL_SECRET_KEY` with `openssl rand -base64 32`
- Use HTTPS in production with valid SSL certificates
- Change default database passwords
- Restrict database network access
- Use environment variables for secrets (never commit `.env`)
- Keep Docker images updated
- Enable container restart policies
- Monitor logs for suspicious activity
- Implement regular backups

❌ **Never:**
- Expose database ports to public internet
- Use default credentials
- Commit secrets to Git
- Run containers as root
- Use self-signed certificates on public sites
- Disable authentication

---

For detailed setup instructions, see **DEPLOYMENT.md**

