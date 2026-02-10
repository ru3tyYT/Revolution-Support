#!/usr/bin/env bash
#
# Discord Support Bot - One-Command Setup Script
# Usage: ./scripts/setup.sh
#

set -euo pipefail

# =============================================================================
# COLORS AND OUTPUT FORMATTING
# =============================================================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
MAGENTA='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# =============================================================================
# LOGGING FUNCTIONS
# =============================================================================

log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

log_step() {
    echo -e "\n${CYAN}${BOLD}➜ $1${NC}"
}

log_prompt() {
    echo -e "${MAGENTA}[PROMPT]${NC} $1"
}

# Progress spinner
spinner() {
    local pid=$1
    local delay=0.1
    local spinstr='|/-\\'
    while [ -d /proc/$pid ]; do
        local temp=${spinstr#?}
        printf " [%c]  " "$spinstr"
        local spinstr=$temp${spinstr%"$temp"}
        sleep $delay
        printf "\b\b\b\b\b\b"
    done
    printf "    \b\b\b\b"
}

# =============================================================================
# CONFIGURATION
# =============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_DIR/.env"
ENV_EXAMPLE="$PROJECT_DIR/.env.example"
COMPOSE_FILE="$PROJECT_DIR/docker-compose.single.yml"
REQUIRED_PYTHON_VERSION="3.11"

# =============================================================================
# PREREQUISITE CHECKS
# =============================================================================

check_prerequisites() {
    log_step "Checking Prerequisites"
    
    local all_passed=true
    
    # Check Python version
    log_info "Checking Python version..."
    if command -v python3 &> /dev/null; then
        PYTHON_VERSION=$(python3 --version 2>&1 | awk '{print $2}')
        REQUIRED_MAJOR=$(echo "$REQUIRED_PYTHON_VERSION" | cut -d. -f1)
        REQUIRED_MINOR=$(echo "$REQUIRED_PYTHON_VERSION" | cut -d. -f2)
        CURRENT_MAJOR=$(echo "$PYTHON_VERSION" | cut -d. -f1)
        CURRENT_MINOR=$(echo "$PYTHON_VERSION" | cut -d. -f2)
        
        if [ "$CURRENT_MAJOR" -gt "$REQUIRED_MAJOR" ] || 
           ([ "$CURRENT_MAJOR" -eq "$REQUIRED_MAJOR" ] && [ "$CURRENT_MINOR" -ge "$REQUIRED_MINOR" ]); then
            log_success "Python $PYTHON_VERSION found (>= $REQUIRED_PYTHON_VERSION)"
        else
            log_error "Python $PYTHON_VERSION found, but $REQUIRED_PYTHON_VERSION+ required"
            all_passed=false
        fi
    else
        log_error "Python 3 not found. Please install Python $REQUIRED_PYTHON_VERSION or higher."
        all_passed=false
    fi
    
    # Check Docker
    log_info "Checking Docker..."
    if command -v docker &> /dev/null; then
        DOCKER_VERSION=$(docker --version | awk '{print $3}' | sed 's/,//')
        log_success "Docker $DOCKER_VERSION found"
        
        # Check if Docker daemon is running
        if docker info &> /dev/null; then
            log_success "Docker daemon is running"
        else
            log_error "Docker daemon is not running. Please start Docker."
            all_passed=false
        fi
    else
        log_error "Docker not found. Please install Docker: https://docs.docker.com/get-docker/"
        all_passed=false
    fi
    
    # Check Docker Compose
    log_info "Checking Docker Compose..."
    if command -v docker-compose &> /dev/null; then
        COMPOSE_VERSION=$(docker-compose --version | awk '{print $3}' | sed 's/,//')
        log_success "Docker Compose $COMPOSE_VERSION found"
    elif docker compose version &> /dev/null; then
        COMPOSE_VERSION=$(docker compose version --short)
        log_success "Docker Compose (plugin) $COMPOSE_VERSION found"
    else
        log_error "Docker Compose not found. Please install Docker Compose."
        all_passed=false
    fi
    
    if [ "$all_passed" = false ]; then
        echo ""
        log_error "Prerequisites check failed. Please install missing dependencies and try again."
        exit 1
    fi
    
    log_success "All prerequisites satisfied!"
}

# =============================================================================
# ENVIRONMENT SETUP
# =============================================================================

setup_environment() {
    log_step "Setting Up Environment"
    
    if [ -f "$ENV_FILE" ]; then
        log_warning ".env file already exists"
        read -p "Do you want to reconfigure? (y/N): " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "Keeping existing .env file"
            return
        fi
        cp "$ENV_FILE" "$ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
        log_info "Backup created: $ENV_FILE.backup.$(date +%Y%m%d_%H%M%S)"
    fi
    
    # Copy example file
    if [ ! -f "$ENV_EXAMPLE" ]; then
        log_error ".env.example not found at $ENV_EXAMPLE"
        exit 1
    fi
    
    cp "$ENV_EXAMPLE" "$ENV_FILE"
    log_success "Created .env file from template"
    
    # Interactive configuration
    configure_discord
    configure_database
    configure_ai_provider
    configure_optional
    
    log_success "Environment configuration complete!"
}

configure_discord() {
    echo ""
    echo -e "${BOLD}${CYAN}Discord Bot Configuration${NC}"
    echo "─────────────────────────────────────────"
    
    log_prompt "Enter your Discord Bot Token (from Discord Developer Portal):"
    read -r DISCORD_TOKEN
    while [ -z "$DISCORD_TOKEN" ]; do
        log_error "Discord Token is required"
        log_prompt "Enter your Discord Bot Token:"
        read -r DISCORD_TOKEN
    done
    sed -i.bak "s|^DISCORD_TOKEN=.*|DISCORD_TOKEN=$DISCORD_TOKEN|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
    
    log_prompt "Enter your Discord Application ID (optional, press Enter to skip):"
    read -r DISCORD_APP_ID
    if [ -n "$DISCORD_APP_ID" ]; then
        sed -i.bak "s|^DISCORD_APPLICATION_ID=.*|DISCORD_APPLICATION_ID=$DISCORD_APP_ID|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
    fi
    
    log_prompt "Enter bot command prefix (default: !):"
    read -r BOT_PREFIX
    BOT_PREFIX=${BOT_PREFIX:-!}
    sed -i.bak "s|^BOT_PREFIX=.*|BOT_PREFIX=$BOT_PREFIX|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
    
    log_success "Discord configuration saved"
}

configure_database() {
    echo ""
    echo -e "${BOLD}${CYAN}Database Configuration${NC}"
    echo "─────────────────────────────────────────"
    
    log_prompt "Enter PostgreSQL password (or press Enter for random):"
    read -r POSTGRES_PASSWORD
    if [ -z "$POSTGRES_PASSWORD" ]; then
        POSTGRES_PASSWORD=$(openssl rand -base64 32 2>/dev/null || python3 -c "import secrets; print(secrets.token_urlsafe(32))")
        log_info "Generated random password"
    fi
    
    # Update docker-compose.single.yml with password
    if [ -f "$COMPOSE_FILE" ]; then
        sed -i.bak "s|POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$POSTGRES_PASSWORD|" "$COMPOSE_FILE" && rm -f "$COMPOSE_FILE.bak"
    fi
    
    # Update .env with connection string
    sed -i.bak "s|DATABASE_URL=.*|DATABASE_URL=postgresql://postgres:$POSTGRES_PASSWORD@localhost:5432/supportbot|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
    sed -i.bak "s|VECTOR_DB_URL=.*|VECTOR_DB_URL=postgresql://postgres:$POSTGRES_PASSWORD@localhost:5432/supportbot|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
    
    log_success "Database configuration saved"
}

configure_ai_provider() {
    echo ""
    echo -e "${BOLD}${CYAN}AI Provider Configuration${NC}"
    echo "─────────────────────────────────────────"
    
    echo "Select your AI provider:"
    echo "  1) OpenAI (GPT-4, GPT-3.5)"
    echo "  2) Anthropic (Claude)"
    echo "  3) Groq (Fast, Affordable)"
    echo "  4) OpenRouter (Multiple Models)"
    echo "  5) Ollama (Self-hosted)"
    
    log_prompt "Enter choice (1-5):"
    read -r provider_choice
    
    case $provider_choice in
        1)
            log_prompt "Enter your OpenAI API Key (sk-...):"
            read -r API_KEY
            sed -i.bak "s|^OPENAI_API_KEY=.*|OPENAI_API_KEY=$API_KEY|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
            sed -i.bak "s|^DEFAULT_MODEL=.*|DEFAULT_MODEL=gpt-4o-mini|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
            log_success "OpenAI configured"
            ;;
        2)
            log_prompt "Enter your Anthropic API Key (sk-ant-...):"
            read -r API_KEY
            sed -i.bak "s|^ANTHROPIC_API_KEY=.*|ANTHROPIC_API_KEY=$API_KEY|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
            sed -i.bak "s|^DEFAULT_MODEL=.*|DEFAULT_MODEL=claude-3-haiku-20240307|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
            sed -i.bak "s|^EMBEDDING_PROVIDER=.*|EMBEDDING_PROVIDER=openai|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
            log_success "Anthropic configured (OpenAI embeddings recommended)"
            ;;
        3)
            log_prompt "Enter your Groq API Key (gsk_...):"
            read -r API_KEY
            sed -i.bak "s|^GROQ_API_KEY=.*|GROQ_API_KEY=$API_KEY|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
            sed -i.bak "s|^DEFAULT_MODEL=.*|DEFAULT_MODEL=llama3-8b-8192|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
            log_success "Groq configured"
            ;;
        4)
            log_prompt "Enter your OpenRouter API Key (sk-or-...):"
            read -r API_KEY
            sed -i.bak "s|^OPENROUTER_API_KEY=.*|OPENROUTER_API_KEY=$API_KEY|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
            sed -i.bak "s|^DEFAULT_MODEL=.*|DEFAULT_MODEL=openai/gpt-4o-mini|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
            log_success "OpenRouter configured"
            ;;
        5)
            log_prompt "Enter your Ollama base URL (default: http://localhost:11434):"
            read -r OLLAMA_URL
            OLLAMA_URL=${OLLAMA_URL:-http://localhost:11434}
            sed -i.bak "s|^OLLAMA_BASE_URL=.*|OLLAMA_BASE_URL=$OLLAMA_URL|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
            sed -i.bak "s|^OLLAMA_MODEL=.*|OLLAMA_MODEL=llama3.2|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
            sed -i.bak "s|^DEFAULT_MODEL=.*|DEFAULT_MODEL=llama3.2|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
            log_warning "Make sure Ollama is running locally!"
            log_info "For Ollama Cloud, set OLLAMA_CLOUD_KEY and OLLAMA_CLOUD_BASE_URL in .env"
            log_success "Ollama configured"
            ;;
        *)
            log_warning "Invalid choice. Please configure AI provider manually in .env"
            ;;
    esac
}

