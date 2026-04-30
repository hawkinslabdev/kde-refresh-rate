#!/usr/bin/env python3

import json
import locale
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

# ── i18n ──────────────────────────────────────────────────────────────────────

_TRANSLATIONS: dict[str, dict[str, str]] = {
    "nl": {
        "Refresh Rate Switcher":   "Refresh Rate Switcher",
        "Screen":                  "Scherm",
        "Main":                    "Hoofd",
        "No displays found":       "Geen beeldschermen gevonden",
        "kscreen-doctor not found — install: sudo dnf install kscreen":
            "kscreen-doctor niet gevonden — installeer: sudo dnf install kscreen",
        "Failed to parse kscreen-doctor output":
            "Kan kscreen-doctor-uitvoer niet verwerken",
        "kscreen-doctor timed out":    "kscreen-doctor time-out",
        "kscreen-doctor error":        "kscreen-doctor fout",
        "No system tray detected.":    "Geen systeemvak gevonden.",
        "Error":                       "Fout",
        "Quit":                        "Afsluiten",
        "Exit the refresh rate switcher": "Ververssnelheid Switcher afsluiten",
        "Primary display":             "Primair beeldscherm",
        "Secondary display":           "Secundair beeldscherm",
        "Current: {desc}":             "Huidig: {desc}",
        "{width}×{height} at {rate} Hz": "{width}×{height} bij {rate} Hz",
        "unknown":                     "onbekend",
    },
    "de": {
        "Refresh Rate Switcher":   "Bildwiederholrate-Umschalter",
        "Screen":                  "Bildschirm",
        "Main":                    "Haupt",
        "No displays found":       "Keine Bildschirme gefunden",
        "kscreen-doctor not found — install: sudo dnf install kscreen":
            "kscreen-doctor nicht gefunden — installieren: sudo dnf install kscreen",
        "Failed to parse kscreen-doctor output":
            "kscreen-doctor-Ausgabe konnte nicht verarbeitet werden",
        "kscreen-doctor timed out":    "kscreen-doctor-Zeitüberschreitung",
        "kscreen-doctor error":        "kscreen-doctor-Fehler",
        "No system tray detected.":    "Kein Systembereich gefunden.",
        "Error":                       "Fehler",
        "Quit":                        "Beenden",
        "Exit the refresh rate switcher": "Bildwiederholrate-Umschalter beenden",
        "Primary display":             "Primärer Bildschirm",
        "Secondary display":           "Sekundärer Bildschirm",
        "Current: {desc}":             "Aktuell: {desc}",
        "{width}×{height} at {rate} Hz": "{width}×{height} bei {rate} Hz",
        "unknown":                     "unbekannt",
    },
    "it": {
        "Refresh Rate Switcher":   "Cambio frequenza di aggiornamento",
        "Screen":                  "Schermo",
        "Main":                    "Principale",
        "No displays found":       "Nessun display trovato",
        "kscreen-doctor not found — install: sudo dnf install kscreen":
            "kscreen-doctor non trovato — installa: sudo dnf install kscreen",
        "Failed to parse kscreen-doctor output":
            "Impossibile analizzare l'output di kscreen-doctor",
        "kscreen-doctor timed out":    "kscreen-doctor: timeout",
        "kscreen-doctor error":        "Errore kscreen-doctor",
        "No system tray detected.":    "Nessun vassoio di sistema rilevato.",
        "Error":                       "Errore",
        "Quit":                        "Esci",
        "Exit the refresh rate switcher": "Esci dal cambio frequenza di aggiornamento",
        "Primary display":             "Display principale",
        "Secondary display":           "Display secondario",
        "Current: {desc}":             "Corrente: {desc}",
        "{width}×{height} at {rate} Hz": "{width}×{height} a {rate} Hz",
        "unknown":                     "sconosciuto",
    },
    "pl": {
        "Refresh Rate Switcher":   "Refresh Rate Switcher",
        "Screen":                  "Ekran",
        "Main":                    "Główny",
        "No displays found":       "Nie znaleziono wyświetlaczy",
        "kscreen-doctor not found — install: sudo dnf install kscreen":
            "Nie znaleziono kscreen-doctor — zainstaluj: sudo dnf install kscreen",
        "Failed to parse kscreen-doctor output":
            "Nie udało się przetworzyć danych kscreen-doctor",
        "kscreen-doctor timed out":    "Przekroczono czas oczekiwania kscreen-doctor",
        "kscreen-doctor error":        "Błąd kscreen-doctor",
        "No system tray detected.":    "Nie wykryto zasobnika systemowego.",
        "Error":                       "Błąd",
        "Quit":                        "Wyjdź",
        "Exit the refresh rate switcher": "Zamknij przełącznik częstotliwości odświeżania",
        "Primary display":             "Główny wyświetlacz",
        "Secondary display":           "Dodatkowy wyświetlacz",
        "Current: {desc}":             "Bieżący: {desc}",
        "{width}×{height} at {rate} Hz": "{width}×{height} przy {rate} Hz",
        "unknown":                     "nieznany",
    },
    "es": {
        "Refresh Rate Switcher":   "Refresh Rate Switcher",
        "Screen":                  "Pantalla",
        "Main":                    "Principal",
        "No displays found":       "No se encontraron pantallas",
        "kscreen-doctor not found — install: sudo dnf install kscreen":
            "kscreen-doctor no encontrado — instala: sudo dnf install kscreen",
        "Failed to parse kscreen-doctor output":
            "Error al analizar la salida de kscreen-doctor",
        "kscreen-doctor timed out":    "kscreen-doctor agotó el tiempo de espera",
        "kscreen-doctor error":        "error de kscreen-doctor",
        "No system tray detected.":    "No se detectó bandeja del sistema.",
        "Error":                       "Error",
        "Quit":                        "Salir",
        "Exit the refresh rate switcher": "Salir del conmutador de frecuencia de actualización",
        "Primary display":             "Pantalla principal",
        "Secondary display":           "Pantalla secundaria",
        "Current: {desc}":             "Actual: {desc}",
        "{width}×{height} at {rate} Hz": "{width}×{height} a {rate} Hz",
        "unknown":                     "desconocido",
    },
}


