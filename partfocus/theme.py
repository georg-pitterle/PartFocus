"""Farben und Qt-Stylesheet: Stimmenhefte auf einem Kartontisch.

Jede Stimmlage hat ihren Einband, Ochsenblut trägt Kopfband und Hauptaktion.
Die Hefte zeichnet gui.ScoreDelegate, alles andere dieses Stylesheet.
"""
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

FONT_UI = '"Segoe UI Variable Text", "Segoe UI", sans-serif'
FONT_TITLE = 'Bahnschrift, "Segoe UI", sans-serif'


@dataclass(frozen=True)
class Palette:
    app: str  # Tisch, darauf liegen die Hefte
    panel: str  # Papierfeld mit den Einstellungen
    head: str  # Kopfband
    head_hover: str
    head_text: str
    head_muted: str
    border: str
    border_strong: str
    control: str  # Umriss von Bedienelementen, auf beiden Flächen mindestens 3:1
    text: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_soft: str
    on_accent: str
    warn: str
    danger: str
    label: str  # Titelschild der Hefte, in beiden Modi hell
    label_text: str
    gesamt: str  # Einbände
    sopran: str
    alt: str
    tenor: str
    bass: str
    solo: str
    check: str  # Häkchen in on_accent, Datei aus assets/controls
    font_ui: str = FONT_UI
    font_title: str = FONT_TITLE


LIGHT = Palette(app="#E7DFC9", panel="#F4EFE0", head="#7A1F2B", head_hover="#8F2D3A", head_text="#FFFFFF",
                head_muted="#E2C4C4", border="#CFC5AC", border_strong="#B8AD92", control="#756B58",
                text="#26211A", text_muted="#5A5142", accent="#7A1F2B", accent_hover="#641722",
                accent_soft="#EFD9D0", on_accent="#FFFFFF", warn="#7A5608", danger="#9B2C22",
                label="#F4EFE0", label_text="#26211A", gesamt="#26211A", sopran="#7A1F2B", alt="#2F6B4F",
                tenor="#1F4E79", bass="#463A73", solo="#94671C", check="check-light")
DARK = Palette(app="#231F1A", panel="#2E2922", head="#5E1722", head_hover="#74232F", head_text="#FFFFFF",
               head_muted="#D9BDBD", border="#453E33", border_strong="#5C5345", control="#83796A",
               text="#EFE8D8", text_muted="#B5AB99", accent="#D06A74", accent_hover="#DC858D",
               accent_soft="#4A2A2C", on_accent="#231F1A", warn="#E0B861", danger="#E08376",
               label="#F4EFE0", label_text="#26211A", gesamt="#8F8572", sopran="#B4505C", alt="#44916F",
               tenor="#4A86BC", bass="#7C70B8", solo="#A87B2A", check="check-dark")


def system_prefers_dark() -> bool:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False


def palette() -> Palette:
    return DARK if system_prefers_dark() else LIGHT


def controls_dir() -> Path:
    """Häkchen und Pfeil im Quellbaum und im PyInstaller-Bundle gleichermaßen finden."""
    bundled = Path(getattr(sys, "_MEIPASS", "")) / "assets" / "controls"
    return bundled if bundled.is_dir() else Path(__file__).resolve().parent.parent / "assets" / "controls"


def stylesheet(p: Palette) -> str:
    return _QSS.format(**asdict(p), controls=controls_dir().as_posix())


