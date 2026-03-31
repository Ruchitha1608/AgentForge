#!/bin/bash
# deploy.sh — Push updates from local and restart the EC2 service.
# Usage: EC2_IP=your.ip.here ./deploy.sh

set -e

EC2_IP="${EC2_IP:-YOUR_EC2_IP}"
EC2_USER="${EC2_USER:-ubuntu}"
EC2_KEY="${EC2_KEY:-~/.ssh/agentforge.pem}"

echo "==> Committing and pushing local changes..."
git add .
git commit -m "deploy: $(date '+%Y-%m-%d %H:%M')" || echo "Nothing new to commit"
git push

echo "==> Deploying to EC2 at ${EC2_IP}..."
ssh -i "${EC2_KEY}" "${EC2_USER}@${EC2_IP}" << 'REMOTE'
  set -e
  cd /home/ubuntu/agentforge
  git pull
  pip3 install -r backend/requirements.txt -q
  systemctl restart agentforge
  echo "Service restarted. Waiting for startup..."
  sleep 3
REMOTE

echo "==> Testing health endpoint..."
HEALTH=$(curl -s "http://${EC2_IP}/health")
echo "Health: ${HEALTH}"

if echo "$HEALTH" | grep -q '"status":"ok"'; then
  echo ""
  echo "  Deployed successfully!"
  echo "  API: http://${EC2_IP}/health"
else
  echo ""
  echo "  WARNING: Health check returned unexpected response."
  echo "  Check: ssh -i ${EC2_KEY} ${EC2_USER}@${EC2_IP} journalctl -u agentforge -n 50"
fi
