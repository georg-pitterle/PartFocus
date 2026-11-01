"""PartFocus-Oberfläche: Partituren wählen, Übe-Tracks rendern."""
import html
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSettings, QSize, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import (
    QAccessible, QAccessibleEvent, QColor, QDesktopServices, QFont, QIcon, QKeySequence, QPainter, QPen, QShortcut,
)
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QGridLayout, QHBoxLayout,
    QLabel, QLineEdit, QListView, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QSizePolicy,
    QSlider, QStackedWidget, QStyle, QStyledItemDelegate, QStyleOptionViewItem, QVBoxLayout, QWidget,
)

from . import core, theme
from ._version import __version__
from .updater import PendingUpdate, UpdateService, start_velopack

UPDATE_CHECK_DELAY_MS = 2000
CANCEL_LOCK_MS = 1000  # ein Doppelklick auf „Tracks erstellen“ darf nicht gleich abbrechen
PATH = Qt.UserRole
TRACKS = Qt.UserRole + 1  # 0 = Datei nicht lesbar
VOICES = Qt.UserRole + 2  # Namen der Hefte, beginnend mit „Gesamt“
QUALITIES = {192: "sehr gut, 1,4 MB/min", 128: "gut, 1 MB/min", 96: "mittel, 0,7 MB/min", 64: "einfach, 0,5 MB/min"}
BOOK = QSize(104, 128)
BOOK_GAP = 10
SAMPLE = ["Gesamt", "Sopran", "Alt", "Tenor", "Bass"]

DYNAMICS = [("Original behalten", None), ("überall pp", "pp"), ("überall p", "p"),
            ("überall mp", "mp"), ("überall mf", "mf"), ("überall f", "f")]
OTHERS_WORDS = [(-31, "sehr leise"), (-21, "leise"), (-13, "mittel"), (-5, "deutlich")]  # bis zu diesem dB-Wert


def named(text: str, widget: QWidget) -> QLabel:
    """Beschriftung mit Alt-Taste; Screenreader lesen sie als Namen des Feldes, den Tooltip als Beschreibung."""
    label = QLabel(text)
    label.setBuddy(widget)
    label.setToolTip(widget.toolTip())
    widget.setAccessibleName(text.replace("&", ""))
    widget.setAccessibleDescription(widget.toolTip().replace("\n", " "))
    return label


def set_kind(button: QPushButton, kind: str):
    """Knopfart wechseln; Qt wendet das Stylesheet erst nach einem neuen polish an."""
    if button.objectName() != kind:
        button.setObjectName(kind)
        button.style().unpolish(button)
        button.style().polish(button)


class Worker(QThread):
    progress = Signal(str, int, int)
    done = Signal(object)  # list[Result] oder Exception

    def __init__(self, scores: list[Path], opts: core.Options):
        super().__init__()
        self.scores, self.opts = scores, opts
        self.stop = threading.Event()

    def run(self):
        # debugpy verfolgt nur Threads aus dem threading-Modul; ohne das hält kein
        # Breakpoint in core.export, wenn aus VS Code gedebuggt wird.
        debugpy = sys.modules.get("debugpy")
        if debugpy is not None and debugpy.is_client_connected():
            debugpy.debug_this_thread()
        try:
            results = core.export(self.scores, self.opts, self.progress.emit, self.stop.is_set)
        except Exception as error:  # noqa: BLE001 - geht als Meldung ins Fenster
            results = error
        self.done.emit(results)


def cover(name: str, p: theme.Palette) -> str:
    """Einbandfarbe zum Stimmnamen: Stimmlagen wie bei Muse Choir, alles andere Ocker."""
    text = name.lower()
    if text == "gesamt":
        return p.gesamt
    if "solo" not in text:
        for (keys, _), colour in zip(core.CHOIR, (p.sopran, p.alt, p.tenor, p.bass)):
            if any(k in text for k in keys):
                return colour
    return p.solo


def title_font(base: QFont, size: int) -> QFont:
    font = QFont(base)
    font.setFamilies(["Bahnschrift", "Segoe UI"])
    font.setPixelSize(size)
    font.setWeight(QFont.DemiBold)
    return font


