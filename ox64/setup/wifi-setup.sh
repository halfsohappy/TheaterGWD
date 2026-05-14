#!/bin/sh
# TheaterGWD – Ox64 WiFi Setup
# Configures the Ox64 as a WiFi client (station mode) via OpenWRT UCI.
# Run this over the USB serial console on first boot.

echo ""
echo "  Ox64 WiFi Setup"
echo "  ───────────────"
echo ""

printf "  Network name (SSID): "
read -r SSID

printf "  Password:            "
# Disable echo for password entry if the terminal supports it
stty -echo 2>/dev/null; read -r PASSWORD; stty echo 2>/dev/null
echo ""
echo ""

if [ -z "$SSID" ]; then
    echo "ERROR: SSID cannot be empty."
    exit 1
fi

echo "  Configuring WiFi..."

# Ensure the radio is on
uci set wireless.radio0.disabled='0'

# Find or create a sta wifi-iface on radio0
IFACE_IDX=""
COUNT=0
while uci get "wireless.@wifi-iface[$COUNT]" >/dev/null 2>&1; do
    RADIO=$(uci get "wireless.@wifi-iface[$COUNT].device" 2>/dev/null)
    MODE=$(uci get "wireless.@wifi-iface[$COUNT].mode" 2>/dev/null)
    if [ "$RADIO" = "radio0" ] && [ "$MODE" = "sta" ]; then
        IFACE_IDX=$COUNT
        break
    fi
    COUNT=$((COUNT + 1))
done

if [ -z "$IFACE_IDX" ]; then
    # Create a new sta interface
    uci add wireless wifi-iface >/dev/null
    IFACE_IDX=$COUNT
    uci set "wireless.@wifi-iface[$IFACE_IDX].device"='radio0'
    uci set "wireless.@wifi-iface[$IFACE_IDX].mode"='sta'
    uci set network.wlan=interface
    uci set network.wlan.device='wlan0'
    uci set network.wlan.proto='dhcp'
fi

uci set "wireless.@wifi-iface[$IFACE_IDX].ssid"="$SSID"
uci set "wireless.@wifi-iface[$IFACE_IDX].disabled"='0'

if [ -n "$PASSWORD" ]; then
    uci set "wireless.@wifi-iface[$IFACE_IDX].encryption"='psk2'
    uci set "wireless.@wifi-iface[$IFACE_IDX].key"="$PASSWORD"
else
    uci set "wireless.@wifi-iface[$IFACE_IDX].encryption"='none'
fi

uci commit wireless
uci commit network

echo "  Restarting wireless..."
wifi reload

echo "  Waiting for connection (up to 20 seconds)..."
ATTEMPTS=0
IP=""
while [ $ATTEMPTS -lt 20 ] && [ -z "$IP" ]; do
    sleep 1
    IP=$(ip addr show wlan0 2>/dev/null \
        | grep 'inet ' \
        | awk '{print $2}' \
        | cut -d/ -f1)
    ATTEMPTS=$((ATTEMPTS + 1))
done

echo ""
if [ -n "$IP" ]; then
    echo "  ✓ Connected!"
    echo ""
    echo "  IP address:  $IP"
    echo "  SSH access:  ssh root@$IP"
    echo ""
    echo "  Next step: run install.sh"
    echo "    wget -qO- https://github.com/halfsohappy/TheaterGWD/raw/main/ox64/setup/install.sh | sh"
else
    echo "  Connection not detected yet. Check status with:"
    echo "    ip addr show wlan0"
    echo "    logread | grep wifi"
fi
echo ""