configure_optional() {
    echo ""
    echo -e "${BOLD}${CYAN}Optional Configuration${NC}"
    echo "─────────────────────────────────────────"
    
    log_prompt "Enable cost optimization? (Y/n):"
    read -r enable_cost
    if [[ ! $enable_cost =~ ^[Nn]$ ]]; then
        sed -i.bak "s|^ENABLE_COST_OPTIMIZATION=.*|ENABLE_COST_OPTIMIZATION=true|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
        log_info "Cost optimization enabled"
    fi
    
    log_prompt "Enable Sentry error tracking? (y/N):"
    read -r enable_sentry
    if [[ $enable_sentry =~ ^[Yy]$ ]]; then
        log_prompt "Enter Sentry DSN:"
        read -r SENTRY_DSN
        sed -i.bak "s|^SENTRY_DSN=.*|SENTRY_DSN=$SENTRY_DSN|" "$ENV_FILE" && rm -f "$ENV_FILE.bak"
        log_success "Sentry configured"
    fi
}

# =============================================================================
# DOCKER COMPOSE FILE CREATION
# =============================================================================

create_docker_compose() {
    log_step "Creating Docker Compose Configuration"
    
    if [ -f "$COMPOSE_FILE" ]; then
        log_info "docker-compose.single.yml already exists"
        return
    fi
    
    cat > "$COMPOSE_FILE" << 'EOF'
version: "3.8"

services:
  # PostgreSQL with pgvector extension
  postgres:
    image: ankane/pgvector:latest
    container_name: discord-bot-db
    restart: unless-stopped
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=${POSTGRES_PASSWORD:-changeme}
      - POSTGRES_DB=supportbot
      - PGDATA=/var/lib/postgresql/data/pgdata
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - bot-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres -d supportbot"]
      interval: 10s
      timeout: 5s
      retries: 5
      start_period: 10s
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 512M

  # Redis Cache & Message Broker
  redis:
    image: redis:7-alpine
    container_name: discord-bot-redis
    restart: unless-stopped
    command: redis-server --appendonly yes --maxmemory 256mb --maxmemory-policy allkeys-lru
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - bot-network
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 3s
      retries: 5
      start_period: 5s
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
        reservations:
          cpus: '0.25'
          memory: 128M

  # Discord Bot Application
  bot:
    build:
      context: .
      dockerfile: docker/Dockerfile
      target: production
    container_name: discord-bot-app
    restart: unless-stopped
    env_file:
      - .env
    environment:
      - DATABASE_URL=postgresql://postgres:${POSTGRES_PASSWORD:-changeme}@postgres:5432/supportbot
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    networks:
      - bot-network
    volumes:
      - ./logs:/app/logs
    deploy:
      resources:
        limits:
          cpus: '1.0'
          memory: 512M
        reservations:
          cpus: '0.5'
          memory: 256M

volumes:
  postgres_data:
    driver: local
  redis_data:
    driver: local

networks:
  bot-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
EOF

    log_success "Created docker-compose.single.yml"
}

