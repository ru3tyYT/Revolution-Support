#!/bin/bash

set -euo pipefail

# Discord Support Bot Deployment Script
# Usage: ./deploy.sh [environment] [action]

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
ENVIRONMENT="${1:-staging}"
ACTION="${2:-deploy}"
NAMESPACE="supportbot"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    echo -e "${BLUE}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

warn() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Validate environment
validate_environment() {
    if [[ ! "$ENVIRONMENT" =~ ^(staging|production)$ ]]; then
        error "Invalid environment: $ENVIRONMENT. Must be 'staging' or 'production'"
    fi
}

# Check prerequisites
check_prerequisites() {
    log "Checking prerequisites..."
    
    command -v kubectl >/dev/null 2>&1 || error "kubectl is required but not installed"
    command -v docker >/dev/null 2>&1 || error "docker is required but not installed"
    
    if [[ "$ENVIRONMENT" == "production" ]]; then
        command -v helm >/dev/null 2>&1 || warn "helm is not installed (optional for production)"
    fi
    
    # Check kubectl connectivity
    kubectl cluster-info >/dev/null 2>&1 || error "Cannot connect to Kubernetes cluster"
    
    success "Prerequisites check passed"
}

# Build and push Docker image
build_image() {
    log "Building Docker image..."
    
    local image_tag="discord-support-bot:${ENVIRONMENT}-$(git rev-parse --short HEAD 2>/dev/null || echo 'latest')"
    local image_name="${DOCKER_REGISTRY:-localhost}/${image_tag}"
    
    docker build -t "$image_name" -f "$PROJECT_ROOT/docker/Dockerfile" "$PROJECT_ROOT"
    
    if [[ -n "${DOCKER_REGISTRY:-}" ]]; then
        log "Pushing image to registry..."
        docker push "$image_name"
    fi
    
    success "Image built: $image_name"
    echo "$image_name" > /tmp/discord-bot-image-tag
}

# Create namespace if it doesn't exist
create_namespace() {
    log "Setting up namespace: $NAMESPACE"
    
    kubectl get namespace "$NAMESPACE" >/dev/null 2>&1 || {
        kubectl create namespace "$NAMESPACE"
        success "Created namespace: $NAMESPACE"
    }
    
    # Apply resource quotas and limits
    cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ResourceQuota
metadata:
  name: compute-quota
  namespace: $NAMESPACE
spec:
  hard:
    requests.cpu: "10"
    requests.memory: 20Gi
    limits.cpu: "20"
    limits.memory: 40Gi
    pods: "50"
EOF
}

# Deploy secrets
deploy_secrets() {
    log "Checking secrets..."
    
    if ! kubectl get secret discord-bot-secrets -n "$NAMESPACE" >/dev/null 2>&1; then
        warn "Secrets not found. Please create them using:"
        warn "kubectl create secret generic discord-bot-secrets \\"
        warn "  --from-literal=discord-token='YOUR_TOKEN' \\"
        warn "  --from-literal=postgres-password='YOUR_PASSWORD' \\"
        warn "  --from-literal=database-url='YOUR_DB_URL' \\"
        warn "  --from-literal=openai-api-key='YOUR_OPENAI_KEY' \\"
        warn "  --from-literal=serpapi-key='YOUR_SERPAPI_KEY' \\"
        warn "  --namespace=$NAMESPACE"
        error "Please create the secrets first"
    fi
    
    success "Secrets verified"
}

# Deploy configuration
deploy_config() {
    log "Applying ConfigMaps..."
    kubectl apply -f "$PROJECT_ROOT/docker/k8s/configmap.yaml"
    success "ConfigMaps applied"
}

# Deploy database
deploy_database() {
    log "Deploying PostgreSQL..."
    kubectl apply -f "$PROJECT_ROOT/docker/k8s/postgres-statefulset.yaml"
    
    log "Waiting for PostgreSQL to be ready..."
    kubectl rollout status statefulset/postgres -n "$NAMESPACE" --timeout=300s
    success "PostgreSQL deployed"
    
    log "Deploying Redis..."
    kubectl apply -f "$PROJECT_ROOT/docker/k8s/redis-deployment.yaml"
    kubectl rollout status deployment/redis -n "$NAMESPACE" --timeout=120s
    success "Redis deployed"
}

# Deploy bot and workers
deploy_application() {
    log "Deploying Discord Bot..."
    
    # Update image tag if built
    if [[ -f /tmp/discord-bot-image-tag ]]; then
        local image_tag
        image_tag=$(cat /tmp/discord-bot-image-tag)
        sed -i.bak "s|image: discord-support-bot:latest|image: $image_tag|" "$PROJECT_ROOT/docker/k8s/bot-deployment.yaml"
        rm "$PROJECT_ROOT/docker/k8s/bot-deployment.yaml.bak"
    fi
    
    kubectl apply -f "$PROJECT_ROOT/docker/k8s/bot-deployment.yaml"
    kubectl rollout status deployment/discord-bot -n "$NAMESPACE" --timeout=300s
    success "Discord Bot deployed"
    
    log "Deploying Research Workers..."
    kubectl apply -f "$PROJECT_ROOT/docker/k8s/research-worker-deployment.yaml"
    kubectl rollout status deployment/research-worker -n "$NAMESPACE" --timeout=300s
    success "Research Workers deployed"
}

