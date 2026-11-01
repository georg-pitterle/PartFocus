"""Oberfläche ohne Bildschirm: Tastatur, Zustände und Abschluss."""
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from partfocus import core, gui, theme


class FakeSettings:
    """Ersetzt QSettings, damit Tests nicht in die echten Einstellungen schreiben."""

    def __init__(self, *_):
        self.values = {}

    def value(self, key, default=None):
        return self.values.get(key, default)

    def setValue(self, key, value):
        self.values[key] = value


class NoUpdates:
    def is_available(self):
        return False


class FakeWorker:
    class stop:
        @staticmethod
        def is_set():
            return False

    def wait(self):
        pass


@pytest.fixture(scope="session")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def window(app, monkeypatch):
    monkeypatch.setattr(gui, "QSettings", FakeSettings)
    w = gui.Window(NoUpdates())
    w.show()
    yield w
    w.worker = None
    w.hide()
    w.deleteLater()


def press(window, key, modifiers=Qt.NoModifier):
    focused = window.focusWidget() or window
    QApplication.sendEvent(focused, QKeyEvent(QEvent.KeyPress, key, modifiers))
    QApplication.sendEvent(focused, QKeyEvent(QEvent.KeyRelease, key, modifiers))


def add_item(window, tracks=2):
    window.list.addItem("Lied\n1 Stimme")
    window.list.item(window.list.count() - 1).setData(gui.TRACKS, tracks)
    window.update_buttons()


def test_enter_triggers_focused_button(window):
    clicks = []
    window.start_btn.clicked.disconnect()
    window.start_btn.clicked.connect(lambda: clicks.append(1))
    add_item(window)
    window.start_btn.setFocus()
    press(window, Qt.Key_Return)
    assert clicks == [1]


def test_unreadable_score_does_not_count_and_cannot_start(window, tmp_path):
    broken = tmp_path / "Kaputt.mscz"
    broken.write_bytes(b"keine zip-Datei")
    window.add_paths([broken])
    assert not window.start_btn.isEnabled()
    assert window.status.text() == "1 nicht lesbar"
    assert "übersprungen" in window.list.item(0).text()


def test_skipped_files_are_reported(window, tmp_path):
    text = tmp_path / "notizen.txt"
    text.write_text("x")
    window.add_paths([text])
    assert "1 übersprungen" in window.status.text()


def test_busy_locks_add_buttons(window):
    window.worker = FakeWorker()
    window.update_buttons()
    assert not window.files_btn.isEnabled() and not window.dir_btn.isEnabled()


def test_cancel_stays_locked_right_after_start(window):
    window.worker = FakeWorker()
    window.cancel_locked = True
    window.update_buttons()
    assert not window.start_btn.isEnabled()
    window.unlock_cancel()
    assert window.start_btn.isEnabled() and window.start_btn.objectName() == "Quiet"


def test_finished_run_makes_open_the_main_action(window, tmp_path):
    out = tmp_path / "Lied" / "a.mp3"
    out.parent.mkdir()
    out.write_bytes(b"x")
    add_item(window)
    window.worker = FakeWorker()
    window.on_done([core.Result(out, None, 0.0)])
    assert window.open_btn.objectName() == "Primary" and window.start_btn.objectName() == "Quiet"
    assert window.status.text().startswith("Fertig: 1 Track in „Lied“")
    window.others.setValue(window.others.value() + 1)
    assert window.open_btn.objectName() == "Quiet" and window.start_btn.objectName() == "Primary"


def test_cancelled_run_says_tracks_are_unchanged(window):
    window.worker = FakeWorker()
    window.on_done(core.Cancelled())
    assert window.status.text() == "Abgebrochen. Vorhandene Tracks sind unverändert."
    assert window.open_btn.isHidden()


def test_close_while_busy_can_keep_running(window, monkeypatch):
    window.worker = FakeWorker()
    monkeypatch.setattr(window, "confirm_close", lambda: False)
    assert window.close() is False


def test_every_field_has_a_name_for_screen_readers(window):
    fields = (window.others, window.dynamic, window.sound, window.format, window.bitrate, window.list, window.bar)
    assert all(f.accessibleName() for f in fields)
    assert [b.accessibleName() for b in window.tempo_btns.values()][:2] == ["Tempo 100 Prozent", "Tempo 90 Prozent"]


def test_shelf_stays_scrollable_but_not_selectable_while_busy(window):
    add_item(window)
    window.worker = FakeWorker()
    window.update_buttons()
    assert window.list.isEnabled() and window.list.selectionMode() == gui.QListWidget.NoSelection


def test_finished_books_carry_a_tick_until_something_changes(window, tmp_path):
    out = tmp_path / "Lied" / "a.mp3"
    out.parent.mkdir()
    out.write_bytes(b"x")
    add_item(window)
    window.worker = FakeWorker()
    window.on_done([core.Result(out, None, 0.0)])
    assert window.all_done
    window.others.setValue(window.others.value() + 1)
    assert not window.all_done


def test_start_button_names_the_track_count(window):
    add_item(window, 8)
    assert window.start_btn.text() == "8 Tracks erstellen"
    window.tempo_btns[80].setChecked(True)
    assert window.start_btn.text() == "16 Tracks erstellen"
    window.format.setCurrentIndex(window.format.findData("both"))
    assert window.start_btn.text() == "32 Tracks erstellen"


def test_books_fill_in_order_with_progress(window):
    add_item(window, 2)
    add_item(window, 2)
    assert window.book_fill(1, 1) == 1.0
    window.progress = 0.625
    assert [window.book_fill(r, b) for r in (0, 1) for b in (0, 1)] == [1.0, 1.0, 0.5, 0.0]
    window.progress = 0.0
    assert window.book_fill(0, 0) == 0.0


@pytest.mark.parametrize("name, field", [("Gesamt", "gesamt"), ("Sopran 1", "sopran"), ("Mezzo", "sopran"),
                                         ("Alto", "alt"), ("Tenor", "tenor"), ("Bariton", "bass"), ("Bass 2", "bass"),
                                         ("Solo Sopran", "solo"), ("Solo 1. Strophe", "solo"), ("Flöte", "solo")])
def test_cover_follows_the_voice(name, field):
    assert gui.cover(name, theme.LIGHT) == getattr(theme.LIGHT, field)


def test_cover_colours_stand_out_on_the_table():
    def luminance(colour):
        rgb = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        return sum(w * (c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
                   for w, c in zip((0.2126, 0.7152, 0.0722), rgb))

    for p in (theme.LIGHT, theme.DARK):
        for name in ("gesamt", "sopran", "alt", "tenor", "bass", "solo"):
            for other in (p.app, p.label):  # Einband gegen Tisch und gegen Titelschild samt Heftklammern
                a, b = sorted((luminance(getattr(p, name)), luminance(other)), reverse=True)
                assert (a + 0.05) / (b + 0.05) >= 3, (name, other)


def test_shelf_stays_on_the_last_piece_at_the_end_of_a_run(window):
    add_item(window, 2)
    add_item(window, 2)
    window.progress = 1.0
    window.follow_progress()
    assert window.shown_row == 1
