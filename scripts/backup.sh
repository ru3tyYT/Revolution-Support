#!/bin/bash

set -euo pipefail

# Discord Support Bot Database Backup Script
# Supports: local backups, S3, GCS, Azure Blob Storage

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKUP_DIR="${BACKUP_DIR:-$PROJECT_ROOT/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-30}"
NAMESPACE="${NAMESPACE:-supportbot}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

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

# Create backup directory
create_backup_dir() {
    local backup_type="$1"
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_path="$BACKUP_DIR/$backup_type/$timestamp"
    
    mkdir -p "$backup_path"
    echo "$backup_path"
}

# Get database credentials from Kubernetes secrets
get_db_credentials() {
    log "Retrieving database credentials..."
    
    DB_HOST="${DB_HOST:-postgres-service.$NAMESPACE.svc.cluster.local}"
    DB_PORT="${DB_PORT:-5432}"
    DB_NAME="${DB_NAME:-supportbot}"
    DB_USER="${DB_USER:-postgres}"
    
    if [[ -z "${DB_PASSWORD:-}" ]]; then
        if kubectl get secret discord-bot-secrets -n "$NAMESPACE" >/dev/null 2>&1; then
            DB_PASSWORD=$(kubectl get secret discord-bot-secrets -n "$NAMESPACE" -o jsonpath='{.data.postgres-password}' | base64 -d)
        else
            error "Database password not found. Set DB_PASSWORD or ensure Kubernetes secret exists"
        fi
    fi
    
    export PGPASSWORD="$DB_PASSWORD"
}

# Create PostgreSQL backup
backup_postgres() {
    log "Creating PostgreSQL backup..."
    
    local backup_path
    backup_path=$(create_backup_dir "postgres")
    local backup_file="$backup_path/supportbot_$(date +%Y%m%d_%H%M%S).sql.gz"
    
    # Create backup using pg_dump
    kubectl run pg-backup-job \
        --rm -i \
        --restart=Never \
        --image=postgres:15-alpine \
        --namespace="$NAMESPACE" \
        --env="PGPASSWORD=$DB_PASSWORD" \
        --command -- \
        pg_dump \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --verbose \
            --format=custom \
            --file=/tmp/backup.dump 2>&1 | tee "$backup_path/backup.log"
    
    # Copy backup from pod
    kubectl cp "$NAMESPACE/pg-backup-job:/tmp/backup.dump" "$backup_file" 2>/dev/null || {
        # Alternative: direct pg_dump
        pg_dump \
            -h "$DB_HOST" \
            -p "$DB_PORT" \
            -U "$DB_USER" \
            -d "$DB_NAME" \
            --verbose \
            --format=custom | gzip > "$backup_file"
    }
    
    # Create metadata file
    cat > "$backup_path/metadata.json" <<EOF
{
    "timestamp": "$(date -Iseconds)",
    "database": "$DB_NAME",
    "host": "$DB_HOST",
    "version": "$(psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -t -c "SELECT version();" 2>/dev/null || echo 'unknown')",
    "size": "$(du -h "$backup_file" | cut -f1)",
    "type": "full"
}
EOF
    
    success "Backup created: $backup_file"
    echo "$backup_file"
}

# Backup Redis data
backup_redis() {
    log "Creating Redis backup..."
    
    local backup_path
    backup_path=$(create_backup_dir "redis")
    local backup_file="$backup_path/redis_$(date +%Y%m%d_%H%M%S).rdb"
    
    # Trigger BGSAVE and copy RDB file
    kubectl exec -n "$NAMESPACE" deployment/redis -- redis-cli BGSAVE
    sleep 5
    
    kubectl cp "$NAMESPACE/redis-0:/data/dump.rdb" "$backup_file" 2>/dev/null || {
        warn "Could not copy Redis RDB file directly"
        # Alternative: use redis-cli --rdb
        kubectl exec -n "$NAMESPACE" deployment/redis -- redis-cli --rdb /tmp/dump.rdb
        kubectl cp "$NAMESPACE/deployment/redis:/tmp/dump.rdb" "$backup_file"
    }
    
    success "Redis backup created: $backup_file"
}

# Upload to S3
upload_to_s3() {
    local file="$1"
    local bucket="${S3_BUCKET:-discord-bot-backups}"
    local region="${AWS_REGION:-us-east-1}"
    
    log "Uploading to S3: s3://$bucket/"
    
    if command -v aws >/dev/null 2>&1; then
        aws s3 cp "$file" "s3://$bucket/$(basename "$file")" --storage-class STANDARD_IA
        success "Uploaded to S3: s3://$bucket/$(basename "$file")"
    else
        warn "AWS CLI not installed. Skipping S3 upload"
    fi
}

# Upload to GCS
upload_to_gcs() {
    local file="$1"
    local bucket="${GCS_BUCKET:-discord-bot-backups}"
    
    log "Uploading to GCS: gs://$bucket/"
    
    if command -v gsutil >/dev/null 2>&1; then
        gsutil cp "$file" "gs://$bucket/"
        success "Uploaded to GCS: gs://$bucket/$(basename "$file")"
    else
        warn "gsutil not installed. Skipping GCS upload"
    fi
}

# Upload to Azure Blob Storage
upload_to_azure() {
    local file="$1"
    local container="${AZURE_CONTAINER:-backups}"
    local account="${AZURE_STORAGE_ACCOUNT}"
    
    log "Uploading to Azure Blob Storage..."
    
    if command -v az >/dev/null 2>&1; then
        az storage blob upload \
            --account-name "$account" \
            --container-name "$container" \
            --file "$file" \
            --name "$(basename "$file")" \
            --tier Cool
        success "Uploaded to Azure: $container/$(basename "$file")"
    else
        warn "Azure CLI not installed. Skipping Azure upload"
    fi
}

