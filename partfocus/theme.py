"""Farben und Qt-Stylesheet, übernommen aus ScoreCap (scorecap/theme.py).

Warmes Neutralgrau statt kaltem App-Grau, ein einziger Akzent im Ultramarin
von Urtext-Ausgaben.
"""
from dataclasses import asdict, dataclass

FONT_UI = '"Segoe UI Variable Text", "Segoe UI", sans-serif'
FONT_MONO = '"Cascadia Mono", Consolas, monospace'


@dataclass(frozen=True)
class Palette:
    app: str
    panel: str
    border: str
    border_strong: str
    text: str
    text_muted: str
    accent: str
    accent_hover: str
    accent_soft: str
    warn: str
    danger: str
    paper: str = "#FFFFFF"
    font_ui: str = FONT_UI
    font_mono: str = FONT_MONO


LIGHT = Palette(app="#F3F3F1", panel="#FAFAF8", border="#D9D8D4", border_strong="#BFBEB9",
                text="#1A1A19", text_muted="#6A6A66", accent="#23459B", accent_hover="#1B3780",
                accent_soft="#E4E9F6", warn="#8A6A12", danger="#9B2C22")
DARK = Palette(app="#1E1E1D", panel="#252523", border="#35342F", border_strong="#4A4842",
               text="#EAE9E6", text_muted="#9A9892", accent="#7E9BE6", accent_hover="#98AFEC",
               accent_soft="#26304A", warn="#D6B25E", danger="#E08376")


def system_prefers_dark() -> bool:
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QGuiApplication
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except Exception:
        return False


def palette() -> Palette:
    return DARK if system_prefers_dark() else LIGHT


def stylesheet(p: Palette) -> str:
    return _QSS.format(**asdict(p))


_QSS = """
QWidget {{ background: {app}; color: {text}; font-family: {font_ui}; font-size: 13px; }}
QLabel {{ background: transparent; }}
QLabel#Heading {{ font-size: 15px; font-weight: 600; }}
QLabel#Muted {{ color: {text_muted}; }}
QLabel#Numeric {{ font-family: {font_mono}; color: {text_muted}; min-width: 52px; }}
QLabel#EmptyState {{ color: {text_muted}; font-size: 14px; }}

QWidget#Toolbar {{ background: {panel}; border-bottom: 1px solid {border}; }}
QWidget#StatusBar {{ background: {panel}; border-top: 1px solid {border}; }}
QWidget#Options {{ background: {panel}; border-top: 1px solid {border}; }}

QPushButton {{
    background: transparent; border: 1px solid transparent; border-radius: 4px;
    padding: 6px 10px; color: {text};
}}
QPushButton:hover {{ background: {accent_soft}; }}
QPushButton:pressed {{ background: {accent_soft}; border-color: {border_strong}; }}
QPushButton:focus {{ border-color: {accent}; }}
QPushButton:disabled {{ color: {text_muted}; background: transparent; }}
QPushButton#Primary {{
    background: {accent}; color: {paper}; border: 1px solid {accent};
    padding: 7px 14px; font-weight: 600;
}}
QPushButton#Primary:hover {{ background: {accent_hover}; border-color: {accent_hover}; }}
QPushButton#Primary:disabled {{ background: transparent; color: {text_muted}; border: 1px solid {border}; }}
QPushButton#Quiet {{ border: 1px solid {border}; }}
QPushButton#Quiet:hover {{ border-color: {border_strong}; background: {accent_soft}; }}

QListWidget {{ background: {panel}; border: none; outline: none; }}
QListWidget::item {{ border-bottom: 1px solid {border}; padding: 6px 10px; }}
QListWidget::item:selected {{ background: {accent_soft}; color: {text}; }}

QComboBox {{
    background: {panel}; border: 1px solid {border_strong}; border-radius: 4px; padding: 4px 8px;
}}
QComboBox:focus {{ border-color: {accent}; }}
QLineEdit {{
    background: {panel}; border: 1px solid {border_strong}; border-radius: 4px; padding: 4px 8px;
}}
QLineEdit:focus {{ border-color: {accent}; }}
QComboBox QAbstractItemView {{
    background: {panel}; border: 1px solid {border_strong};
    selection-background-color: {accent_soft}; selection-color: {text};
}}

QSlider::groove:horizontal {{ height: 3px; background: {border_strong}; border-radius: 2px; }}
QSlider::handle:horizontal {{
    background: {accent}; width: 12px; height: 12px; margin: -5px 0; border-radius: 6px;
}}

QProgressBar {{
    background: {border}; border: none; border-radius: 2px; max-height: 4px; text-align: center;
}}
QProgressBar::chunk {{ background: {accent}; border-radius: 2px; }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 0; }}
QScrollBar::handle:vertical {{ background: {border_strong}; border-radius: 6px; min-height: 32px; }}
QScrollBar::handle:hover {{ background: {text_muted}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QToolTip {{ background: {panel}; color: {text}; border: 1px solid {border_strong}; padding: 4px 6px; }}
"""
