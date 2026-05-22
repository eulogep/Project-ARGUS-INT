#!/usr/bin/env bash
# ==============================================================================
# Project ARGUS-INT - Secure Production Deployment Script
# ==============================================================================
set -euo pipefail

# Log formatting
info() { echo -e "\e[32m[INFO]\e[0m $*"; }
warn() { echo -e "\e[33m[WARN]\e[0m $*"; }
error() { echo -e "\e[31m[ERROR]\e[0m $*" >&2; exit 1; }

# Target check
info "Starting VPS Hardening and Deployment..."

# 1. Firewall (UFW) Configuration
if command -v ufw >/dev/null 2>&1; then
    info "Configuring UFW Firewall Rules..."
    ufw default deny incoming
    ufw default allow outgoing
    ufw allow 22/tcp comment 'SSH'
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'
    ufw allow 3000/tcp comment 'ARGUS C2 Frontend'
    ufw allow 8000/tcp comment 'ARGUS Backend Gateway'
    ufw --force enable
    info "UFW Firewall Rules active."
else
    warn "UFW is not installed. Skipping firewall rules."
fi

# 2. Fail2ban Protection
if command -v fail2ban-client >/dev/null 2>&1; then
    info "Configuring Fail2ban..."
    cat <<EOF > /etc/fail2ban/jail.d/argus.local
[nginx-http-auth]
enabled = true
port    = http,https
logpath = %(nginx_error_log)s

[sshd]
enabled = true
port    = ssh
maxretry = 3
findtime = 600
bantime = 3600
EOF
    systemctl restart fail2ban || true
    info "Fail2ban updated and restarted."
else
    warn "Fail2ban is not installed. Skipping intrusion protection."
fi

# 3. Decrypt Secrets via SOPS
if [ -f ".env.enc" ]; then
    info "Decrypting production secrets using SOPS..."
    if command -v sops >/dev/null 2>&1; then
        sops --decrypt .env.enc > .env
        info ".env decrypted successfully."
    else
        error "SOPS binary not found. Unable to decrypt production secrets."
    fi
else
    warn "No .env.enc file found. Using existing .env or host variables."
fi

# 4. Launch Stack
info "Launching Stack with Docker Compose..."
docker compose -f docker-compose.prod.yml down --remove-orphans
docker compose -f docker-compose.prod.yml up -d --build

info "ARGUS-INT Deployment completed successfully."
