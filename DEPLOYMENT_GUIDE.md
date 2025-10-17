# VPS Deployment Guide

Complete guide for deploying the Gradio UI on a VPS and accessing it from anywhere in the world.

## Quick Start

### Option 1: Secure Deployment (Recommended)

```bash
# Set password via environment variable
export GRADIO_PASSWORD="your_secure_password_here"

# Launch with authentication
python launch_ui_secure.py --host 0.0.0.0 --port 7860

# Access from anywhere at: http://YOUR_VPS_IP:7860
```

### Option 2: With Gradio Share Link

```bash
# Creates a temporary public URL (no firewall config needed)
python launch_ui.py --share
```

## Detailed Setup

### Step 1: Check Your VPS IP

```bash
# Find your public IP
curl ifconfig.me
# or
ip addr show
```

### Step 2: Open Firewall Port

#### UFW (Ubuntu/Debian)
```bash
# Check status
sudo ufw status

# Allow port 7860
sudo ufw allow 7860/tcp

# Verify
sudo ufw status numbered
```

#### Firewalld (CentOS/RHEL/Fedora)
```bash
# Check status
sudo firewall-cmd --state

# Allow port 7860
sudo firewall-cmd --permanent --add-port=7860/tcp
sudo firewall-cmd --reload

# Verify
sudo firewall-cmd --list-ports
```

#### iptables (Manual)
```bash
# Allow port 7860
sudo iptables -A INPUT -p tcp --dport 7860 -j ACCEPT

# Save rules
sudo netfilter-persistent save
# or on CentOS/RHEL:
sudo service iptables save
```

#### Cloud Provider Firewall
Don't forget to also open the port in your cloud provider's firewall/security group:
- **AWS**: EC2 Security Groups
- **GCP**: VPC Firewall Rules
- **Azure**: Network Security Groups
- **DigitalOcean**: Firewalls
- **Linode**: Cloud Firewalls

### Step 3: Launch the Application

#### Option A: With Password Protection (Recommended)

```bash
# Set credentials
export GRADIO_USERNAME="admin"
export GRADIO_PASSWORD="your_secure_password"

# Launch
python launch_ui_secure.py --host 0.0.0.0 --port 7860
```

Or pass directly:
```bash
python launch_ui_secure.py \
  --host 0.0.0.0 \
  --port 7860 \
  --username admin \
  --password "your_secure_password"
```

#### Option B: Without Authentication (Not Recommended)
```bash
python launch_ui.py --host 0.0.0.0 --port 7860
```

### Step 4: Access from Browser

Open any browser and go to:
```
http://YOUR_VPS_IP:7860
```

Example:
```
http://192.168.1.100:7860
http://123.45.67.89:7860
```

## Running as a Background Service

### Method 1: Using systemd (Best for Production)

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/cudabot-ui.service
```

Add this content:

```ini
[Unit]
Description=AI Documentation Assistant - Gradio UI
After=network.target

[Service]
Type=simple
User=YOUR_USERNAME
WorkingDirectory=/root/cudabot
Environment="GRADIO_PASSWORD=your_secure_password"
Environment="GRADIO_USERNAME=admin"
ExecStart=/usr/bin/python3 /root/cudabot/launch_ui_secure.py --host 0.0.0.0 --port 7860
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable on boot
sudo systemctl enable cudabot-ui

# Start service
sudo systemctl start cudabot-ui

# Check status
sudo systemctl status cudabot-ui

# View logs
sudo journalctl -u cudabot-ui -f
```

### Method 2: Using screen (Quick and Easy)

```bash
# Install screen if needed
sudo apt install screen  # Ubuntu/Debian
sudo yum install screen  # CentOS/RHEL

# Start a screen session
screen -S gradio-ui

# Launch the app
python launch_ui_secure.py --host 0.0.0.0 --port 7860

# Detach from screen: Press Ctrl+A, then D

# Reattach later
screen -r gradio-ui

# List all screens
screen -ls
```

### Method 3: Using nohup (Simple Background Process)

```bash
# Run in background
nohup python launch_ui_secure.py --host 0.0.0.0 --port 7860 > gradio.log 2>&1 &

# Check if running
ps aux | grep gradio

# View logs
tail -f gradio.log

# Stop the process
kill $(pgrep -f launch_ui_secure)
```

## SSL/HTTPS Setup (Recommended for Production)

### Option 1: Using Nginx Reverse Proxy with Let's Encrypt

#### Install Nginx and Certbot
```bash
# Ubuntu/Debian
sudo apt update
sudo apt install nginx certbot python3-certbot-nginx

# CentOS/RHEL
sudo yum install nginx certbot python3-certbot-nginx
```

#### Configure Nginx

Create config file:
```bash
sudo nano /etc/nginx/sites-available/cudabot
```

Add this configuration:
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:7860;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable the site:
```bash
sudo ln -s /etc/nginx/sites-available/cudabot /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

#### Get SSL Certificate
```bash
sudo certbot --nginx -d your-domain.com
```

