"""PartFocus-Oberfläche: Partituren wählen, Übe-Tracks rendern."""
import sys
import threading
from pathlib import Path

from PySide6.QtCore import QSettings, Qt, QThread, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QIcon
from PySide6.QtWidgets import (
    QApplication, QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QProgressBar, QPushButton, QSlider,
    QStackedWidget, QVBoxLayout, QWidget,
)

from . import core, theme
from ._version import __version__
from .updater import PendingUpdate, UpdateService, start_velopack

UPDATE_CHECK_DELAY_MS = 2000

DYNAMICS = [("Original behalten", None), ("überall pp", "pp"), ("überall p", "p"),
            ("überall mp", "mp"), ("überall mf", "mf"), ("überall f", "f")]


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
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.RestoreDefaults).clicked.connect(self.restore_defaults)
        form.addRow(buttons)

    def _row(self, form: QFormLayout, label: str, value: str, browse) -> QLineEdit:
        edit = QLineEdit(value)
        pick = QPushButton("…", objectName="Quiet", clicked=lambda: edit.setText(browse() or edit.text()))
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
        self.last_out: Path | None = None
        self.setWindowTitle(f"PartFocus {__version__}")
        self.resize(760, 560)
        self.setAcceptDrops(True)

        # Werkzeugleiste
        toolbar = QWidget(objectName="Toolbar")
        tb = QHBoxLayout(toolbar)
        tb.setContentsMargins(12, 8, 12, 8)
        heading = QLabel("Partituren", objectName="Heading")
        add_files = QPushButton("Dateien hinzufügen …", objectName="Quiet", clicked=self.add_files)
        add_dir = QPushButton("Ordner hinzufügen …", objectName="Quiet", clicked=self.add_dir)
        self.remove_btn = QPushButton("Entfernen", clicked=self.remove_selected)
        self.paths_btn = QPushButton("Pfade …", objectName="Quiet", clicked=self.edit_paths)
        self.paths_btn.setToolTip("Wo MuseScore 4 und Muse Sounds installiert sind")
        self.update_label = QLabel(objectName="Muted")
        self.update_btn = QPushButton("Jetzt neu starten", objectName="Quiet", clicked=self.restart_into_update)
        self.update_label.hide()
        self.update_btn.hide()
        tb.addWidget(heading)
        tb.addSpacing(12)
        tb.addWidget(self.update_label)
        tb.addWidget(self.update_btn)
        tb.addStretch()
        for b in (add_files, add_dir, self.remove_btn, self.paths_btn):
            tb.addWidget(b)

        # Liste bzw. Hinweis, solange sie leer ist
        self.list = QListWidget()
        self.list.setSelectionMode(QListWidget.ExtendedSelection)
        self.list.setWordWrap(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.list.itemSelectionChanged.connect(self.update_buttons)
        empty = QLabel("Partituren (.mscz) hierher ziehen\noder über „Dateien hinzufügen“ wählen.",
                       objectName="EmptyState", alignment=Qt.AlignCenter)
        self.stack = QStackedWidget()
        self.stack.addWidget(empty)
        self.stack.addWidget(self.list)

        # Einstellungen
        options = QWidget(objectName="Options")
        op = QHBoxLayout(options)
        op.setContentsMargins(12, 10, 12, 10)
        op.setSpacing(10)
        self.others = QSlider(Qt.Horizontal, minimum=-40, maximum=-5, singleStep=1, pageStep=5)
        self.others.setValue(int(self.settings.value("others_db", -25)))
        self.others.setToolTip("Wie viel leiser die anderen Stimmen im Track einer Stimme sind")
        self.others_label = QLabel(objectName="Numeric")
        self.others.valueChanged.connect(self.show_others)
        self.show_others(self.others.value())
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
                              "Grand Piano: alle Stimmen als Flügel")
        op.addWidget(QLabel("Andere Stimmen"))
        op.addWidget(self.others, 1)
        op.addWidget(self.others_label)
        op.addSpacing(16)
        op.addWidget(QLabel("Dynamik"))
        op.addWidget(self.dynamic)
        op.addSpacing(16)
        op.addWidget(QLabel("Klang"))
        op.addWidget(self.sound)

        # Statuszeile
        status = QWidget(objectName="StatusBar")
        st = QVBoxLayout(status)
        st.setContentsMargins(12, 8, 12, 10)
        self.bar = QProgressBar(textVisible=False)
        self.bar.hide()
        row = QHBoxLayout()
        self.status = QLabel("", objectName="Muted")
        self.open_btn = QPushButton("Ausgabeordner öffnen", objectName="Quiet", clicked=self.open_output)
        self.open_btn.hide()
        self.start_btn = QPushButton("Tracks erstellen", objectName="Primary", clicked=self.start_or_cancel)
        row.addWidget(self.status, 1)
        row.addWidget(self.open_btn)
        row.addWidget(self.start_btn)
        st.addWidget(self.bar)
        st.addLayout(row)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(toolbar)
        layout.addWidget(self.stack, 1)
        layout.addWidget(options)
        layout.addWidget(status)

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
        self.update_label.show()
        self.update_btn.show()
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
        box = QMessageBox(QMessageBox.Warning, "Voraussetzungen fehlen",
                          "Für den Export fehlt:\n\n" + "\n".join(f"• {m}" for m in missing),
                          QMessageBox.Ok, self)
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
        return [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())]

    def add_score(self, path: Path):
        path = path.resolve()
        if path.suffix.lower() != ".mscz" or path in self.scores():
            return
        tracks = 0
        try:
            names = [n for n, _ in core.voices(path)[1:]]
            detail = f"{len(names)} Stimmen: " + ", ".join(names)
            tracks = len(names) + 1
        except Exception as error:  # noqa: BLE001 - eine kaputte Datei darf die Liste nicht sprengen
            detail = f"nicht lesbar ({error})"
        item = QListWidgetItem(f"{path.stem}\n{detail}")
        item.setData(Qt.UserRole, path)
        item.setData(Qt.UserRole + 1, tracks)
        item.setToolTip(str(path))
        self.list.addItem(item)

    def add_paths(self, paths):
        for p in map(Path, paths):
            for f in sorted(p.glob("*.mscz")) if p.is_dir() else [p]:
                self.add_score(f)
        self.status.setText("")
        self.update_buttons()

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
        self.status.setText("")
        self.update_buttons()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and not self.worker:
            event.acceptProposedAction()

    def dropEvent(self, event):
        self.add_paths(u.toLocalFile() for u in event.mimeData().urls())

    # --- Zustand ----------------------------------------------------------

    def show_others(self, value: int):
        self.others_label.setText(f"{value} dB")

    def update_buttons(self):
        busy = self.worker is not None
        self.stack.setCurrentIndex(1 if self.list.count() else 0)
        self.remove_btn.setEnabled(not busy and bool(self.list.selectedItems()))
        self.start_btn.setEnabled(busy or self.list.count() > 0)
        self.start_btn.setText("Abbrechen" if busy else "Tracks erstellen")
        for w in (self.others, self.dynamic, self.sound, self.list, self.paths_btn):
            w.setEnabled(not busy)
        # Kein Neustart mitten im Rendern: MuseScore liefe verwaist weiter.
        self.update_btn.setEnabled(not busy)
        if not busy and not self.status.text() and self.list.count():
            n = sum(self.list.item(i).data(Qt.UserRole + 1) for i in range(self.list.count()))
            self.status.setText(f"{self.list.count()} Partitur(en), {n} Tracks")

    def save_settings(self):
        self.settings.setValue("others_db", self.others.value())
        self.settings.setValue("dynamic", self.dynamic.currentData() or "")
        self.settings.setValue("sound", self.sound.currentData())
        self.settings.setValue("scores", [str(s) for s in self.scores()])

    # --- Rendern ----------------------------------------------------------

    def start_or_cancel(self):
        if self.worker:
            self.worker.stop.set()
            self.status.setText("Breche ab …")
            self.start_btn.setEnabled(False)
            return
        if not Path(self.mscore()).is_file():
            QMessageBox.critical(self, "MuseScore fehlt",
                                 f"MuseScore nicht gefunden:\n{self.mscore()}\n\nPfad unter „Pfade …“ einstellen.")
            return
        self.save_settings()
        opts = core.Options(others_db=float(self.others.value()), flat_dynamic=self.dynamic.currentData(),
                                 sound=self.sound.currentData(), mscore=self.mscore())
        scores = [self.list.item(i).data(Qt.UserRole) for i in range(self.list.count())
                  if self.list.item(i).data(Qt.UserRole + 1)]
        if not scores:
            QMessageBox.warning(self, "Nichts zu tun", "Keine lesbare Partitur in der Liste.")
            return
        self.last_out = scores[0].parent / core.safe(scores[0].stem)
        self.worker = Worker(scores, opts)
        self.worker.progress.connect(self.on_progress)
        self.worker.done.connect(self.on_done)
        self.bar.setRange(0, 0)
        self.bar.show()
        self.open_btn.hide()
        self.status.setText("Starte MuseScore …")
        self.worker.start()
        self.update_buttons()

    def on_progress(self, text: str, done: int, total: int):
        self.bar.setRange(0, total)
        self.bar.setValue(done)
        self.status.setText(f"{text} … {done}/{total}")

    def on_done(self, results):
        self.worker.wait()
        self.worker = None
        self.bar.hide()
        if isinstance(results, core.Cancelled):
            self.status.setText("Abgebrochen.")
        elif isinstance(results, Exception):
            self.status.setText("Fehler.")
            QMessageBox.critical(self, "Fehler beim Rendern", str(results))
        else:
            bad = [r for r in results if not r.ok]
            self.status.setText(f"Fertig: {len(results)} Tracks erstellt."
                                + (f" {len(bad)} verdächtig leise oder fehlend." if bad else ""))
            self.open_btn.show()
            if bad:
                QMessageBox.warning(self, "Bitte prüfen", "\n".join(r.out.name for r in bad))
        self.update_buttons()

    def open_output(self):
        if self.last_out:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.last_out)))

    def closeEvent(self, event):
        if self.worker:
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
    window = Window()
    window.add_paths(sys.argv[1:])
    window.show()
    QTimer.singleShot(0, window.warn_missing_requirements)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