def draw_cover(painter: QPainter, box: QRect, name: str, p: theme.Palette, done: bool):
    colour = QColor(cover(name, p))
    painter.setPen(Qt.NoPen)
    painter.setBrush(colour)
    painter.drawRoundedRect(box.adjusted(0, 0, -1, -1), 2, 2)
    fold = QColor(p.label)
    fold.setAlpha(70)
    painter.setPen(QPen(fold, 1))
    painter.drawLine(box.left() + 8, box.top(), box.left() + 8, box.bottom())
    painter.setPen(QPen(QColor(p.label), 2))
    for y in (box.top() + box.height() // 4, box.bottom() - box.height() // 4):
        painter.drawLine(box.left() + 8, y - 5, box.left() + 8, y + 5)
    plate = book_plate(box)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor(p.label))
    painter.drawRect(plate)
    if done:
        x, y = box.right() - 18, box.bottom() - 13
        painter.setPen(QPen(QColor(p.label), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        painter.drawPolyline([QPoint(x, y), QPoint(x + 4, y + 4), QPoint(x + 11, y - 4)])
    draw_plate_text(painter, plate, name, p.label_text)


def book_plate(box: QRect) -> QRect:
    return QRect(box.left() + 14, box.top() + 34, box.width() - 24, 60)


def draw_plate_text(painter: QPainter, plate: QRect, name: str, colour: str):
    painter.setPen(QColor(colour))
    painter.setFont(title_font(painter.font(), 13))
    metrics = painter.fontMetrics()
    text = plate.adjusted(4, 3, -4, -3)
    # Drei Zeilen passen aufs Schild; lange zusammengesetzte Wörter brechen sonst an keiner Stelle um.
    wrap = Qt.TextWrapAnywhere if any(metrics.horizontalAdvance(w) > text.width() for w in name.split()) \
        else Qt.TextWordWrap
    painter.drawText(text, Qt.AlignCenter | wrap, metrics.elidedText(name, Qt.ElideRight, 3 * text.width() - 24))


def draw_book(painter: QPainter, box: QRect, name: str, p: theme.Palette, fill: float = 1.0, done: bool = False):
    """Ein Stimmenheft. Unter fill = 1 steht es als Umriss da und füllt sich von unten mit seinem Einband."""
    painter.save()
    painter.setRenderHint(QPainter.Antialiasing)
    if fill < 1:
        painter.setPen(QPen(QColor(cover(name, p)), 1.5, Qt.DashLine))
        painter.setBrush(Qt.NoBrush)
        painter.drawRoundedRect(box.adjusted(0, 0, -1, -1), 2, 2)
        draw_plate_text(painter, book_plate(box), name, p.text_muted)
    if fill > 0:
        height = round(box.height() * fill)
        painter.setClipRect(QRect(box.left(), box.bottom() + 1 - height, box.width(), height))
        draw_cover(painter, box, name, p, done)
    painter.restore()


def shelf_layout(width: int) -> int:
    """Wie viele Hefte in eine Reihe passen."""
    return max(1, (width + BOOK_GAP) // (BOOK.width() + BOOK_GAP))


class ScoreDelegate(QStyledItemDelegate):
    """Ein Stück als Regalreihe: Titel, Trackzahl, darunter ein Heft pro Track."""

    PAD_X, PAD_Y, HEAD = 18, 14, 54

    def __init__(self, window: "Window"):
        super().__init__(window.list)
        self.main = window

    def _books(self, index) -> list[str]:
        return index.data(VOICES) or []

    def paint(self, painter, option, index):
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.widget.style().drawPrimitive(QStyle.PE_PanelItemViewItem, opt, painter, opt.widget)
        p = theme.palette()
        title, _, detail = str(index.data()).partition("\n")
        books = self._books(index)
        box = option.rect.adjusted(self.PAD_X, self.PAD_Y, -self.PAD_X, -self.PAD_Y)
        painter.save()
        painter.setFont(title_font(option.font, 19))
        painter.setPen(QColor(p.text))
        painter.drawText(box, Qt.AlignLeft | Qt.AlignTop | Qt.TextSingleLine,
                         painter.fontMetrics().elidedText(title, Qt.ElideMiddle, box.width()))
        painter.setFont(option.font)
        painter.setPen(QColor(p.text_muted if index.data(TRACKS) else p.warn))
        line = self.main.track_line(index.row()) if books else detail
        painter.drawText(box.adjusted(0, 25, 0, 0), Qt.AlignLeft | Qt.AlignTop | Qt.TextSingleLine, line)
        per_row = shelf_layout(box.width())
        for i, name in enumerate(books):
            x = box.left() + (i % per_row) * (BOOK.width() + BOOK_GAP)
            y = box.top() + self.HEAD + (i // per_row) * (BOOK.height() + BOOK_GAP)
            draw_book(painter, QRect(x, y, BOOK.width(), BOOK.height()), name, p, self.main.book_fill(index.row(), i),
                      self.main.all_done)
        painter.restore()

    def sizeHint(self, option, index):
        width = option.widget.viewport().width()
        books = len(self._books(index))
        rows = -(-books // shelf_layout(width - 2 * self.PAD_X))
        shelf = rows * BOOK.height() + max(0, rows - 1) * BOOK_GAP
        return QSize(width, 2 * self.PAD_Y + self.HEAD + shelf)


class EmptyShelf(QWidget):
    """Leerer Zustand: sagt, was zu tun ist, und zeigt, was daraus wird."""

    TITLE = "Partituren (.mscz) oder einen Ordner hierher ziehen"
    TEXT = ("oder über „Dateien hinzufügen“ wählen.\n"
            "Für jede Stimme entsteht ein Track, dazu ein Gesamt-Track, in einem Ordner neben der Partitur.")

    def __init__(self):
        super().__init__()
        self.setAccessibleName("Noch keine Partituren")
        self.setAccessibleDescription(f"{self.TITLE} {self.TEXT}".replace("\n", " "))

    def paintEvent(self, event):
        p = theme.palette()
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(p.app))
        row = len(SAMPLE) * BOOK.width() + (len(SAMPLE) - 1) * BOOK_GAP
        top = max(16, (self.height() - 112 - BOOK.height()) // 2 - 16)
        painter.setPen(QColor(p.text))
        painter.setFont(title_font(self.font(), 22))
        painter.drawText(QRect(0, top, self.width(), 32), Qt.AlignHCenter | Qt.AlignTop, self.TITLE)
        painter.setFont(self.font())
        painter.drawText(QRect(0, top + 36, self.width(), 44), Qt.AlignHCenter | Qt.AlignTop, self.TEXT)
        painter.setPen(QColor(p.text_muted))
        painter.drawText(QRect(0, top + 92, self.width(), 20), Qt.AlignHCenter | Qt.AlignTop,
                         "Beispiel: Daraus werden fünf Tracks")
        for i, name in enumerate(SAMPLE):
            x = (self.width() - row) // 2 + i * (BOOK.width() + BOOK_GAP)
            draw_book(painter, QRect(x, top + 116, BOOK.width(), BOOK.height()), name, p, 0.0)


class PathsDialog(QDialog):
    """Wo MuseScore 4 und Muse Sounds liegen, falls nicht am Standardort."""

    def __init__(self, parent: QWidget, mscore: str, sampler: str):
        super().__init__(parent)
        self.setWindowTitle("Pfade")
        self.setMinimumWidth(560)
        form = QFormLayout(self)
        self.mscore = self._row(form, "MuseScore 4", mscore, lambda: QFileDialog.getOpenFileName(
            self, "MuseScore4.exe wählen", self.mscore.text(), "Programm (*.exe)")[0])
        self.sampler = self._row(form, "Muse Sounds", sampler, lambda: QFileDialog.getExistingDirectory(
            self, "MuseSampler-Ordner wählen", self.sampler.text()))
        form.addRow(QLabel("Muse Sounds: der Ordner „MuseSampler“, den Muse Hub anlegt (enthält lib\\).",
                           objectName="Muted", wordWrap=True))
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel
                                   | QDialogButtonBox.RestoreDefaults)
        buttons.button(QDialogButtonBox.Cancel).setText("Abbrechen")
        buttons.button(QDialogButtonBox.RestoreDefaults).setText("Standardpfade")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)
        form.addRow(buttons)

    def _row(self, form: QFormLayout, label: str, value: str, browse) -> QLineEdit:
        edit = QLineEdit(value)
        edit.setAccessibleName(label)
        pick = QPushButton("…", objectName="Quiet", clicked=lambda: edit.setText(browse() or edit.text()))
        pick.setAccessibleName(f"{label} wählen")
        row = QHBoxLayout()
        row.addWidget(edit, 1)
        row.addWidget(pick)
        form.addRow(label, row)
        return edit

    def restore_defaults(self):
        self.mscore.setText(core.MSCORE)
        self.sampler.setText(str(core.default_sampler()))


class Window(QWidget):
    # Vom Update-Thread gesendet; Qt stellt sie in den UI-Thread zu.
    update_ready = Signal(object)  # PendingUpdate, fertig geladen

    def __init__(self, updates: UpdateService | None = None):
        super().__init__()
        self.settings = QSettings("PartFocus", "PartFocus")
        self.updates = updates or UpdateService()
        self.ready_update: PendingUpdate | None = None
        self.update_ready.connect(self.on_update_ready)
        self.worker: Worker | None = None
        self.out_dirs: list[Path] = []
        self.finished = False  # letzter Lauf fertig, seitdem nichts geändert: Ordner öffnen ist der nächste Schritt
        self.cancel_locked = False
        self.notice = ""  # Hinweis in der Statuszeile, gilt bis zur nächsten Änderung
        self.progress: float | None = None  # Anteil fertiger Hefte während eines Laufs
        self.all_done = False  # Hefte tragen ein Häkchen, bis sich etwas ändert
        self.shown_row = -1  # beim Erstellen folgt das Regal dem Stück, das gerade entsteht
        self.setWindowTitle(f"PartFocus {__version__}")
        self.resize(1120, 700)
        self.setAcceptDrops(True)

        # Werkzeugleiste
        toolbar = QWidget(objectName="Toolbar")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(12, 8, 12, 8)
        heading = QLabel("PartFocus", objectName="Heading")
        self.files_btn = QPushButton("Dateien hinzufügen …", objectName="Quiet", clicked=self.add_files)
        self.files_btn.setToolTip("Strg+O")
        self.dir_btn = QPushButton("Ordner hinzufügen …", objectName="Quiet", clicked=self.add_dir)
        self.remove_btn = QPushButton("Entfernen", objectName="Quiet", clicked=self.remove_selected)
        self.remove_btn.setToolTip("Entf")
        self.paths_btn = QPushButton("Pfade …", objectName="Quiet", clicked=self.edit_paths)
        self.paths_btn.setToolTip("Wo MuseScore 4 und Muse Sounds installiert sind")
        tb.addWidget(heading)
        tb.addStretch()
        for b in (self.files_btn, self.dir_btn, self.remove_btn, self.paths_btn):
            tb.addWidget(b)

        # Liste bzw. Hinweis, solange sie leer ist
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.ExtendedSelection)
        self.list.setResizeMode(QListView.Adjust)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.setItemDelegate(ScoreDelegate(self))
        self.list.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.list.setAccessibleName("Partituren")
        self.list.itemSelectionChanged.connect(self.update_buttons)
        self.stack = QStackedWidget()
        self.stack.addWidget(EmptyShelf())
        self.stack.addWidget(self.list)

        # Einstellungen: drei Gruppen, rechts daneben die Aktionsspalte
        options = QWidget(objectName="Options")
        self.others = QSlider(Qt.Horizontal, minimum=-40, maximum=-5, singleStep=1, pageStep=5)
        self.others.setValue(int(self.settings.value("others_db", -25)))
        self.others.setMinimumWidth(160)
        self.others_label = QLabel(objectName="Muted")
        self.others_label.setMinimumWidth(62)
        self.dynamic = QComboBox()
        for label, level in DYNAMICS:
            self.dynamic.addItem(label, level)
        saved = self.settings.value("dynamic", "mf")
        self.dynamic.setCurrentIndex(max(0, self.dynamic.findData(None if saved == "" else saved)))
        self.dynamic.setToolTip("Dynamik einebnen, damit leise Stellen gut hörbar bleiben")
        self.sound = QComboBox()
        for key, label in core.SOUNDS.items():
            self.sound.addItem(label, key)
        self.sound.setCurrentIndex(max(0, self.sound.findData(self.settings.value("sound", "original"))))
        self.sound.setToolTip("Original: Klang aus der Partitur\n"
                              "Muse Choir: Chorstimme passend zum Stimmnamen, anderes bleibt original\n"
                              "Grand Piano: alle Stimmen als Flügel\n"
                              "Bei MIDI wählt das Abspielprogramm den Klang")
        self.unison = QCheckBox("&Unisono einfach")
        self.unison.setChecked(self.settings.value("merge_unison", "true") in (True, "true"))
        self.unison.setToolTip("Singen mehrere Stimmen denselben Ton, erklingt er nur einmal,\n"
                               "damit Unisono-Stellen nicht lauter werden")
        self.accompaniment = QCheckBox("&Begleitung")
        self.accompaniment.setChecked(self.settings.value("accompaniment", "true") in (True, "true"))
        self.accompaniment.setToolTip("Begleitung wie Klavier in jedem Track so laut wie die anderen Stimmen\n"
                                      "mitspielen, ohne Haken bleibt sie stumm; einen eigenen Track bekommt sie nicht")
        saved = {int(t) for t in str(self.settings.value("tempos", "100")).split(",") if t.strip().isdigit()}
        self.tempo_btns: dict[int, QPushButton] = {}
        chips = QGridLayout()
        chips.setSpacing(4)
        for t in core.TEMPOS:
            b = QPushButton(str(t), objectName="Chip", checkable=True)
            b.setAccessibleName(f"Tempo {t} Prozent")
            b.setToolTip("Eine Fassung pro gewähltem Tempo, in Prozent vom Original")
            b.setChecked(t in saved)
            b.toggled.connect(lambda on, b=b: self.tempo_toggled(b, on))
            self.tempo_btns[t] = b
            chips.addWidget(b, 0, len(self.tempo_btns) - 1)
        if not self.tempos():
            self.tempo_btns[100].setChecked(True)
        self.format = QComboBox()
        for key, label in core.FORMATS.items():
            self.format.addItem(label, key)
        self.format.setCurrentIndex(max(0, self.format.findData(self.settings.value("format", "mp3"))))
        self.format.setToolTip("MIDI braucht kaum Speicher; die anderen Stimmen werden über die\n"
                               "Anschlagstärke leiser, den Klang wählt das Abspielprogramm")
        self.bitrate = QComboBox()
        for kbps in core.BITRATES:
            self.bitrate.addItem(QUALITIES[kbps], kbps)
        self.bitrate.setCurrentIndex(max(0, self.bitrate.findData(int(self.settings.value("bitrate", 128)))))
        self.bitrate.setToolTip("Bitrate der MP3s: 192, 128, 96 oder 64 kbps\n"
                                "„einfach“ klingt etwas dumpfer, zum Üben reicht es")
        self.short_names = QCheckBox("Kurze Date&inamen")
        self.short_names.setChecked(self.settings.value("short_names", "false") in (True, "true"))
        self.short_names.setToolTip("„Lied - Bass1.mp3“ statt „Lied - Bass 1 (Muse Choir).mp3“.\n"
                                    "Das Tempo bleibt im Namen, damit sich Fassungen nicht überschreiben;\n"
                                    "ein Lauf mit anderem Klang ersetzt aber die Tracks des vorherigen")
        self.show_others(self.others.value())

        self.update_label = QLabel(objectName="UpdateNote")
        self.update_btn = QPushButton("Jetzt neu starten", clicked=self.restart_into_update)
        band = QWidget(objectName="UpdateBand")
        update = QHBoxLayout(band)
        update.setContentsMargins(18, 6, 18, 6)
        update.addWidget(self.update_label)
        update.addWidget(self.update_btn)
        update.addStretch()
        band.hide()
        self.update_band = band

        def group(title: str) -> QVBoxLayout:
            column = QVBoxLayout()
            column.setSpacing(8)
            column.addWidget(QLabel(title, objectName="Group"))
            return column

        def pair(left: QWidget, right: QWidget) -> QHBoxLayout:
            row = QHBoxLayout()
            row.setSpacing(12)
            row.addWidget(left)
            row.addWidget(right)
            return row

        def field(text: str, widget: QWidget) -> QWidget:
            box = QWidget(objectName="Field")
            column = QVBoxLayout(box)
            column.setContentsMargins(0, 0, 0, 0)
            column.setSpacing(3)
            column.addWidget(named(text, widget))
            column.addWidget(widget)
            return box

        sound = group("Stimmen")
        level = QHBoxLayout()
        level.setSpacing(10)
        level.addWidget(named("&Andere Stimmen", self.others))
        level.addWidget(self.others, 1)
        level.addWidget(self.others_label)
        sound.addLayout(level)
        sound.addLayout(pair(field("&Dynamik", self.dynamic), field("&Klang", self.sound)))
        checks = QHBoxLayout()
        checks.setSpacing(16)
        checks.addWidget(self.unison)
        checks.addWidget(self.accompaniment)
        checks.addStretch()
        sound.addLayout(checks)
        sound.addStretch()

        tempo = group("Tempo")
        tempo.addLayout(chips)
        hint = QLabel("&Eine Fassung pro Wert, in Prozent")
        hint.setBuddy(self.tempo_btns[100])
        tempo.addWidget(hint)
        tempo.addStretch()

        files = group("Dateien")
        files.addLayout(pair(field("&Format", self.format), field("&Qualität", self.bitrate)))
        files.addWidget(self.short_names)
        files.addStretch()

        self.bar = QProgressBar(textVisible=False)
        self.bar.setAccessibleName("Fortschritt")
        self.bar.hide()
        self.status = QLabel("", objectName="Muted", wordWrap=True)
        self.status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.status.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.open_btn = QPushButton("Ordner öffnen", objectName="Quiet", clicked=self.open_output)
        self.open_btn.hide()
        self.start_btn = QPushButton("Tracks erstellen", objectName="Primary", clicked=self.start_or_cancel)
        self.start_btn.setToolTip("Strg+Enter")
        column = QWidget(objectName="Field", fixedWidth=180, minimumHeight=127)  # feste Höhe: Das Papierfeld springt nicht
        action = QVBoxLayout(column)
        action.setContentsMargins(0, 0, 0, 0)
        action.setSpacing(6)
        action.addWidget(self.bar)
        action.addWidget(self.status, 1)
        action.addWidget(self.open_btn)
        action.addWidget(self.start_btn)

        rows = QHBoxLayout(options)
        rows.setContentsMargins(18, 12, 18, 14)
        rows.setSpacing(28)
        rows.addLayout(sound, 5)
        rows.addLayout(tempo, 4)
        rows.addLayout(files, 4)
        rows.addWidget(column)
        self.option_labels = options.findChildren(QLabel)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(toolbar)
        layout.addWidget(band)
        layout.addWidget(self.stack, 1)
        layout.addWidget(options)

        # Nur per Tab: Sonst sähe ein angeklickter Chip wie ein gewählter aus.
        for w in (*self.findChildren(QPushButton), *self.findChildren(QCheckBox), self.others):
            w.setFocusPolicy(Qt.TabFocus)
        order = (self.files_btn, self.dir_btn, self.remove_btn, self.paths_btn, self.list, self.others, self.dynamic,
                 self.sound, *self.tempo_btns.values(), self.unison, self.accompaniment, self.format, self.bitrate,
                 self.short_names, self.update_btn, self.open_btn, self.start_btn)
        for first, second in zip(order, order[1:]):
            QWidget.setTabOrder(first, second)
        for keys in ("Ctrl+Return", "Ctrl+Enter"):
            QShortcut(QKeySequence(keys), self, activated=self.start_btn.click)
        QShortcut(QKeySequence.Open, self, activated=self.files_btn.click)
        QShortcut(QKeySequence.Delete, self.list, context=Qt.WidgetShortcut, activated=self.remove_btn.click)

        self.others.valueChanged.connect(self.show_others)
        for signal in (self.others.valueChanged, self.dynamic.currentIndexChanged, self.sound.currentIndexChanged,
                       self.unison.toggled, self.accompaniment.toggled, self.format.currentIndexChanged,
                       self.bitrate.currentIndexChanged, self.short_names.toggled):
            signal.connect(lambda *_: self.changed())

        for path in self.settings.value("scores", []) or []:
            if Path(path).is_file():
                self.add_score(Path(path))
        self.update_buttons()
        QTimer.singleShot(UPDATE_CHECK_DELAY_MS, self.check_for_updates)

    # --- Updates ----------------------------------------------------------

    def check_for_updates(self):
        """Im Hintergrund suchen und laden; still, wenn nicht installiert oder offline."""
        if not self.updates.is_available():
            return  # aus dem Quellbaum gestartet

        def work():
            update = self.updates.check()
            if update is not None and self.updates.download(update):
                try:
                    self.update_ready.emit(update)
                except RuntimeError:
                    pass  # Fenster schon zu

        threading.Thread(target=work, daemon=True).start()

    def on_update_ready(self, update: PendingUpdate):
        self.ready_update = update
        self.update_label.setText(f"Version {update.version} ist bereit, sie wird beim Schließen installiert")
        self.update_btn.setToolTip(f"PartFocus sofort in Version {update.version} neu starten")
        self.update_band.show()
        self.update_buttons()

    def restart_into_update(self):
        if self.ready_update is None or self.worker:
            return
        self.save_settings()
        if not self.updates.restart_into(self.ready_update):
            self.update_label.setText("Neustart nicht möglich, das Update wird beim Schließen installiert")
            self.update_btn.hide()

    # --- Voraussetzungen --------------------------------------------------

    def mscore(self) -> str:
        return self.settings.value("mscore", "") or core.MSCORE

    def sampler(self) -> Path:
        return Path(self.settings.value("sampler", "") or core.default_sampler())

    def warn_missing_requirements(self):
        missing = core.missing_requirements(self.mscore(), self.sampler())
        if not missing:
            return
        accent = theme.palette().accent
        box = QMessageBox(QMessageBox.Warning, "Voraussetzungen fehlen",
                          "Für den Export fehlt:<br><br>" + "<br>".join(f"• {html.escape(m)}" for m in missing)
                          + f'<br><br>Herunterladen: <a style="color:{accent}" href="https://musescore.org">MuseScore'
                            f'</a> · <a style="color:{accent}" href="https://www.musehub.com">Muse Hub</a>',
                          QMessageBox.Ok, self)
        box.setTextFormat(Qt.RichText)
        box.setTextInteractionFlags(Qt.TextBrowserInteraction)
        paths = box.addButton("Pfade ändern …", QMessageBox.ActionRole)
        box.exec()
        if box.clickedButton() is paths:
            self.edit_paths()

    def edit_paths(self):
        dialog = PathsDialog(self, self.mscore(), str(self.sampler()))
        if dialog.exec() != QDialog.Accepted:
            return
        # Standardwerte leer speichern, damit sie einem geänderten Standard folgen.
        mscore, sampler = dialog.mscore.text().strip(), dialog.sampler.text().strip()
        self.settings.setValue("mscore", "" if mscore == core.MSCORE else mscore)
        self.settings.setValue("sampler", "" if Path(sampler) == core.default_sampler() else sampler)
        self.warn_missing_requirements()

    # --- Liste ------------------------------------------------------------

    def scores(self) -> list[Path]:
        return [self.list.item(i).data(PATH) for i in range(self.list.count())]

    def readable(self) -> list[QListWidgetItem]:
        return [self.list.item(i) for i in range(self.list.count()) if self.list.item(i).data(TRACKS)]

    def add_score(self, path: Path) -> bool:
        path = path.resolve()
        if path.suffix.lower() != ".mscz" or path in self.scores():
            return False
        tracks, books = 0, []
        try:
            books = [n for n, _ in core.voices(path)]
            names = books[1:]
            detail = f"{len(names)} {'Stimme' if len(names) == 1 else 'Stimmen'} plus Gesamt: " + ", ".join(names)
            tracks = len(books)
        except Exception:  # noqa: BLE001 - eine kaputte Datei darf die Liste nicht sprengen
            detail = "Lässt sich nicht öffnen und wird übersprungen"
        item = QListWidgetItem(f"{path.stem}\n{detail}")
        item.setData(PATH, path)
        item.setData(TRACKS, tracks)
        item.setData(VOICES, books)
        item.setToolTip(str(path))
        self.list.addItem(item)
        return True

    def add_paths(self, paths):
        skipped = 0
        for p in map(Path, paths):
            files = sorted(p.glob("*.mscz")) if p.is_dir() else [p]
            skipped += not files
            skipped += sum(not self.add_score(f) for f in files)
        self.changed(f"{skipped} übersprungen: keine .mscz oder schon in der Liste" if skipped else "")

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Partituren wählen", self.settings.value("dir", ""),
                                                "MuseScore (*.mscz)")
        if files:
            self.settings.setValue("dir", str(Path(files[0]).parent))
            self.add_paths(files)

    def add_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Ordner mit Partituren", self.settings.value("dir", ""))
        if d:
            self.settings.setValue("dir", d)
            self.add_paths([d])

    def remove_selected(self):
        for item in self.list.selectedItems():
            self.list.takeItem(self.list.row(item))
        self.changed()

    def show_dropping(self, on: bool):
        self.stack.setProperty("dropping", on)
        self.stack.style().unpolish(self.stack)
        self.stack.style().polish(self.stack)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and not self.worker:
            event.acceptProposedAction()
            self.show_dropping(True)

    def dragLeaveEvent(self, event):
        self.show_dropping(False)

    def dropEvent(self, event):
        self.show_dropping(False)
        self.add_paths(u.toLocalFile() for u in event.mimeData().urls())

    # --- Zustand ----------------------------------------------------------

    def keyPressEvent(self, event):
        # Außerhalb von Dialogen lösen Knöpfe in Qt nicht auf Enter aus.
        focused = self.focusWidget()
        if event.key() in (Qt.Key_Return, Qt.Key_Enter) and isinstance(focused, QPushButton):
            focused.click()
            return
        super().keyPressEvent(event)

    def show_others(self, value: int):
        word = next(w for limit, w in OTHERS_WORDS if value <= limit)
        self.others_label.setText(word)
        self.others.setToolTip(f"Wie viel leiser die anderen Stimmen im Track einer Stimme sind, zurzeit {value} dB")
        self.others.setAccessibleDescription(f"{word}, {value} dB")

    def tempos(self) -> tuple[int, ...]:
        return tuple(t for t, b in self.tempo_btns.items() if b.isChecked())

    def tempo_toggled(self, button: QPushButton, on: bool):
        if not on and not self.tempos():
            button.setChecked(True)  # mindestens ein Tempo
            return
        self.changed()

    def track_count(self, books: int) -> int:
        return books * len(self.tempos()) * (2 if self.format.currentData() == "both" else 1)

    def track_line(self, row: int) -> str:
        """Zeile unter dem Stücktitel: wie viele Tracks aus den Heften dieser Reihe werden."""
        books = self.list.item(row).data(TRACKS)
        tempos = len(self.tempos())
        return f"{self.track_count(books)} Tracks" + (f" in {tempos} Tempi" if tempos > 1 else "")

    def book_fill(self, row: int, book: int) -> float:
        """Beim Erstellen füllen sich die Hefte der Reihe nach, proportional zum Gesamtfortschritt."""
        if self.progress is None:
            return 1.0
        before = sum(self.list.item(r).data(TRACKS) for r in range(row))
        total = sum(item.data(TRACKS) for item in self.readable())
        return min(1.0, max(0.0, self.progress * total - before - book))

    def follow_progress(self):
        """Das Regal scrollt zum Stück, das gerade entsteht; dazwischen darf man selbst scrollen."""
        done = self.progress * sum(item.data(TRACKS) for item in self.readable())
        row = self.list.count() - 1
        for r in range(self.list.count()):
            done -= self.list.item(r).data(TRACKS)
            if done < 0:
                row = r
                break
        if row != self.shown_row:
            self.shown_row = row
            self.list.scrollToItem(self.list.item(row))

    def changed(self, notice: str = ""):
        """Liste oder Einstellung geändert: Das Ergebnis des letzten Laufs gilt nicht mehr."""
        self.finished = self.all_done = False
        self.notice = notice
        self.status.setText("")
        self.update_buttons()

    def count_text(self) -> str:
        unreadable = self.list.count() - len(self.readable())
        return " · ".join([f"{unreadable} nicht lesbar"] * bool(unreadable) + [self.notice] * bool(self.notice))

    def tracks_total(self) -> int:
        return self.track_count(sum(item.data(TRACKS) for item in self.readable()))

    def update_buttons(self):
        busy = self.worker is not None
        stopping = busy and self.worker.stop.is_set()
        self.stack.setCurrentIndex(1 if self.list.count() else 0)
        self.remove_btn.setEnabled(not busy and bool(self.list.selectedItems()))
        self.start_btn.setEnabled(not self.cancel_locked and not stopping if busy else bool(self.readable()))
        total = self.tracks_total()
        self.start_btn.setText("Abbrechen" if busy else f"{total} Tracks erstellen" if total else "Tracks erstellen")
        # Nur ein Hauptknopf im Fenster, und zwar der nächste sinnvolle Schritt.
        set_kind(self.start_btn, "Quiet" if busy or self.finished else "Primary")
        set_kind(self.open_btn, "Primary" if self.finished and not busy else "Quiet")
        for w in (self.others, self.dynamic, self.sound, self.unison, self.accompaniment, self.format, self.short_names,
                  self.paths_btn, self.files_btn, self.dir_btn, *self.tempo_btns.values()):
            w.setEnabled(not busy)
        # Scrollen bleibt möglich: Das Regal zeigt den Fortschritt.
        self.list.setSelectionMode(QListWidget.NoSelection if busy else QListWidget.ExtendedSelection)
        # MIDI hat keinen Klang, den spielt die Übe-App.
        self.sound.setEnabled(not busy and self.format.currentData() != "midi")
        self.bitrate.setEnabled(not busy and self.format.currentData() != "midi")
        for label in self.option_labels:
            label.setEnabled(label.buddy().isEnabled() if label.buddy() else not busy)
        # Kein Neustart mitten im Rendern: MuseScore liefe verwaist weiter.
        self.update_btn.setEnabled(not busy)
        if not busy and not self.status.text():
            self.status.setText(self.count_text())
        self.list.viewport().update()

    def save_settings(self):
        self.settings.setValue("others_db", self.others.value())
        self.settings.setValue("dynamic", self.dynamic.currentData() or "")
        self.settings.setValue("sound", self.sound.currentData())
        self.settings.setValue("merge_unison", self.unison.isChecked())
        self.settings.setValue("accompaniment", self.accompaniment.isChecked())
        self.settings.setValue("format", self.format.currentData())
        self.settings.setValue("bitrate", self.bitrate.currentData())
        self.settings.setValue("short_names", self.short_names.isChecked())
        self.settings.setValue("tempos", ",".join(map(str, self.tempos())))
        self.settings.setValue("scores", [str(s) for s in self.scores()])

    # --- Rendern ----------------------------------------------------------

    def confirm_replace(self, existing: list[Path]) -> bool:
        pieces = sorted({p.parent.name for p in existing})
        where = ", ".join(f"„{name}“" for name in pieces[:3]) + (f" und {len(pieces) - 3} weiteren" if pieces[3:] else "")
        count = "1 vorhandener Track" if len(existing) == 1 else f"{len(existing)} vorhandene Tracks"
        box = QMessageBox(QMessageBox.Question, "Vorhandene Tracks ersetzen?",
                          f"{count} aus {where} {'wird' if len(existing) == 1 else 'werden'} ersetzt.\n\n"
                          "Die alten Tracks bleiben erhalten, bis alle neuen fertig sind.",
                          QMessageBox.NoButton, self)
        replace = box.addButton("Ersetzen", QMessageBox.AcceptRole)
        box.setEscapeButton(box.addButton("Nicht starten", QMessageBox.RejectRole))
        box.setDefaultButton(replace)
        box.exec()
        return box.clickedButton() is replace

    def start_or_cancel(self):
        if self.worker:
            self.worker.stop.set()
            self.status.setText("Breche ab …")
            self.update_buttons()
            return
        if not Path(self.mscore()).is_file():
            QMessageBox.critical(self, "MuseScore fehlt",
                                 f"MuseScore nicht gefunden:\n{self.mscore()}\n\nPfad unter „Pfade …“ einstellen.")
            return
        self.save_settings()
        opts = core.Options(others_db=float(self.others.value()), flat_dynamic=self.dynamic.currentData(),
                                 sound=self.sound.currentData(), tempos=self.tempos(), mscore=self.mscore(),
                                 merge_unison=self.unison.isChecked(), format=self.format.currentData(),
                                 accompaniment=self.accompaniment.isChecked(), bitrate=self.bitrate.currentData(),
                                 short_names=self.short_names.isChecked())
        scores = [item.data(PATH) for item in self.readable()]
        existing = core.existing_outputs(scores, opts)
        if existing and not self.confirm_replace(existing):
            return
        self.finished = self.all_done = False
        self.list.clearSelection()
        self.shown_row = -1
        self.worker = Worker(scores, opts)
        self.worker.progress.connect(self.on_progress)
        self.worker.done.connect(self.on_done)
        self.bar.setRange(0, 0)
        self.bar.show()
        self.progress = 0.0
        self.open_btn.hide()
        self.status.setText("Starte MuseScore …")
        self.worker.start()
        self.cancel_locked = True
        QTimer.singleShot(CANCEL_LOCK_MS, self.unlock_cancel)
        self.update_buttons()

    def unlock_cancel(self):
        self.cancel_locked = False
        self.update_buttons()

    def on_progress(self, text: str, done: int, total: int):
        self.bar.setRange(0, total)
        self.bar.setValue(done)
        self.progress = done / total if total else 0.0
        self.follow_progress()
        self.list.viewport().update()
        self.status.setText(f"{text} … {done}/{total}")

    def on_done(self, results):
        self.worker.wait()
        self.worker = None
        self.progress = None
        self.bar.hide()
        QApplication.alert(self)  # Rendern dauert: Taskleiste blinkt, wenn das Fenster im Hintergrund liegt
        if isinstance(results, core.Cancelled):
            self.status.setText("Abgebrochen. Vorhandene Tracks sind unverändert.")
        elif isinstance(results, PermissionError):
            name = Path(results.filename or "").name
            self.status.setText("Nicht ersetzt. Vorhandene Tracks sind unverändert.")
            QMessageBox.critical(self, "Tracks nicht ersetzt",
                                 f"„{name}“ ist noch in einem anderen Programm geöffnet.\n\n"
                                 "Schließe es und erstelle die Tracks noch einmal.")
        elif isinstance(results, Exception):
            self.status.setText("Fehlgeschlagen. Vorhandene Tracks sind unverändert.")
            QMessageBox.critical(self, "Tracks nicht erstellt",
                                 f"{results}\n\nPrüfe, ob sich die Partitur in MuseScore öffnen lässt, "
                                 "und versuche es noch einmal.")
        else:
            bad = [r for r in results if not r.ok]
            self.out_dirs = [r.out.parent for r in results]
            self.finished = True
            self.all_done = not bad
            self.status.setText(core.summary(results) + (f" {len(bad)} prüfen." if bad else ""))
            self.open_btn.show()
            if bad:
                names = [r.out.name for r in bad[:12]] + [f"und {len(bad) - 12} weitere"] * (len(bad) > 12)
                QMessageBox.warning(self, "Bitte prüfen", "Diese Tracks sind fast stumm oder fehlen:\n\n"
                                    + "\n".join(names))
        QAccessible.updateAccessibility(QAccessibleEvent(self.status, QAccessible.Event.Alert))
        self.update_buttons()

    def open_output(self):
        for folder in core.folders_to_open(self.out_dirs):
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))

    def confirm_close(self) -> bool:
        box = QMessageBox(QMessageBox.Question, "Tracks werden noch erstellt",
                          "Beim Schließen wird der Lauf abgebrochen. Vorhandene Tracks bleiben unverändert.",
                          QMessageBox.NoButton, self)
        stop = box.addButton("Abbrechen und schließen", QMessageBox.AcceptRole)
        keep = box.addButton("Weiter erstellen", QMessageBox.RejectRole)
        box.setDefaultButton(keep)
        box.setEscapeButton(keep)
        box.exec()
        return box.clickedButton() is stop

    def closeEvent(self, event):
        if self.worker:
            if not self.confirm_close():
                event.ignore()
                return
            self.worker.stop.set()
            self.worker.wait()
        self.save_settings()
        if self.ready_update is not None:
            self.updates.install_on_exit(self.ready_update)
        super().closeEvent(event)