Now launch the app locally (only Nginx needs to be public):
```bash
python launch_ui_secure.py --host 127.0.0.1 --port 7860
```

Access via HTTPS:
```
https://your-domain.com
```

### Option 2: Using Caddy (Automatic HTTPS)

#### Install Caddy
```bash
# Ubuntu/Debian
sudo apt install -y debian-keyring debian-archive-keyring apt-transport-https
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/gpg.key' | sudo gpg --dearmor -o /usr/share/keyrings/caddy-stable-archive-keyring.gpg
curl -1sLf 'https://dl.cloudsmith.io/public/caddy/stable/debian.deb.txt' | sudo tee /etc/apt/sources.list.d/caddy-stable.list
sudo apt update
sudo apt install caddy
```

#### Configure Caddy

Edit Caddyfile:
```bash
sudo nano /etc/caddy/Caddyfile
```

Add:
```
your-domain.com {
    reverse_proxy localhost:7860
}
```

Restart Caddy:
```bash
sudo systemctl restart caddy
```

Caddy will automatically obtain and renew SSL certificates!

## Security Best Practices

### 1. Use Strong Passwords
```bash
# Generate a strong password
openssl rand -base64 32
```

### 2. Limit Access by IP (Optional)

Using UFW:
```bash
# Allow only specific IPs
sudo ufw deny 7860
sudo ufw allow from 203.0.113.0/24 to any port 7860
```

Using Nginx:
```nginx
location / {
    allow 203.0.113.0/24;
    deny all;
    proxy_pass http://127.0.0.1:7860;
}
```

### 3. Rate Limiting with Nginx

Add to nginx config:
```nginx
limit_req_zone $binary_remote_addr zone=gradio:10m rate=10r/m;

location / {
    limit_req zone=gradio burst=20;
    proxy_pass http://127.0.0.1:7860;
}
```

### 4. Regular Updates
```bash
# Update system packages
sudo apt update && sudo apt upgrade

# Update Python packages
pip install --upgrade -r requirements.txt
```

## Monitoring and Logs

### View Application Logs

With systemd:
```bash
sudo journalctl -u cudabot-ui -f
```

With screen:
```bash
screen -r gradio-ui
```

With nohup:
```bash
tail -f gradio.log
```

### Monitor System Resources

```bash
# CPU and memory usage
htop

# Disk usage
df -h

# Network connections
sudo netstat -tlnp | grep 7860
```

## Troubleshooting

### Port Already in Use

```bash
# Find what's using the port
sudo lsof -i :7860
# or
sudo netstat -tlnp | grep 7860

# Kill the process
sudo kill -9 PID
```

### Can't Connect from Outside

1. **Check firewall**:
   ```bash
   sudo ufw status
   ```

2. **Verify server is listening on all interfaces**:
   ```bash
   sudo netstat -tlnp | grep 7860
   # Should show 0.0.0.0:7860, not 127.0.0.1:7860
   ```

3. **Check cloud provider security group/firewall**

4. **Test locally first**:
   ```bash
   curl http://localhost:7860
   ```

### Permission Denied

```bash
# Use a port above 1024, or run as root (not recommended)
python launch_ui_secure.py --port 8080
```

### Service Won't Start

```bash
# Check service status
sudo systemctl status cudabot-ui

# View detailed logs
sudo journalctl -u cudabot-ui -n 50 --no-pager

# Test manual start
cd /root/cudabot
python launch_ui_secure.py
```

## Performance Optimization

### 1. Use Production WSGI Server

For better performance under load, consider using a production server.

### 2. Increase Worker Threads

In `gradio_app.py`, modify launch:
```python
demo.queue(max_size=20).launch(...)
```

### 3. Enable Caching

Add caching for frequently accessed data.

### 4. Monitor Resources

```bash
# Install monitoring tools
sudo apt install htop iotop nethogs
```

## Alternative Deployment: Docker (Advanced)

Create a Dockerfile:
```dockerfile
FROM python:3.10-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["python", "launch_ui_secure.py", "--host", "0.0.0.0", "--port", "7860"]
```

Build and run:
```bash
docker build -t cudabot-ui .
docker run -d -p 7860:7860 \
  -e GRADIO_PASSWORD=your_password \
  -v $(pwd)/data:/app/data \
  cudabot-ui
```

## Summary: Quick Commands

```bash
# 1. Open firewall
sudo ufw allow 7860/tcp

# 2. Set password
export GRADIO_PASSWORD="your_secure_password"

# 3. Launch (foreground)
python launch_ui_secure.py --host 0.0.0.0 --port 7860

# OR Launch (background with screen)
screen -S gradio
python launch_ui_secure.py --host 0.0.0.0 --port 7860
# Press Ctrl+A, D to detach

# 4. Access from browser
# http://YOUR_VPS_IP:7860
```

---

**You're now ready to deploy!** 🚀

Access your AI Documentation Assistant from anywhere in the world with a simple browser visit to your VPS IP!