# =============================================================================
# DIRECTORY CREATION
# =============================================================================

create_directories() {
    log_step "Creating Directories"
    
    local dirs=("logs" "data" "backups")
    
    for dir in "${dirs[@]}"; do
        local full_path="$PROJECT_DIR/$dir"
        if [ ! -d "$full_path" ]; then
            mkdir -p "$full_path"
            log_success "Created $dir/ directory"
        else
            log_info "$dir/ directory already exists"
        fi
    done
}

# =============================================================================
# DOCKER OPERATIONS
# =============================================================================

start_services() {
    log_step "Starting Services"
    
    cd "$PROJECT_DIR"
    
    log_info "Pulling latest images..."
    docker-compose -f "$COMPOSE_FILE" pull &
    spinner $!
    wait $!
    
    log_info "Building and starting services..."
    docker-compose -f "$COMPOSE_FILE" up -d --build &
    spinner $!
    wait $!
    
    log_success "Services started!"
    
    # Wait for services to be healthy
    log_info "Waiting for services to be healthy..."
    sleep 5
    
    local attempts=0
    local max_attempts=30
    
    while [ $attempts -lt $max_attempts ]; do
        if docker-compose -f "$COMPOSE_FILE" ps | grep -q "healthy"; then
            log_success "All services are healthy!"
            return 0
        fi
        attempts=$((attempts + 1))
        echo -n "."
        sleep 2
    done
    
    echo ""
    log_warning "Services may still be starting. Check status with: docker-compose -f docker-compose.single.yml ps"
}