# Clean up old backups
cleanup_old_backups() {
    log "Cleaning up backups older than $RETENTION_DAYS days..."
    
    find "$BACKUP_DIR" -type f -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -type d -empty -delete
    
    success "Cleanup completed"
}

# List available backups
list_backups() {
    log "Available backups:"
    
    if [[ -d "$BACKUP_DIR" ]]; then
        find "$BACKUP_DIR" -type f -name "*.sql*" -o -name "*.rdb" | sort -r | head -20
    else
        warn "No backup directory found"
    fi
}

# Restore from backup
restore_backup() {
    local backup_file="$1"
    
    if [[ ! -f "$backup_file" ]]; then
        error "Backup file not found: $backup_file"
    fi
    
    log "Restoring from backup: $backup_file"
    warn "This will overwrite the current database!"
    read -p "Are you sure? (yes/no): " confirm
    
    if [[ "$confirm" != "yes" ]]; then
        log "Restore cancelled"
        exit 0
    fi
    
    get_db_credentials
    
    if [[ "$backup_file" == *.gz ]]; then
        gunzip -c "$backup_file" | kubectl run pg-restore-job \
            --rm -i \
            --restart=Never \
            --image=postgres:15-alpine \
            --namespace="$NAMESPACE" \
            --env="PGPASSWORD=$DB_PASSWORD" \
            --command -- \
            psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME"
    else
        kubectl run pg-restore-job \
            --rm -i \
            --restart=Never \
            --image=postgres:15-alpine \
            --namespace="$NAMESPACE" \
            --env="PGPASSWORD=$DB_PASSWORD" \
            --command -- \
            pg_restore \
                -h "$DB_HOST" \
                -p "$DB_PORT" \
                -U "$DB_USER" \
                -d "$DB_NAME" \
                --verbose \
                --no-owner \
                --no-privileges \
                "$backup_file"
    fi
    
    success "Restore completed"
}

# Create volume snapshots (if supported by storage provider)
create_volume_snapshots() {
    log "Creating volume snapshots..."
    
    # Check if VolumeSnapshot CRD exists
    if kubectl get volumesnapshot -n "$NAMESPACE" >/dev/null 2>&1; then
        local timestamp
        timestamp=$(date +%Y%m%d-%H%M%S)
        
        # Snapshot PostgreSQL PVC
        cat <<EOF | kubectl apply -f -
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: postgres-snapshot-$timestamp
  namespace: $NAMESPACE
spec:
  volumeSnapshotClassName: csi-snapclass
  source:
    persistentVolumeClaimName: postgres-storage-postgres-0
EOF
        
        # Snapshot Redis PVC
        cat <<EOF | kubectl apply -f -
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: redis-snapshot-$timestamp
  namespace: $NAMESPACE
spec:
  volumeSnapshotClassName: csi-snapclass
  source:
    persistentVolumeClaimName: redis-pvc
EOF
        
        success "Volume snapshots created"
    else
        warn "Volume snapshots not supported by cluster"
    fi
}

# Main backup function
backup() {
    log "Starting backup process..."
    
    get_db_credentials
    
    local postgres_backup
    postgres_backup=$(backup_postgres)
    backup_redis
    
    # Upload to cloud storage if configured
    if [[ -n "${S3_BUCKET:-}" ]]; then
        upload_to_s3 "$postgres_backup"
    fi
    
    if [[ -n "${GCS_BUCKET:-}" ]]; then
        upload_to_gcs "$postgres_backup"
    fi
    
    if [[ -n "${AZURE_STORAGE_ACCOUNT:-}" ]]; then
        upload_to_azure "$postgres_backup"
    fi
    
    # Create volume snapshots as additional backup
    create_volume_snapshots
    
    cleanup_old_backups
    
    success "Backup process completed successfully"
}

# Main entry point
main() {
    local action="${1:-backup}"
    
    case "$action" in
        backup)
            backup
            ;;
        restore)
            if [[ -z "${2:-}" ]]; then
                echo "Usage: $0 restore <backup-file>"
                list_backups
                exit 1
            fi
            restore_backup "$2"
            ;;
        list)
            list_backups
            ;;
        snapshot)
            create_volume_snapshots
            ;;
        cleanup)
            cleanup_old_backups
            ;;
        *)
            echo "Discord Support Bot Backup Script"
            echo ""
            echo "Usage: $0 [action] [options]"
            echo ""
            echo "Actions:"
            echo "  backup              Create full backup (default)"
            echo "  restore <file>      Restore database from backup"
            echo "  list                List available backups"
            echo "  snapshot            Create volume snapshots"
            echo "  cleanup             Remove old backups"
            echo ""
            echo "Environment Variables:"
            echo "  BACKUP_DIR          Local backup directory (default: ./backups)"
            echo "  RETENTION_DAYS      Days to keep backups (default: 30)"
            echo "  DB_HOST             Database host"
            echo "  DB_PASSWORD         Database password"
            echo "  S3_BUCKET           S3 bucket for cloud backups"
            echo "  GCS_BUCKET          GCS bucket for cloud backups"
            echo "  AZURE_STORAGE_ACCOUNT  Azure storage account"
            echo "  AZURE_CONTAINER     Azure container name"
            echo ""
            echo "Examples:"
            echo "  $0 backup"
            echo "  $0 restore ./backups/postgres/20240101_120000/supportbot_20240101_120000.sql.gz"
            echo "  BACKUP_DIR=/mnt/backups $0 backup"
            exit 1
            ;;
    esac
}

main "$@"
