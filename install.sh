#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP="$SCRIPT_DIR/refresh_rate_tray.py"
AUTOSTART_DIR="$HOME/.config/autostart"
DESKTOP_FILE="$AUTOSTART_DIR/refresh-rate-tray.desktop"

echo "==> Installing dependencies..."
sudo dnf install -y python3-pyqt6 kscreen

echo "==> Making script executable..."
chmod +x "$APP"

echo "==> Setting up KDE autostart..."
mkdir -p "$AUTOSTART_DIR"
cat > "$DESKTOP_FILE" << EOF
[Desktop Entry]
Name=Refresh Rate Switcher
Comment=Switch monitor refresh rates from system tray
Exec=/usr/bin/python3 $APP
Icon=video-display
Type=Application
Categories=Utility;
X-KDE-autostart-phase=2
EOF

echo ""
echo "Done!"
echo "  Autostart entry: $DESKTOP_FILE"
echo "  To start now:    python3 $APP"
