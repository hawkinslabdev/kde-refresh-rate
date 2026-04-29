# kde-refresh-rate

Switch monitor refresh rates directly from the KDE system tray.

No settings window. No extra clicks. Right-click the tray icon, pick your rate, done.

> [!NOTE]
> Tested on KDE Plasma 6.6 (Wayland). Should work on KDE 5 and X11 sessions as well.

![tray menu screenshot placeholder](docs/screenshot.png)

---

## Features

- All connected displays, each with their own submenu
- Main screen listed first, labeled **[Main]**
- Active mode is checkmarked — always know what's currently set
- Auto-updates when you plug/unplug a monitor or change display settings elsewhere
- Zero background overhead — event-driven with a lightweight fallback poll

## Requirements

- KDE Plasma 6 (Wayland or X11)
- Fedora or any RPM-based distro

## Install

```bash
git clone https://github.com/yourusername/kde-refresh-rate
cd kde-refresh-rate
./install.sh
```

`install.sh` installs `python3-pyqt6` and `kscreen`, makes the script executable, and registers it as a KDE autostart entry so it launches on every login.

## Manual setup

```bash
sudo dnf install python3-pyqt6 kscreen
chmod +x refresh_rate_tray.py
python3 refresh_rate_tray.py
```

## Usage

Click or right-click the monitor icon in your system tray. Each display appears as a submenu — select any mode to apply it immediately.

Configuration changes made outside the app (KDE Display Settings, `kscreen-doctor`, hotplug events) are picked up automatically without a restart.

## How it works

Reads display configuration via `kscreen-doctor --json` and applies mode changes via:

```
kscreen-doctor output.<name>.mode.<id>
```

Change detection uses a `QFileSystemWatcher` on `~/.local/share/kscreen/` for instant response, backed by a 10-second poll as a fallback for events the filesystem watcher misses (e.g. compositor-driven changes).

## License

MIT
