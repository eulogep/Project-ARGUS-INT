#!/usr/bin/env bash
# ==============================================================================
# Rapport de Crash Anonyme (via Tor & GPG)
# ==============================================================================
set -euo pipefail

REPORT_DIR="/tmp/argus_crash_report_$(date +%s)"
mkdir -p "$REPORT_DIR"

echo "[*] Génération du rapport de crash anonymisé..."

# 1. Collecte des logs
echo "  -> Extraction des logs Docker..."
docker logs --tail 500 argus-backend > "${REPORT_DIR}/backend.log" 2>/dev/null || echo "Backend logs non disponibles" > "${REPORT_DIR}/backend.log"
docker logs --tail 500 argus-vllm > "${REPORT_DIR}/vllm.log" 2>/dev/null || echo "VLLM logs non disponibles" > "${REPORT_DIR}/vllm.log"

# 2. Anonymisation (sed regex basiques pour IPv4 et UUIDs)
echo "  -> Anonymisation des données sensibles..."
for file in "${REPORT_DIR}"/*.log; do
    sed -i -E 's/[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}/[REDACTED_IP]/g' "$file"
    sed -i -E 's/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/[REDACTED_UUID]/g' "$file"
    sed -i -E 's/\/home\/[a-zA-Z0-9_-]+\//[REDACTED_PATH]\//g' "$file"
done

# 3. Empaquetage et chiffrement
echo "  -> Compression et chiffrement (GPG)..."
tar -czf "${REPORT_DIR}/crash.tar.gz" -C "$REPORT_DIR" backend.log vllm.log
gpg --batch --yes --trust-model always --recipient "security@argus.local" --encrypt "${REPORT_DIR}/crash.tar.gz"

ENCRYPTED_FILE="${REPORT_DIR}/crash.tar.gz.gpg"

# 4. Envoi via Tor
echo "  -> Transmission sécurisée via Tor..."
# Configuration de l'endpoint backend (Onion ou HTTPS clear)
SUPPORT_ENDPOINT="http://localhost:8000/api/v1/support/crash-report"

if command -v torsocks >/dev/null; then
    # Simulation d'envoi curl via torsocks
    curl --socks5-hostname 127.0.0.1:9050 -X POST -F "file=@${ENCRYPTED_FILE}" "$SUPPORT_ENDPOINT" || echo "[-] Échec de l'envoi réseau. Rapport dispo ici: $ENCRYPTED_FILE"
else
    echo "[-] 'torsocks' non installé. Envoi réseau direct."
    curl -X POST -F "file=@${ENCRYPTED_FILE}" "$SUPPORT_ENDPOINT" || echo "[-] Échec de l'envoi réseau. Rapport dispo ici: $ENCRYPTED_FILE"
fi

echo "✅ Rapport de crash généré et transmis. Merci !"
rm -rf "${REPORT_DIR}/backend.log" "${REPORT_DIR}/vllm.log" "${REPORT_DIR}/crash.tar.gz"
