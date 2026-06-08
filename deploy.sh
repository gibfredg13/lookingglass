#!/bin/bash
# Quick deployment script for The Analyst Lens on remote machines
# Usage: bash deploy.sh [production|staging|development]

set -e

ENVIRONMENT=${1:-production}
PROJECT_NAME="analyst-lens"
DOCKER_COMPOSE_FILE="docker-compose.yml"
ADMIN_COMPOSE_PATH="/home/admin/docker-compose.yml"
MANAGED_BEGIN="# --- lookingglass managed block: begin ---"
MANAGED_END="# --- lookingglass managed block: end ---"

if [ "$ENVIRONMENT" = "production" ]; then
    DOCKER_COMPOSE_FILE="docker-compose.prod.yml"
fi

install_or_append_admin_compose() {
    local source_file="$1"
    local target_file="$2"

    mkdir -p "$(dirname "$target_file")"

    if [ ! -f "$target_file" ]; then
        cp "$source_file" "$target_file"
        echo "✓ Installed compose file to $target_file"
        return
    fi

    # Keep this idempotent by replacing only the managed block on repeated runs.
    local tmp_file
    tmp_file=$(mktemp)

    awk -v begin="$MANAGED_BEGIN" -v end="$MANAGED_END" '
        $0 == begin {skip=1; next}
        $0 == end {skip=0; next}
        skip == 0 {print}
    ' "$target_file" > "$tmp_file"

    {
        cat "$tmp_file"
        echo ""
        echo "$MANAGED_BEGIN"
        cat "$source_file"
        echo "$MANAGED_END"
    } > "$target_file"

    rm -f "$tmp_file"
    echo "✓ Appended managed Lookingglass compose block to $target_file"
}

echo "================================"
echo "Deploying to: $ENVIRONMENT"
echo "Using: $DOCKER_COMPOSE_FILE"
echo "================================"
echo ""

# 1. Check prerequisites
echo "✓ Checking prerequisites..."
if ! command -v docker &> /dev/null; then
    echo "✗ Docker not installed. Please install Docker first."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "✗ Docker Compose not installed. Please install Docker Compose first."
    exit 1
fi

# 2. Check if .env exists
echo "✓ Checking environment configuration..."
if [ ! -f .env ]; then
    if [ "$ENVIRONMENT" = "production" ]; then
        cp .env.production .env
        echo "  Created .env from .env.production"
    else
        cp .env.example .env
        echo "  Created .env from .env.example"
    fi
    echo ""
    echo "⚠️  IMPORTANT: Edit .env with your settings before continuing!"
    echo "   nano .env"
    exit 1
fi

# 3. Install/append compose content to /home/admin/docker-compose.yml
echo "✓ Installing compose content at $ADMIN_COMPOSE_PATH..."
install_or_append_admin_compose "$DOCKER_COMPOSE_FILE" "$ADMIN_COMPOSE_PATH"

# 4. Build or pull images
echo "✓ Building/pulling Docker images..."
docker-compose -f $DOCKER_COMPOSE_FILE build --no-cache

# 5. Start services
echo "✓ Starting services..."
docker-compose -f $DOCKER_COMPOSE_FILE up -d

# 6. Wait for database to be ready
echo "✓ Waiting for database..."
sleep 5
for i in {1..30}; do
    if docker-compose -f $DOCKER_COMPOSE_FILE exec -T db pg_isready -U analyst &> /dev/null; then
        echo "  Database ready!"
        break
    fi
    if [ $i -eq 30 ]; then
        echo "✗ Database failed to start. Check logs:"
        docker-compose -f $DOCKER_COMPOSE_FILE logs db
        exit 1
    fi
    echo "  Waiting... ($i/30)"
    sleep 1
done

# 7. Run migrations
echo "✓ Running database migrations..."
docker-compose -f $DOCKER_COMPOSE_FILE exec -T api alembic upgrade head || {
    echo "✗ Migration failed. Rolling back..."
    docker-compose -f $DOCKER_COMPOSE_FILE down
    exit 1
}

# 8. Seed demo data (development only)
if [ "$ENVIRONMENT" != "production" ]; then
    echo "✓ Seeding demo data..."
    docker-compose -f $DOCKER_COMPOSE_FILE exec -T api python scripts/seed_demo.py || true
fi

# 9. Verify services
echo "✓ Verifying services..."
sleep 2
docker-compose -f $DOCKER_COMPOSE_FILE ps

# 10. Display access information
echo ""
echo "================================"
echo "✓ Deployment Complete!"
echo "================================"
echo ""
echo "Access your application:"
echo "  API:      http://localhost:8000/docs"
echo "  Frontend: http://localhost:8501"
echo ""
echo "Demo credentials:"
echo "  Email:    demo@analyst-lens.local"
echo "  Password: demo123"
echo ""
echo "Useful commands:"
echo "  docker-compose logs -f          # View logs"
echo "  docker-compose ps               # Check status"
echo "  docker-compose down             # Stop services"
echo "  docker-compose exec api bash    # Shell into API"
echo ""

