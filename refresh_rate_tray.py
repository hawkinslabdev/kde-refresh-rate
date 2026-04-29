#!/usr/bin/env python3

import json
import os
import signal
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional

from PyQt6.QtCore import QEasingCurve, QLoggingCategory, QPropertyAnimation, QRectF, Qt, QTimer, QFileSystemWatcher
from PyQt6.QtGui import QAction, QActionGroup, QColor, QCursor, QIcon, QPainter, QPainterPath
from PyQt6.QtWidgets import (
    QApplication, QGraphicsOpacityEffect, QLabel, QMenu,
    QMessageBox, QSystemTrayIcon, QVBoxLayout, QWidget,
)


@dataclass
class Mode:
    id: str
    width: int
    height: int
    refresh_rate: float
    name: str = ""

    @property
    def label(self) -> str:
        if self.name and "@" in self.name:
            res, _, rate = self.name.partition("@")
            return f"{res} @ {rate} Hz"
        rate_str = f"{self.refresh_rate:.2f}".rstrip("0").rstrip(".")
        return f"{self.width}x{self.height} @ {rate_str} Hz"

    @property
    def rate_label(self) -> str:
        if self.name and "@" in self.name:
            _, _, rate = self.name.partition("@")
            return f"{rate} Hz"
        rate_str = f"{self.refresh_rate:.2f}".rstrip("0").rstrip(".")
        return f"{rate_str} Hz"


@dataclass
class Display:
    index: int
    name: str
    is_main: bool
    current_mode_id: str
    modes: list[Mode] = field(default_factory=list)

    @property
    def menu_label(self) -> str:
        suffix = "  [Main]    " if self.is_main else ""
        return f"Screen {self.index}: {self.name}{suffix}"


def query_displays() -> tuple[list[Display], Optional[str]]:
    try:
        result = subprocess.run(
            ["kscreen-doctor", "--json"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return [], result.stderr.strip() or "kscreen-doctor error"

        data = json.loads(result.stdout)
        enabled = [o for o in data.get("outputs", []) if o.get("enabled", False)]
        # KDE 6 uses priority (1 = main); KDE 5 used a primary bool
        enabled.sort(key=lambda o: (o.get("priority", 9999), 0 if o.get("primary") else 1, o.get("id", 9999)))
        min_priority = enabled[0].get("priority") if enabled else None

        displays = []
        for i, out in enumerate(enabled):
            modes = [
                Mode(
                    id=str(m.get("id", "")),
                    width=m.get("size", {}).get("width", 0),
                    height=m.get("size", {}).get("height", 0),
                    refresh_rate=float(m.get("refreshRate", 0)),
                    name=m.get("name", ""),
                )
                for m in out.get("modes", [])
            ]
            modes.sort(key=lambda m: (m.width * m.height, m.refresh_rate), reverse=True)

            is_main = (
                out.get("priority") == min_priority
                if min_priority is not None
                else bool(out.get("primary", i == 0))
            )

            displays.append(Display(
                index=i + 1,
                name=out.get("name", f"output{i + 1}"),
                is_main=is_main,
                current_mode_id=str(out.get("currentModeId", "")),
                modes=modes,
            ))

        return displays, None

    except FileNotFoundError:
        return [], "kscreen-doctor not found — install: sudo dnf install kscreen"
    except json.JSONDecodeError:
        return [], "Failed to parse kscreen-doctor output"
    except subprocess.TimeoutExpired:
        return [], "kscreen-doctor timed out"
    except Exception as e:
        return [], str(e)


class OsdOverlay(QWidget):
    _SHOW_MS = 2000
    _FADE_MS = 350

    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.BypassWindowManagerHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFixedSize(280, 100)
        self.setObjectName("osd")

        self._effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self._effect)

        self._anim = QPropertyAnimation(self._effect, b"opacity")
        self._anim.setDuration(self._FADE_MS)
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.finished.connect(self.hide)

        self._timer = QTimer()
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._start_fade)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(2)

        self._rate_label = QLabel()
        self._rate_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        rate_font = self._rate_label.font()
        rate_font.setPointSize(34)
        rate_font.setBold(True)
        self._rate_label.setFont(rate_font)
        self._rate_label.setStyleSheet("color: white; background: transparent;")

        self._sub_label = QLabel()
        self._sub_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub_font = self._sub_label.font()
        sub_font.setPointSize(10)
        self._sub_label.setFont(sub_font)
        self._sub_label.setStyleSheet("color: rgba(255,255,255,160); background: transparent;")

        layout.addStretch()
        layout.addWidget(self._rate_label)
        layout.addWidget(self._sub_label)
        layout.addStretch()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRoundedRect(QRectF(self.rect()), 20, 20)
        painter.fillPath(path, QColor(0, 0, 0, 43))

    def show_rate(self, rate_label: str, sub: str = "") -> None:
        self._timer.stop()
        self._anim.stop()
        self._effect.setOpacity(1.0)

        self._rate_label.setText(rate_label)
        self._sub_label.setText(sub)
        self._sub_label.setVisible(bool(sub))

        screen = QApplication.primaryScreen()
        geo = screen.geometry()
        self.move(
            geo.x() + (geo.width() - self.width()) // 2,
            geo.y() + (geo.height() - self.height()) // 2,
        )
        self.show()
        self.raise_()
        self._timer.start(self._SHOW_MS)

    def _start_fade(self) -> None:
        self._anim.setStartValue(1.0)
        self._anim.setEndValue(0.0)
        self._anim.start()