# =============================================================================
# DATABASE MIGRATIONS
# =============================================================================

run_migrations() {
    log_step "Running Database Migrations"
    
    cd "$PROJECT_DIR"
    
    # Wait for PostgreSQL to be ready
    log_info "Waiting for PostgreSQL to be ready..."
    local attempts=0
    local max_attempts=30
    
    while [ $attempts -lt $max_attempts ]; do
        if docker-compose -f "$COMPOSE_FILE" exec -T postgres pg_isready -U postgres -d supportbot &> /dev/null; then
            log_success "PostgreSQL is ready!"
            break
        fi
        attempts=$((attempts + 1))
        echo -n "."
        sleep 2
    done
    
    if [ $attempts -eq $max_attempts ]; then
        log_error "PostgreSQL failed to start. Check logs: docker-compose -f docker-compose.single.yml logs postgres"
        exit 1
    fi
    
    # Run migrations
    log_info "Running Alembic migrations..."
    
    # Check if we can run migrations inside the container or locally
    if docker-compose -f "$COMPOSE_FILE" exec -T bot which alembic &> /dev/null; then
        docker-compose -f "$COMPOSE_FILE" exec -T bot alembic upgrade head
    elif command -v alembic &> /dev/null; then
        # Run locally with docker network
        export DATABASE_URL="postgresql://postgres:${POSTGRES_PASSWORD:-changeme}@localhost:5432/supportbot"
        alembic upgrade head
    else
        log_warning "Alembic not found. Attempting to run migrations via Python..."
        
        # Create a simple migration script
        cat > /tmp/run_migrations.py << 'MIGRATION_SCRIPT'
import asyncio
import sys
sys.path.insert(0, '.')

from sqlalchemy.ext.asyncio import create_async_engine
from database.connection import Base
from database.models import *

async def init_db():
    engine = create_async_engine('postgresql+asyncpg://postgres:${POSTGRES_PASSWORD:-changeme}@localhost:5432/supportbot')
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("Database initialized successfully!")

asyncio.run(init_db())
MIGRATION_SCRIPT
        
        python3 /tmp/run_migrations.py
    fi
    
    log_success "Database migrations completed!"
}

