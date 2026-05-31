#!/usr/bin/env bash
# Starts a local MediaMTX RTMP server so DJI Mimo can push the Action 2 stream to your laptop.
# Requires: Docker Desktop running
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Pick the first routable LAN IP across common interface names
LAN_IP=$(
  for iface in en0 en1 en2 wlan0; do
    ip=$(ipconfig getifaddr "$iface" 2>/dev/null)
    if [[ -n "$ip" && "$ip" != 169.254.* ]]; then echo "$ip"; break; fi
  done
)
LAN_IP="${LAN_IP:-$(hostname -I 2>/dev/null | awk '{print $1}')}"
LAN_IP="${LAN_IP:-<your-laptop-ip>}"

RTMP_URL="rtmp://${LAN_IP}/live/car"

# Save URL to file so telemetry_app can read it automatically
echo "$RTMP_URL" > "$SCRIPT_DIR/.rtmp_url"

# Print URL before Docker starts (in case you need to copy it early)
echo ""
echo "  ┌─────────────────────────────────────────────┐"
echo "  │  DJI Mimo → Live Stream → Custom RTMP       │"
echo "  │                                             │"
printf "  │  %-43s │\n" "URL: $RTMP_URL"
echo "  │                                             │"
echo "  │  Starting server... (URL repeated below)    │"
echo "  └─────────────────────────────────────────────┘"
echo ""

# Run MediaMTX; when it's ready reprint the URL so it's visible above the log noise
docker run --rm \
  -v "$SCRIPT_DIR/mediamtx.yml:/mediamtx.yml" \
  -p 1935:1935 \
  bluenviron/mediamtx &

DOCKER_PID=$!

# Wait for port 1935 to open (up to 15s)
for i in $(seq 1 15); do
  if nc -z localhost 1935 2>/dev/null; then break; fi
  sleep 1
done

echo ""
echo "  ┌─────────────────────────────────────────────┐"
echo "  │  SERVER READY — paste this into DJI Mimo:   │"
echo "  │                                             │"
printf "  │  %-43s │\n" "$RTMP_URL"
echo "  │                                             │"
echo "  │  Press Ctrl+C to stop.                      │"
echo "  └─────────────────────────────────────────────┘"
echo ""

# Keep running until Ctrl+C; kill Docker on exit
trap "kill $DOCKER_PID 2>/dev/null; rm -f '$SCRIPT_DIR/.rtmp_url'; exit 0" INT TERM
wait $DOCKER_PID
