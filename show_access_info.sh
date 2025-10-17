#!/bin/bash
# Display access information for the Gradio UI

echo ""
echo "╔════════════════════════════════════════════════════════════╗"
echo "║     AI Documentation Assistant - Access Information        ║"
echo "╚════════════════════════════════════════════════════════════╝"
echo ""

# Get VPS IPs
VPS_IP_V4=$(curl -4 -s ifconfig.me 2>/dev/null || curl -4 -s icanhazip.com 2>/dev/null || echo "Not available")
VPS_IP_V6=$(curl -6 -s ifconfig.me 2>/dev/null || curl -6 -s icanhazip.com 2>/dev/null || echo "Not available")

echo "🌐 Your VPS IP Addresses:"
echo "   IPv4: $VPS_IP_V4"
echo "   IPv6: $VPS_IP_V6"
echo ""

# Check if service is running
PORT=7860
if sudo netstat -tlnp 2>/dev/null | grep -q ":$PORT"; then
    echo "✅ Service Status: RUNNING"
    echo ""
    echo "🔗 Access URLs:"
    echo "   Local:   http://localhost:$PORT"
    if [ "$VPS_IP_V4" != "Not available" ]; then
        echo "   IPv4:    http://$VPS_IP_V4:$PORT"
    fi
    if [ "$VPS_IP_V6" != "Not available" ]; then
        echo "   IPv6:    http://[$VPS_IP_V6]:$PORT"
    fi
    echo ""

    # Check if running on correct interface
    if sudo netstat -tlnp 2>/dev/null | grep ":$PORT" | grep -q "0.0.0.0"; then
        echo "✅ Listening on: All interfaces (0.0.0.0) - Accessible from internet"
    else
        echo "⚠️  Listening on: Localhost only (127.0.0.1) - NOT accessible from internet"
        echo "   Fix: Restart with --host 0.0.0.0"
    fi
else
    echo "❌ Service Status: NOT RUNNING"
    echo ""
    echo "To start the service:"
    echo "   python launch_ui_secure.py --host 0.0.0.0 --port $PORT"
fi

echo ""

# Check firewall status
echo "🔥 Firewall Status:"
if command -v ufw &> /dev/null; then
    if sudo ufw status | grep -q "Status: active"; then
        if sudo ufw status | grep -q "$PORT"; then
            echo "   ✅ UFW is active and port $PORT is allowed"
        else
            echo "   ⚠️  UFW is active but port $PORT is NOT allowed"
            echo "   Fix: sudo ufw allow $PORT/tcp"
        fi
    else
        echo "   ℹ️  UFW is inactive"
    fi
elif command -v firewall-cmd &> /dev/null; then
    if sudo firewall-cmd --state 2>/dev/null | grep -q "running"; then
        if sudo firewall-cmd --list-ports | grep -q "$PORT"; then
            echo "   ✅ Firewalld is active and port $PORT is allowed"
        else
            echo "   ⚠️  Firewalld is active but port $PORT is NOT allowed"
            echo "   Fix: sudo firewall-cmd --permanent --add-port=$PORT/tcp && sudo firewall-cmd --reload"
        fi
    else
        echo "   ℹ️  Firewalld is not running"
    fi
else
    echo "   ℹ️  No firewall detected (or using iptables)"
fi

echo ""

# Check available targets
echo "🎯 Available Documentation Targets:"
if [ -d "config/targets" ]; then
    TARGETS=$(ls config/targets/*.yaml 2>/dev/null | xargs -n1 basename | sed 's/.yaml//' || echo "None")
    echo "   $TARGETS"
else
    echo "   None found"
fi

echo ""
echo "════════════════════════════════════════════════════════════"
echo ""
echo "📚 Quick Start:"
echo "   1. Ensure firewall port is open: sudo ufw allow $PORT/tcp"
echo "   2. Launch: python launch_ui_secure.py --host 0.0.0.0"
if [ "$VPS_IP_V4" != "Not available" ]; then
    echo "   3. Visit: http://$VPS_IP_V4:$PORT"
else
    echo "   3. Visit: http://[$VPS_IP_V6]:$PORT"
fi
echo ""
echo "📖 Full documentation: cat DEPLOYMENT_GUIDE.md"
echo ""
