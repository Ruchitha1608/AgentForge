#!/bin/bash
# setup.sh — One-time setup on a fresh EC2 Ubuntu 22.04 t2.micro.
# Run as: chmod +x setup.sh && ./setup.sh

set -e

echo "==> Updating system packages..."
apt update && apt upgrade -y

echo "==> Installing Python 3.11, pip, git, nginx..."
apt install -y python3.11 python3.11-venv python3-pip git nginx

echo "==> Installing and starting Redis..."
apt install -y redis-server
systemctl enable redis-server
systemctl start redis-server
redis-cli ping && echo "Redis: OK"

echo "==> Cloning AgentForge repo..."
cd /home/ubuntu
git clone https://github.com/yourusername/agentforge.git || (cd agentforge && git pull)

echo "==> Installing Python dependencies..."
cd /home/ubuntu/agentforge/backend
pip3 install -r requirements.txt

echo "==> Creating .env from example..."
if [ ! -f .env ]; then
  cp .env.example .env
  echo ""
  echo "  *** ACTION REQUIRED: edit /home/ubuntu/agentforge/backend/.env"
  echo "  *** and add your OPENAI_API_KEY before starting the service."
  echo ""
fi

echo "==> Creating systemd service..."
cat > /etc/systemd/system/agentforge.service << 'EOF'
[Unit]
Description=AgentForge FastAPI
After=network.target redis-server.service

[Service]
User=ubuntu
WorkingDirectory=/home/ubuntu/agentforge/backend
EnvironmentFile=/home/ubuntu/agentforge/backend/.env
ExecStart=/usr/bin/python3 -m uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable agentforge

echo "==> Configuring nginx reverse proxy..."
cat > /etc/nginx/sites-available/agentforge << 'EOF'
server {
    listen 80;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        add_header Access-Control-Allow-Origin *;
        proxy_read_timeout 120s;
    }
}
EOF

ln -sf /etc/nginx/sites-available/agentforge /etc/nginx/sites-enabled/agentforge
rm -f /etc/nginx/sites-enabled/default
nginx -t && systemctl reload nginx

PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "YOUR_EC2_IP")

echo ""
echo "=========================================="
echo "  Setup complete!"
echo "  1. Edit backend/.env and add OPENAI_API_KEY"
echo "  2. systemctl start agentforge"
echo "  3. Test: curl http://${PUBLIC_IP}/health"
echo "=========================================="
