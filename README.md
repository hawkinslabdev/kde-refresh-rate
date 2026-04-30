# KDE Refresh Rate Switcher

[![License](https://img.shields.io/badge/license-AGPL%203.0-blue)](LICENSE)

Switch monitor refresh rates directly from the KDE system tray.

![Screenshot](.github/assets/example.webp)

## Usage

Click or right-click the monitor icon in your system tray. Each display appears as a submenu, select any mode to apply it immediately. Use the middle-click (e.g. the scroll wheel) to switch without opening the menu (only for the main screen).

## Setup

#### Requirements

- KDE Plasma 6 (Wayland or X11)
- Fedora or any RPM-based distro
- Python 3

The application has only been tested on KDE Plasma 6.6 (Wayland). Should work on KDE 5 and X11 sessions as well, but no guarantees.

#### Installation

It's pretty straight forward to set this up. As I currently have not set-up a deployment pipeline, you'll have to clone the repository and run `install.sh`:

```bash
git clone https://github.com/yourusername/kde-refresh-rate
cd kde-refresh-rate
./install.sh
```

The installation script installs `python3-pyqt6` and `kscreen`, makes the script executable, and registers it as a KDE autostart entry so it launches on every login.

#### Manual setup

```bash
sudo dnf install python3-pyqt6 kscreen
chmod +x refresh_rate_tray.py
python3 refresh_rate_tray.py
```

That's all.

## License

Free for open source projects and personal use under the **AGPL 3.0** license. For more information, please see the [license](LICENSE) file.

## Contributing

Contributions are always welcome! Please submit issues and pull requests, you'll probably know what to do.