def _make_translator() -> dict[str, str]:
    try:
        lang = (
            locale.getlocale()[0]
            or os.environ.get("LANG", "")
            or os.environ.get("LANGUAGE", "")
        )
        code = lang.split("_")[0].split(".")[0].lower()
        return _TRANSLATIONS.get(code, {})
    except Exception:
        return {}


_T: dict[str, str] = _make_translator()


def _(text: str) -> str:
    return _T.get(text, text)

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
        suffix = f"  [{_('Main')}]    " if self.is_main else ""
        return f"{_('Screen')} {self.index}: {self.name}{suffix}"


def query_displays() -> tuple[list[Display], Optional[str]]:
    try:
        result = subprocess.run(
            ["kscreen-doctor", "--json"],
            capture_output=True, text=True, timeout=5,
        )
        if result.returncode != 0:
            return [], result.stderr.strip() or _("kscreen-doctor error")

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
        return [], _("kscreen-doctor not found — install: sudo dnf install kscreen")
    except json.JSONDecodeError:
        return [], _("Failed to parse kscreen-doctor output")
    except subprocess.TimeoutExpired:
        return [], _("kscreen-doctor timed out")
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

        self.menu = QMenu()
        self.menu.setStyleSheet("QMenu::item { padding-right: 28px; }")
        self.menu.setToolTipsVisible(True)

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self._find_icon())
        self.tray.setToolTip(_("Refresh Rate Switcher"))
        self.tray.setContextMenu(self.menu)
        self.tray.activated.connect(self._on_activated)

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
            msg = error or _("No displays found")
            a = QAction(msg, self.menu)
            a.setEnabled(False)
            self.menu.addAction(a)
            self.tray.setToolTip(_("Refresh Rate Switcher") + "\n" + msg)
        else:
            self._sig = [(d.name, d.current_mode_id, len(d.modes)) for d in displays]
            subtext_lines = []
            for display in displays:
                self._build_display_menu(display)
                current = next((m for m in display.modes if m.id == display.current_mode_id), None)
                if current:
                    subtext_lines.append(f"{display.name}: {current.label}")
            tooltip = _("Refresh Rate Switcher")
            if subtext_lines:
                tooltip += "\n" + " · ".join(subtext_lines)
            self.tray.setToolTip(tooltip)

        self.menu.addSeparator()
        quit_action = QAction(_("Quit"), self.menu)
        quit_action.setToolTip(_("Exit the refresh rate switcher"))
        quit_action.triggered.connect(self.app.quit)
        self.menu.addAction(quit_action)

    def _build_display_menu(self, display: Display) -> None:
        submenu = self.menu.addMenu(display.menu_label)
        submenu.setToolTipsVisible(True)

        current_mode = next((m for m in display.modes if m.id == display.current_mode_id), None)
        current_desc = current_mode.label if current_mode else _("unknown")
        role = _("Primary display") if display.is_main else _("Secondary display")
        submenu.menuAction().setToolTip(
            f"{role}: {display.name}\n" + _("Current: {desc}").format(desc=current_desc)
        )

        group = QActionGroup(submenu)
        group.setExclusive(True)

        for mode in display.modes:
            action = QAction(mode.label, submenu)
            action.setCheckable(True)
            action.setChecked(mode.id == display.current_mode_id)
            exact_rate = f"{mode.refresh_rate:.4f}".rstrip("0").rstrip(".")
            action.setToolTip(
                _("{width}×{height} at {rate} Hz").format(
                    width=mode.width, height=mode.height, rate=exact_rate,
                )
            )
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
        QMessageBox.critical(None, _("Error"), _("No system tray detected."))
        sys.exit(1)

    _tray = RefreshRateTray(app)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