def apply_mode(output_name: str, mode_id: str) -> None:
    subprocess.Popen(
        ["kscreen-doctor", f"output.{output_name}.mode.{mode_id}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


class RefreshRateTray:
    _KSCREEN_DIR = os.path.expanduser("~/.local/share/kscreen")
    _POLL_MS = 10_000
    _APPLY_DELAY_MS = 1_500
    _DEBOUNCE_MS = 400

    def __init__(self, app: QApplication) -> None:
        self.app = app
        self._sig: list = []
        self._osd = OsdOverlay()

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self._find_icon())
        self.tray.setToolTip("Refresh Rate Switcher")
        self.tray.activated.connect(self._on_activated)

        self.menu = QMenu()
        self.menu.setStyleSheet("QMenu::item { padding-right: 28px; }")
        self.tray.setContextMenu(self.menu)

        self._setup_watcher()

        self._debounce = QTimer()
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(self._DEBOUNCE_MS)
        self._debounce.timeout.connect(self.rebuild_menu)

        # Fallback poll for Wayland compositor changes that bypass the fs watcher
        self._poll = QTimer()
        self._poll.setInterval(self._POLL_MS)
        self._poll.timeout.connect(self._poll_tick)
        self._poll.start()

        self.rebuild_menu()
        self.tray.show()

    def _find_icon(self) -> QIcon:
        for name in ("video-display-symbolic", "video-display", "monitor-symbolic", "monitor"):
            icon = QIcon.fromTheme(name)
            if not icon.isNull():
                return QIcon(icon.pixmap(22, 22))
        return QIcon()

    def _setup_watcher(self) -> None:
        watch_paths = []
        for subdir in ("", "outputs"):
            path = os.path.join(self._KSCREEN_DIR, subdir) if subdir else self._KSCREEN_DIR
            os.makedirs(path, exist_ok=True)
            watch_paths.append(path)

        self._watcher = QFileSystemWatcher(watch_paths)
        self._watcher.directoryChanged.connect(self._on_fs_change)
        self._watcher.fileChanged.connect(self._on_fs_change)

    def _on_activated(self, reason) -> None:
        try:
            if reason == QSystemTrayIcon.ActivationReason.Trigger:
                self.menu.popup(QCursor.pos())
            elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
                self._cycle_mode()
        except TypeError:
            pass  # PyQt6 enum conversion can fail during shutdown

    def _cycle_mode(self) -> None:
        displays, _ = query_displays()
        if len(displays) != 1:
            return
        display = displays[0]
        if len(display.modes) < 2:
            return
        current_idx = next(
            (i for i, m in enumerate(display.modes) if m.id == display.current_mode_id),
            0,
        )
        next_mode = display.modes[(current_idx + 1) % len(display.modes)]
        apply_mode(display.name, next_mode.id)
        # Delay OSD until after the screen flash
        QTimer.singleShot(self._APPLY_DELAY_MS, self.rebuild_menu)
        QTimer.singleShot(self._APPLY_DELAY_MS, lambda: self._osd.show_rate(next_mode.rate_label, display.name))

    def _on_fs_change(self, path: str = "") -> None:
        if os.path.isdir(path):
            for entry in os.scandir(path):
                if entry.path not in self._watcher.files():
                    self._watcher.addPath(entry.path)
        self._debounce.start()

    def _poll_tick(self) -> None:
        displays, _ = query_displays()
        sig = [(d.name, d.current_mode_id, len(d.modes)) for d in displays]
        if sig != self._sig:
            self.rebuild_menu()

    def rebuild_menu(self) -> None:
        self.menu.clear()
        displays, error = query_displays()

        if error or not displays:
            a = QAction(error or "No displays found", self.menu)
            a.setEnabled(False)
            self.menu.addAction(a)
        else:
            self._sig = [(d.name, d.current_mode_id, len(d.modes)) for d in displays]
            for display in displays:
                self._build_display_menu(display)

        self.menu.addSeparator()
        quit_action = QAction("Quit", self.menu)
        quit_action.triggered.connect(self.app.quit)
        self.menu.addAction(quit_action)

    def _build_display_menu(self, display: Display) -> None:
        submenu = self.menu.addMenu(display.menu_label)
        group = QActionGroup(submenu)
        group.setExclusive(True)

        for mode in display.modes:
            action = QAction(mode.label, submenu)
            action.setCheckable(True)
            action.setChecked(mode.id == display.current_mode_id)
            action.triggered.connect(self._make_handler(display.name, mode, display.current_mode_id))
            group.addAction(action)
            submenu.addAction(action)

    def _make_handler(self, output_name: str, mode: Mode, current_mode_id: str):
        def handler(checked: bool) -> None:
            if checked and mode.id != current_mode_id:
                apply_mode(output_name, mode.id)
                QTimer.singleShot(self._APPLY_DELAY_MS, self.rebuild_menu)
                QTimer.singleShot(self._APPLY_DELAY_MS, lambda: self._osd.show_rate(mode.rate_label, output_name))
        return handler


def main() -> None:
    # Suppress harmless Wayland grab warning from StatusNotifier tray popups
    QLoggingCategory.setFilterRules("qt.qpa.wayland=false")

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Refresh Rate Switcher")
    signal.signal(signal.SIGINT, lambda *_: app.quit())

    if not QSystemTrayIcon.isSystemTrayAvailable():
        QMessageBox.critical(None, "Error", "No system tray detected.")
        sys.exit(1)

    _tray = RefreshRateTray(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