_QSS = """
QWidget {{ background: {app}; color: {text}; font-family: {font_ui}; font-size: 13px; }}
QLabel {{ background: transparent; }}
QLabel:disabled {{ color: {text_muted}; }}
QLabel#Muted {{ color: {text_muted}; }}
QLabel#Group {{ font-weight: 700; }}
QWidget#Field {{ background: transparent; }}

QWidget#Toolbar {{ background: {head}; }}
QWidget#UpdateBand {{ background: {head}; border-top: 1px solid {head_hover}; }}
QLabel#Heading {{ color: {head_text}; font-family: {font_title}; font-size: 20px; font-weight: 600; }}
QLabel#UpdateNote {{ color: {head_text}; }}
QWidget#Options {{ background: {panel}; border-top: 1px solid {border_strong}; }}

QStackedWidget {{ background: {app}; border: 2px solid transparent; }}
QStackedWidget[dropping="true"] {{ border-color: {accent}; }}

QPushButton {{
    background: transparent; border: 1px solid {control}; border-radius: 4px;
    padding: 6px 10px; color: {text}; outline: none;
}}
QPushButton:hover {{ background: {accent_soft}; }}
QPushButton:pressed {{ background: {accent_soft}; border-color: {border_strong}; }}
QPushButton:focus {{ border: 2px solid {accent}; padding: 5px 9px; }}
QPushButton:default {{ border: 2px solid {accent}; padding: 5px 9px; font-weight: 600; }}
QPushButton:disabled {{ color: {text_muted}; background: transparent; border-color: {border_strong}; }}
QPushButton#Primary {{
    background: {accent}; color: {on_accent}; border: 1px solid {accent};
    padding: 12px 16px; font-family: {font_title}; font-size: 16px; font-weight: 600;
}}
QPushButton#Primary:hover {{ background: {accent_hover}; border-color: {accent_hover}; }}
QPushButton#Primary:focus {{ border: 2px solid {text}; padding: 11px 15px; }}
QPushButton#Primary:disabled {{ background: transparent; color: {text_muted}; border: 1px solid {border_strong}; }}
QPushButton#Quiet {{ border: 1px solid {control}; }}
QPushButton#Quiet:hover {{ background: {accent_soft}; }}
QPushButton#Quiet:focus {{ border: 2px solid {accent}; padding: 5px 9px; }}
QPushButton#Quiet:disabled {{ border-color: {border_strong}; }}
QPushButton#Chip {{ background: {panel}; border: 1px solid {control}; padding: 4px 0; font-family: {font_title}; }}
QPushButton#Chip:hover {{ background: {accent_soft}; }}
QPushButton#Chip:checked {{ background: {accent}; border-color: {accent}; color: {on_accent}; }}
QPushButton#Chip:focus {{ border: 2px solid {text}; padding: 3px 0; }}
QPushButton#Chip:disabled {{ background: transparent; border-color: {border_strong}; color: {text_muted}; }}
QPushButton#Chip:checked:disabled {{ background: {border_strong}; color: {text}; }}

QWidget#Toolbar QPushButton, QWidget#UpdateBand QPushButton {{
    background: transparent; color: {head_text}; border: 1px solid {head_muted};
}}
QWidget#Toolbar QPushButton:hover, QWidget#UpdateBand QPushButton:hover {{ background: {head_hover}; }}
QWidget#Toolbar QPushButton:focus, QWidget#UpdateBand QPushButton:focus {{
    border: 2px solid {head_text}; padding: 5px 9px;
}}
QWidget#Toolbar QPushButton:disabled, QWidget#UpdateBand QPushButton:disabled {{
    color: {head_muted}; border-color: {head_hover};
}}

QCheckBox {{ background: transparent; spacing: 6px; }}
QCheckBox:disabled {{ color: {text_muted}; }}
QCheckBox::indicator {{
    width: 14px; height: 14px; background: {panel}; border: 1px solid {control}; border-radius: 2px;
}}
QCheckBox::indicator:checked {{
    background: {accent}; border-color: {accent}; image: url("{controls}/{check}.png");
}}
QCheckBox::indicator:focus {{ width: 12px; height: 12px; border: 2px solid {accent}; }}
QCheckBox::indicator:checked:focus {{ border-color: {text}; }}
QCheckBox::indicator:disabled {{ background: transparent; border-color: {border_strong}; }}
QCheckBox::indicator:checked:disabled {{ background: {border_strong}; border-color: {border_strong}; }}

QListWidget {{ background: {app}; border: 2px solid transparent; outline: none; }}
QListWidget:focus {{ border-color: {accent}; }}
QListWidget::item {{ border-bottom: 1px solid {border_strong}; }}
QListWidget::item:selected {{ background: {accent_soft}; color: {text}; }}
QListWidget::item:focus {{ border-bottom: 2px solid {accent}; }}

QComboBox {{
    background: {panel}; border: 1px solid {control}; border-radius: 4px; padding: 4px 8px;
}}
QComboBox:focus {{ border: 2px solid {accent}; padding: 3px 7px; }}
QComboBox:disabled {{ background: transparent; color: {text_muted}; border-color: {border_strong}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox::down-arrow {{ image: url("{controls}/chevron.png"); width: 10px; height: 10px; }}
QLineEdit {{
    background: {panel}; border: 1px solid {control}; border-radius: 4px; padding: 4px 8px;
    selection-background-color: {accent}; selection-color: {on_accent};
}}
QLineEdit:focus {{ border: 2px solid {accent}; padding: 3px 7px; }}
QComboBox QAbstractItemView {{
    background: {panel}; border: 1px solid {control};
    selection-background-color: {accent_soft}; selection-color: {text};
}}

QSlider {{ background: transparent; }}
QSlider::groove:horizontal {{ height: 3px; background: {control}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {accent}; width: 14px; height: 14px; margin: -6px 0; border-radius: 7px;
}}
QSlider::handle:horizontal:focus {{
    border: 2px solid {text}; width: 10px; height: 10px; margin: -6px 0; border-radius: 7px;
}}
QSlider::handle:horizontal:disabled {{ background: {border_strong}; }}
QSlider::groove:horizontal:disabled {{ background: {border_strong}; }}

QProgressBar {{
    background: {border}; border: none; border-radius: 2px; max-height: 4px; text-align: center;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 2px; }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {control}; border-radius: 6px; min-height: 32px; }}
QScrollBar::handle:hover {{ background: {text_muted}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QToolTip {{ background: {panel}; color: {text}; border: 1px solid {control}; padding: 4px 6px; }}
"""
