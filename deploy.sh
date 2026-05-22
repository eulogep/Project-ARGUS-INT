#!/bin/bash
# deploy.sh
# ============================================================================
# ARGUS-INT Production Server Hardening Script
# For Ubuntu 22.04 LTS / Debian 12
# ============================================================================

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# Check if running as root
if [[ $EUID -ne 0 ]]; then
   log_error "This script must be run as root"
   exit 1
fi

log_info "Starting ARGUS-INT server hardening..."

# ============================================================================
# 1. System Updates & Essential Packages
# ============================================================================
log_info "Updating system packages..."
apt-get update && apt-get upgrade -y
apt-get install -y \
    ufw \
    fail2ban \
    unattended-upgrades \
    apt-listchanges \
    curl \
    wget \
    gnupg \
    lsb-release \
    ca-certificates \
    software-properties-common

# ============================================================================
# 2. Firewall Configuration (UFW)
# ============================================================================
log_info "Configuring firewall..."
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 3000/tcp  # Frontend
ufw allow 8000/tcp  # Backend API
ufw --force enable
log_info "Firewall enabled with rules: SSH, 3000, 8000"

# ============================================================================
# 3. Fail2Ban Configuration
# ============================================================================
log_info "Configuring fail2ban..."
cat > /etc/fail2ban/jail.local <<EOF
[DEFAULT]
bantime = 3600
findtime = 600
maxretry = 5
backend = systemd

[sshd]
enabled = true
port = ssh
filter = sshd
logpath = /var/log/auth.log
maxretry = 3
EOF

systemctl restart fail2ban
systemctl enable fail2ban
log_info "Fail2ban configured and enabled"

# ============================================================================
# 4. Automatic Security Updates
# ============================================================================
log_info "Configuring automatic security updates..."
cat > /etc/apt/apt.conf.d/20auto-upgrades <<EOF
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

systemctl restart unattended-upgrades
log_info "Automatic security updates enabled"

# ============================================================================
# 5. Docker Installation (if not present)
# ============================================================================
if ! command -v docker &> /dev/null; then
    log_info "Installing Docker..."
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    log_info "Docker installed and enabled"
else
    log_info "Docker already installed"
fi

# ============================================================================
# 6. Create Encrypted Data Partition
# ============================================================================
log_info "Creating encrypted data directories..."
mkdir -p /opt/argus-data/{postgres,neo4j}
chmod 700 /opt/argus-data
chmod 700 /opt/argus-data/postgres
chmod 700 /opt/argus-data/neo4j

# Note: For production, use LUKS encryption on a dedicated partition
log_warn "For maximum security, mount /opt/argus-data from a LUKS-encrypted partition"

# ============================================================================
# 7. Secrets Management Setup
# ============================================================================
log_info "Setting up secrets management..."
if ! command -v sops &> /dev/null; then
    log_info "Installing sops..."
    curl -LO https://github.com/getsops/sops/releases/download/v3.8.1/sops-v3.8.1.linux.amd64
    mv sops-v3.8.1.linux.amd64 /usr/local/bin/sops
    chmod +x /usr/local/bin/sops
fi

if ! command -v age &> /dev/null; then
    log_info "Installing age..."
    apt-get install -y age
fi

log_info "Secrets management tools installed"

# ============================================================================
# 8. Application Deployment
# ============================================================================
log_info "Deploying ARGUS-INT..."
cd "$(dirname "$0")"

# Decrypt secrets if encrypted
if [ -f .env.prod.enc ]; then
    log_info "Decrypting production secrets..."
    sops --decrypt .env.prod.enc > .env.prod
    chmod 600 .env.prod
fi

# Build and start services
log_info "Building Docker images..."
docker compose -f docker-compose.prod.yml build --no-cache

log_info "Starting services..."
docker compose -f docker-compose.prod.yml up -d

# Wait for health checks
log_info "Waiting for services to become healthy..."
sleep 30

# Verify deployment
log_info "Verifying deployment..."
if curl -f http://localhost:8000/health > /dev/null 2>&1; then
    log_info "✅ Backend health check passed"
else
    log_error "❌ Backend health check failed"
    docker compose -f docker-compose.prod.yml logs backend
    exit 1
fi

if curl -f http://localhost:3000 > /dev/null 2>&1; then
    log_info "✅ Frontend health check passed"
else
    log_error "❌ Frontend health check failed"
    docker compose -f docker-compose.prod.yml logs frontend
    exit 1
fi

# ============================================================================
# 9. Backup Strategy Setup
# ============================================================================
log_info "Setting up backup cron job..."
cat > /etc/cron.daily/argus-backup <<'EOF'
#!/bin/bash
BACKUP_DIR="/opt/argus-backups/$(date +%Y%m%d)"
mkdir -p "$BACKUP_DIR"

# PostgreSQL backup
docker exec argus-postgres pg_dump -U ${POSTGRES_USER} ${POSTGRES_DB} | gzip > "$BACKUP_DIR/postgres.sql.gz"

# Neo4j backup
docker exec argus-neo4j neo4j-admin dump --database=neo4j --to=/backups/neo4j.dump
cp /opt/argus-data/neo4j/backups/neo4j.dump "$BACKUP_DIR/"

# Encrypt backups
find "$BACKUP_DIR" -type f -exec gpg --recipient your-backup-key --encrypt {} \;

# Retention: keep 30 days
find /opt/argus-backups -type d -mtime +30 -exec rm -rf {} \;
EOF

chmod +x /etc/cron.daily/argus-backup
log_info "Daily backup cron job configured"

# ============================================================================
# 10. Final Security Checks
# ============================================================================
log_info "Running final security checks..."

# Check for listening ports
log_info "Listening ports:"
ss -tlnp | grep -E ':(3000|8000|5432|7474|7687|6379)' || true

# Check running containers
log_info "Running containers:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

log_info "=========================================="
log_info "✅ ARGUS-INT deployment complete!"
log_info "=========================================="
log_info "Frontend: http://$(hostname -I | awk '{print $1}'):3000"
log_info "Backend API: http://$(hostname -I | awk '{print $1}'):8000"
log_info "API Docs: http://$(hostname -I | awk '{print $1}'):8000/api/docs"
log_warn "⚠️  Remember to:"
log_warn "   1. Change all default passwords in .env.prod"
log_warn "   2. Set up TLS/SSL certificates (Let's Encrypt)"
log_warn "   3. Configure log rotation and monitoring"
log_warn "   4. Set up alerting for failed health checks"
log_warn "   5. Review and harden SSH configuration"