# Deploy monitoring
deploy_monitoring() {
    log "Deploying monitoring stack..."
    
    # Check if Prometheus/Grafana is already deployed
    if ! kubectl get deployment prometheus -n monitoring >/dev/null 2>&1; then
        warn "Prometheus/Grafana not found in monitoring namespace"
        warn "Please deploy monitoring stack separately or use Helm:"
        warn "helm repo add prometheus-community https://prometheus-community.github.io/helm-charts"
        warn "helm install prometheus prometheus-community/kube-prometheus-stack -n monitoring --create-namespace"
    else
        success "Monitoring stack detected"
    fi
    
    # Deploy ServiceMonitors for the bot
    cat <<EOF | kubectl apply -f -
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: discord-bot-metrics
  namespace: monitoring
  labels:
    release: prometheus
spec:
  selector:
    matchLabels:
      app: discord-bot
  namespaceSelector:
    matchNames:
    - $NAMESPACE
  endpoints:
  - port: metrics
    interval: 15s
    path: /metrics
EOF
    success "ServiceMonitor deployed"
}

# Run database migrations
run_migrations() {
    log "Running database migrations..."
    
    kubectl run migration-job \
        --rm -i \
        --restart=Never \
        --image=discord-support-bot:latest \
        --namespace="$NAMESPACE" \
        --env="DATABASE_URL=$(kubectl get secret discord-bot-secrets -n $NAMESPACE -o jsonpath='{.data.database-url}' | base64 -d)" \
        --command -- \
        alembic upgrade head
    
    success "Migrations completed"
}

# Verify deployment
verify_deployment() {
    log "Verifying deployment..."
    
    echo ""
    echo "=== Pod Status ==="
    kubectl get pods -n "$NAMESPACE"
    
    echo ""
    echo "=== Service Status ==="
    kubectl get svc -n "$NAMESPACE"
    
    echo ""
    echo "=== HPA Status ==="
    kubectl get hpa -n "$NAMESPACE"
    
    success "Deployment verification complete"
}

# Rollback deployment
rollback() {
    log "Rolling back deployment..."
    
    kubectl rollout undo deployment/discord-bot -n "$NAMESPACE"
    kubectl rollout undo deployment/research-worker -n "$NAMESPACE"
    
    success "Rollback completed"
}

# Scale deployment
scale() {
    local replicas="${3:-2}"
    log "Scaling to $replicas replicas..."
    
    kubectl scale deployment/discord-bot --replicas="$replicas" -n "$NAMESPACE"
    kubectl scale deployment/research-worker --replicas="$replicas" -n "$NAMESPACE"
    
    success "Scaled to $replicas replicas"
}

# Cleanup
cleanup() {
    log "Cleaning up temporary files..."
    rm -f /tmp/discord-bot-image-tag
}

# Main deployment function
deploy() {
    validate_environment
    check_prerequisites
    create_namespace
    deploy_secrets
    deploy_config
    
    if [[ "${BUILD_IMAGE:-true}" == "true" ]]; then
        build_image
    fi
    
    deploy_database
    run_migrations
    deploy_application
    
    if [[ "${DEPLOY_MONITORING:-true}" == "true" ]]; then
        deploy_monitoring
    fi
    
    verify_deployment
}

# Main entry point
main() {
    trap cleanup EXIT
    
    case "$ACTION" in
        deploy)
            deploy
            ;;
        rollback)
            rollback
            ;;
        scale)
            scale "$@"
            ;;
        verify)
            verify_deployment
            ;;
        build)
            build_image
            ;;
        migrate)
            run_migrations
            ;;
        *)
            echo "Usage: $0 [environment] [action]"
            echo ""
            echo "Environments:"
            echo "  staging     Deploy to staging environment"
            echo "  production  Deploy to production environment"
            echo ""
            echo "Actions:"
            echo "  deploy      Full deployment (default)"
            echo "  rollback    Rollback to previous version"
            echo "  scale       Scale deployments (requires replicas argument)"
            echo "  verify      Verify deployment status"
            echo "  build       Build Docker image only"
            echo "  migrate     Run database migrations only"
            echo ""
            echo "Examples:"
            echo "  $0 staging deploy"
            echo "  $0 production deploy"
            echo "  $0 staging scale 5"
            exit 1
            ;;
    esac
}

main "$@"