def icon_path() -> Path:
    """Icon im Quellbaum und im PyInstaller-Bundle gleichermaßen finden."""
    bundled = Path(getattr(sys, "_MEIPASS", "")) / "assets" / "partfocus.ico"
    if bundled.is_file():
        return bundled
    return Path(__file__).resolve().parent.parent / "assets" / "partfocus.ico"


def selftest(report: Path) -> int:
    """Beweist, dass ein gebautes Bundle wirklich läuft; Bericht als Datei, weil die exe kein Terminal hat."""
    import os
    import traceback

    lines = [f"PartFocus {__version__}"]
    try:
        flat = core.flatten_dynamics("<Dynamic><subtype>pp</subtype><velocity>33</velocity></Dynamic>", "mf")
        if "<subtype>mf</subtype>" not in flat or "<velocity>80</velocity>" not in flat:
            raise RuntimeError(f"flatten_dynamics kaputt: {flat}")
        lines.append("core: ok")
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        app = QApplication.instance() or QApplication(sys.argv[:1])
        app.setStyleSheet(theme.stylesheet(theme.LIGHT))
        Window().close()
        lines.append(f"qt: Fenster gebaut, Icon {'da' if icon_path().is_file() else 'FEHLT'}")
        if not icon_path().is_file():
            raise RuntimeError("Icon fehlt im Bundle")
        if not (theme.controls_dir() / "chevron.png").is_file():
            raise RuntimeError("Bilder für Bedienelemente fehlen im Bundle")
        import velopack  # noqa: F401 - fehlt es im Bundle, gibt es nie Updates

        lines.append(f"velopack: installiert={UpdateService().is_available()}")
        lines.append("RESULT: ok")
        code = 0
    except Exception as error:  # noqa: BLE001 - der Bericht ist der Fehlerkanal
        lines += [f"RESULT: failed: {error!r}", traceback.format_exc()]
        code = 1
    try:
        report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    except OSError:
        pass
    return code


def main():
    if "--selftest" in sys.argv:
        i = sys.argv.index("--selftest")
        return selftest(Path(sys.argv[i + 1] if len(sys.argv) > i + 1 else "selftest.txt"))
    start_velopack()
    app = QApplication(sys.argv)
    app.setApplicationName("PartFocus")
    app.setApplicationVersion(__version__)
    if icon_path().is_file():
        app.setWindowIcon(QIcon(str(icon_path())))
    app.setStyleSheet(theme.stylesheet(theme.palette()))
    app.styleHints().colorSchemeChanged.connect(lambda: app.setStyleSheet(theme.stylesheet(theme.palette())))
    window = Window()
    window.add_paths(sys.argv[1:])
    window.show()
    QTimer.singleShot(0, window.warn_missing_requirements)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