# =============================================================================
# HEALTH CHECKS
# =============================================================================

validate_setup() {
    log_step "Validating Setup"
    
    cd "$PROJECT_DIR"
    
    local all_healthy=true
    
    # Check Docker containers
    log_info "Checking Docker containers..."
    local services=("postgres" "redis" "bot")
    
    for service in "${services[@]}"; do
        local container_name="discord-bot-${service/app/}"
        [ "$service" = "bot" ] && container_name="discord-bot-app"
        
        if docker ps --format "{{.Names}}" | grep -q "^${container_name}$"; then
            local status=$(docker inspect --format='{{.State.Status}}' "$container_name" 2>/dev/null)
            local health=$(docker inspect --format='{{.State.Health.Status}}' "$container_name" 2>/dev/null || echo "N/A")
            
            if [ "$status" = "running" ]; then
                if [ "$health" = "healthy" ] || [ "$health" = "N/A" ]; then
                    log_success "$service is running and healthy"
                else
                    log_warning "$service is running but health check shows: $health"
                fi
            else
                log_error "$service is not running (status: $status)"
                all_healthy=false
            fi
        else
            log_error "$service container not found"
            all_healthy=false
        fi
    done
    
    # Test PostgreSQL connection
    log_info "Testing PostgreSQL connection..."
    if docker-compose -f "$COMPOSE_FILE" exec -T postgres psql -U postgres -d supportbot -c "SELECT 1;" &> /dev/null; then
        log_success "PostgreSQL connection successful"
    else
        log_error "PostgreSQL connection failed"
        all_healthy=false
    fi
    
    # Test Redis connection
    log_info "Testing Redis connection..."
    if docker-compose -f "$COMPOSE_FILE" exec -T redis redis-cli ping | grep -q "PONG"; then
        log_success "Redis connection successful"
    else
        log_error "Redis connection failed"
        all_healthy=false
    fi
    
    # Check if bot can connect to Discord (token validation)
    log_info "Validating Discord token..."
    local discord_token=$(grep "^DISCORD_TOKEN=" "$ENV_FILE" | cut -d= -f2)
    if [ -n "$discord_token" ] && [ "$discord_token" != "your_token_here" ]; then
        log_success "Discord token is configured"
    else
        log_error "Discord token is not configured properly"
        all_healthy=false
    fi
    
    if [ "$all_healthy" = true ]; then
        echo ""
        log_success "=========================================="
        log_success "  SETUP VALIDATION PASSED!"
        log_success "=========================================="
        return 0
    else
        echo ""
        log_warning "=========================================="
        log_warning "  SETUP VALIDATION FAILED"
        log_warning "=========================================="
        log_info "Check the logs for details:"
        log_info "  docker-compose -f docker-compose.single.yml logs"
        return 1
    fi
}

