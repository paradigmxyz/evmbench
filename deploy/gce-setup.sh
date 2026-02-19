#!/usr/bin/env bash
# ── svmbench gce deployment script ──
# provisions a gce vm, installs docker + caddy, deploys the backend stack.
#
# usage:
#   ./deploy/gce-setup.sh --domain YOURDOMAIN.com [--zone us-central1-a] [--machine e2-standard-2] [--name svmbench]
#
# prerequisites:
#   - gcloud cli authenticated with a project set
#   - a domain with dns you can point to the vm ip
#   - backend/.env filled in from .env.production template
set -euo pipefail

# ── defaults ──
ZONE="us-central1-a"
MACHINE="e2-standard-2"
NAME="svmbench"
DOMAIN=""
REPO_URL=""
DISK_SIZE="40GB"

# ── parse args ──
while [[ $# -gt 0 ]]; do
  case $1 in
    --domain)  DOMAIN="$2";  shift 2 ;;
    --zone)    ZONE="$2";    shift 2 ;;
    --machine) MACHINE="$2"; shift 2 ;;
    --name)    NAME="$2";    shift 2 ;;
    --repo)    REPO_URL="$2"; shift 2 ;;
    *) echo "unknown option: $1"; exit 1 ;;
  esac
done

if [[ -z "$DOMAIN" ]]; then
  echo "error: --domain is required (e.g. --domain example.com)"
  exit 1
fi

echo "=== provisioning gce instance ==="
echo "  name:    $NAME"
echo "  zone:    $ZONE"
echo "  machine: $MACHINE"
echo "  domain:  $DOMAIN"
echo ""

# ── 1. create vm ──
gcloud compute instances create "$NAME" \
  --zone="$ZONE" \
  --machine-type="$MACHINE" \
  --image-family=ubuntu-2404-lts-amd64 \
  --image-project=ubuntu-os-cloud \
  --boot-disk-size="$DISK_SIZE" \
  --tags=svmbench-server \
  --metadata=startup-script='#!/bin/bash
    apt-get update -qq
    apt-get install -y -qq docker.io docker-compose-v2 debian-keyring debian-archive-keyring apt-transport-https curl
    systemctl enable --now docker
    # install caddy
    curl -1sLf "https://dl.cloudsmith.io/public/caddy/stable/gpg.key" | gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
    curl -1sLf "https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt" | tee /etc/apt/sources.list.d/caddy-stable.list
    apt-get update -qq
    apt-get install -y -qq caddy
    systemctl enable caddy
  '

echo "waiting for vm to boot..."
sleep 10

# ── 2. create firewall rules ──
for PORT in 80 443; do
  RULE="svmbench-allow-${PORT}"
  if ! gcloud compute firewall-rules describe "$RULE" &>/dev/null; then
    gcloud compute firewall-rules create "$RULE" \
      --allow="tcp:${PORT}" \
      --target-tags=svmbench-server \
      --description="svmbench: allow port ${PORT}"
  fi
done

# ── 3. get external ip ──
EXTERNAL_IP=$(gcloud compute instances describe "$NAME" \
  --zone="$ZONE" \
  --format='get(networkInterfaces[0].accessConfigs[0].natIP)')

echo ""
echo "=== vm created ==="
echo "  external ip: $EXTERNAL_IP"
echo ""
echo "=== next steps ==="
echo ""
echo "1) point dns records to $EXTERNAL_IP:"
echo "     api.${DOMAIN}  →  A  ${EXTERNAL_IP}"
echo "     (and app.${DOMAIN} → vercel cname if not done yet)"
echo ""
echo "2) wait for startup script to finish (~2 min), then ssh in:"
echo "     gcloud compute ssh $NAME --zone=$ZONE"
echo ""
echo "3) on the vm, clone and deploy:"
echo "     git clone <YOUR_REPO_URL> /opt/svmbench"
echo "     cd /opt/svmbench/backend"
echo "     cp .env.production .env   # then edit with real secrets"
echo ""
echo "     # generate secrets easily:"
echo "     python3 -c \"import secrets; print(secrets.token_urlsafe(32))\""
echo ""
echo "     # build & start"
echo "     docker compose up -d --build"
echo ""
echo "     # set up caddy"
echo "     cp Caddyfile /etc/caddy/Caddyfile"
echo "     echo 'BACKEND_DOMAIN=api.${DOMAIN}' >> /etc/default/caddy"
echo "     systemctl restart caddy"
echo ""
echo "4) in vercel project settings:"
echo "     - root directory: frontend"
echo "     - build command: bun run build"
echo "     - output directory: out"
echo "     - framework preset: next.js"
echo "     - environment variable: NEXT_PUBLIC_API_BASE=https://api.${DOMAIN}"
echo "     - add custom domain: app.${DOMAIN}"
echo ""
echo "5) trigger a vercel redeploy so NEXT_PUBLIC_API_BASE is baked in."
