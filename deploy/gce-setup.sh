#!/usr/bin/env bash
# ── evmbench GCE deployment script ──
# Provisions a GCE VM, installs Docker + Caddy, deploys the backend stack.
#
# Usage:
#   ./deploy/gce-setup.sh --domain YOURDOMAIN.com [--zone us-central1-a] [--machine e2-standard-2] [--name evmbench]
#
# Prerequisites:
#   - gcloud CLI authenticated with a project set
#   - A domain with DNS you can point to the VM IP
#   - backend/.env filled in from .env.production template
set -euo pipefail

# ── Defaults ──
ZONE="us-central1-a"
MACHINE="e2-standard-2"
NAME="evmbench"
DOMAIN=""
REPO_URL=""
DISK_SIZE="40GB"

# ── Parse args ──
while [[ $# -gt 0 ]]; do
  case $1 in
    --domain)  DOMAIN="$2";  shift 2 ;;
    --zone)    ZONE="$2";    shift 2 ;;
    --machine) MACHINE="$2"; shift 2 ;;
    --name)    NAME="$2";    shift 2 ;;
    --repo)    REPO_URL="$2"; shift 2 ;;
    *) echo "Unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$DOMAIN" ]]; then
  echo "Error: --domain is required (e.g. --domain example.com)"
  exit 1
fi

echo "=== Provisioning GCE instance ==="
echo "  Name:    $NAME"
echo "  Zone:    $ZONE"
echo "  Machine: $MACHINE"
echo "  Domain:  $DOMAIN"
echo ""

# ── 1. Create VM ──
gcloud compute instances create "$NAME" \
  --zone="$ZONE" \
  --machine-type="$MACHINE" \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size="$DISK_SIZE" \
  --tags=evmbench-server \
  --metadata=startup-script='#!/bin/bash
    apt-get update -qq
    apt-get install -y -qq docker.io docker-compose-v2 debian-keyring debian-archive-keyring apt-transport-https curl
    systemctl enable --now docker
    # Install Caddy
    curl -1sLf "https://dl.cloudsmith.io/public/caddy/stable/gpg.key" | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf "https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt" | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq
    apt-get install -y -qq caddy
    systemctl enable caddy
  '

echo "Waiting for VM to boot..."
sleep 10

# ── 2. Create firewall rules ──
for PORT in 80 443; do
  RULE="evmbench-allow-${PORT}"
  if ! gcloud compute firewall-rules describe "$RULE" &>/dev/null; then
    gcloud compute firewall-rules create "$RULE" \
      --allow="tcp:${PORT}" \
      --target-tags=evmbench-server \
      --description="evmbench: allow port ${PORT}"
  fi
done

# ── 3. Get external IP ──
EXTERNAL_IP=$(gcloud compute instances describe "$NAME" \
  --zone="$ZONE" \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "=== VM created ==="
echo "  External IP: $EXTERNAL_IP"
echo ""
echo "=== Next steps ==="
echo ""
echo "1) Point DNS records to $EXTERNAL_IP:"
echo "     api.${DOMAIN}  →  A  ${EXTERNAL_IP}"
echo "     (and app.${DOMAIN} → Vercel CNAME if not done yet)"
echo ""
echo "2) Wait for startup script to finish (~2 min), then SSH in:"
echo "     gcloud compute ssh $NAME --zone=$ZONE"
echo ""
echo "3) On the VM, clone and deploy:"
echo "     git clone <YOUR_REPO_URL> /opt/evmbench"
echo "     cd /opt/evmbench/backend"
echo "     cp .env.production .env   # then edit with real secrets"
echo ""
echo "     # Generate secrets easily:"
echo "     python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
echo ""
echo "     # Build & start"
echo "     docker compose up -d --build"
echo ""
echo "     # Set up Caddy"
echo "     cp Caddyfile /etc/caddy/Caddyfile"
echo "     echo 'BACKEND_DOMAIN=api.${DOMAIN}' >> /etc/default/caddy"
echo "     systemctl restart caddy"
echo ""
echo "4) In Vercel project settings:"
echo "     - Root Directory: frontend"
echo "     - Build Command: bun run build"
echo "     - Output Directory: out"
echo "     - Framework Preset: Next.js"
echo "     - Environment variable: NEXT_PUBLIC_API_BASE=https://api.${DOMAIN}"
echo "     - Add custom domain: app.${DOMAIN}"
echo ""
echo "5) Trigger a Vercel redeploy so NEXT_PUBLIC_API_BASE is baked in."