# =============================================================================
# NEXT STEPS
# =============================================================================

print_next_steps() {
    echo ""
    echo -e "${GREEN}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║          SETUP COMPLETE! 🎉                                ║${NC}"
    echo -e "${GREEN}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${BOLD}Next Steps:${NC}"
    echo ""
    echo "  1. ${CYAN}Invite your bot to Discord:${NC}"
    echo "     - Go to: https://discord.com/developers/applications"
    echo "     - Select your application"
    echo "     - Go to OAuth2 > URL Generator"
    echo "     - Select 'bot' scope and necessary permissions"
    echo "     - Copy and visit the generated URL"
    echo ""
    echo "  2. ${CYAN}View logs:${NC}"
    echo "     docker-compose -f docker-compose.single.yml logs -f"
    echo ""
    echo "  3. ${CYAN}Stop the bot:${NC}"
    echo "     docker-compose -f docker-compose.single.yml down"
    echo ""
    echo "  4. ${CYAN}Restart the bot:${NC}"
    echo "     docker-compose -f docker-compose.single.yml restart"
    echo ""
    echo "  5. ${CYAN}Access PostgreSQL:${NC}"
    echo "     docker-compose -f docker-compose.single.yml exec postgres psql -U postgres -d supportbot"
    echo ""
    echo "  6. ${CYAN}Access Redis:${NC}"
    echo "     docker-compose -f docker-compose.single.yml exec redis redis-cli"
    echo ""
    echo -e "${YELLOW}Configuration file:${NC} $ENV_FILE"
    echo -e "${YELLOW}Documentation:${NC} https://github.com/yourusername/discord-support-bot"
    echo ""
    echo -e "${GREEN}Your Discord Support Bot is ready to go!${NC}"
    echo ""
}

# =============================================================================
# MAIN
# =============================================================================

main() {
    echo ""
    echo -e "${CYAN}${BOLD}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}${BOLD}║     Discord Support Bot - One-Command Setup               ║${NC}"
    echo -e "${CYAN}${BOLD}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    
    # Trap errors
    trap 'log_error "Setup failed! Check the error messages above."' ERR
    
    # Run setup steps
    check_prerequisites
    create_docker_compose
    setup_environment
    create_directories
    start_services
    run_migrations
    validate_setup
    
    # Print success message
    print_next_steps
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        echo "Discord Support Bot Setup Script"
        echo ""
        echo "Usage: ./scripts/setup.sh [OPTIONS]"
        echo ""
        echo "Options:"
        echo "  --help, -h      Show this help message"
        echo "  --skip-config   Skip interactive configuration (use existing .env)"
        echo "  --reset         Reset all data and start fresh"
        echo ""
        echo "Examples:"
        echo "  ./scripts/setup.sh              # Full interactive setup"
        echo "  ./scripts/setup.sh --skip-config # Use existing configuration"
        echo ""
        exit 0
        ;;
    --skip-config)
        check_prerequisites
        create_docker_compose
        create_directories
        start_services
        run_migrations
        validate_setup
        print_next_steps
        ;;
    --reset)
        log_warning "This will DELETE all data and reset everything!"
        read -p "Are you sure? (yes/no): " confirm
        if [ "$confirm" = "yes" ]; then
            cd "$PROJECT_DIR"
            docker-compose -f "$COMPOSE_FILE" down -v
            rm -rf logs data
            log_success "Reset complete. Run setup again to start fresh."
        else
            log_info "Reset cancelled."
        fi
        ;;
    *)
        main
        ;;
esac
