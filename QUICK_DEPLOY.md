# Quick Deploy Cheat Sheet

## 🚀 Fastest Way to Deploy

### Step 1: Open Firewall
```bash
sudo ufw allow 7860/tcp
```

### Step 2: Launch with Password
```bash
python launch_ui_secure.py \
  --host 0.0.0.0 \
  --port 7860 \
  --username admin \
  --password "YourSecurePassword123"
```

### Step 3: Access from Browser
```
http://YOUR_VPS_IP:7860
```

Login with:
- Username: `admin`
- Password: `YourSecurePassword123`

---

## 🔒 Production Deployment (Background Service)

### Quick systemd Setup

```bash
# Create service file
sudo tee /etc/systemd/system/cudabot-ui.service > /dev/null <<EOF
[Unit]
Description=AI Documentation Assistant - Gradio UI
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$(pwd)
Environment="GRADIO_PASSWORD=YourSecurePassword123"
Environment="GRADIO_USERNAME=admin"
ExecStart=$(which python3) $(pwd)/launch_ui_secure.py --host 0.0.0.0 --port 7860
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Start service
sudo systemctl daemon-reload
sudo systemctl enable cudabot-ui
sudo systemctl start cudabot-ui

# Check status
sudo systemctl status cudabot-ui
```

---

## 🌐 Alternative: Gradio Share (No Firewall Needed)

```bash
# Creates temporary public link
python launch_ui.py --share
```

You'll get a URL like: `https://xxxxx.gradio.live`

---

## 📊 Common Commands

```bash
# Check if port is open
sudo lsof -i :7860

# View logs (systemd)
sudo journalctl -u cudabot-ui -f

# Stop service
sudo systemctl stop cudabot-ui

# Restart service
sudo systemctl restart cudabot-ui

# Run in background (screen)
screen -S gradio
python launch_ui_secure.py --host 0.0.0.0 --port 7860
# Press Ctrl+A then D to detach

# Reattach to screen
screen -r gradio
```

---

## 🔧 Troubleshooting

**Can't connect?**
```bash
# 1. Check if running
ps aux | grep gradio

# 2. Check firewall
sudo ufw status

# 3. Verify listening on correct interface
sudo netstat -tlnp | grep 7860
# Should show: 0.0.0.0:7860 (not 127.0.0.1:7860)

# 4. Test locally
curl http://localhost:7860
```

**Port in use?**
```bash
# Find process
sudo lsof -i :7860

# Kill it
sudo kill -9 <PID>

# Or use different port
python launch_ui_secure.py --port 8080
```

---

## 🎯 Your VPS Info

Fill this in for reference:

- **VPS IP**: `_______________`
- **Port**: `7860`
- **URL**: `http://_______________:7860`
- **Username**: `admin`
- **Password**: `_______________`

---

**That's it!** You're deployed! 🎉
