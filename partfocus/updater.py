"""Selbst-Update über die GitHub-Releases des Projekts (aus ScoreCap übernommen).

Velopack erledigt den schweren Teil - eine laufende App ersetzen -, aber nur in
einem installierten Bundle. Aus dem Quellbaum gestartet wirft es, ebenso bei
Netzfehlern. All diese Fälle enden still: Ein Übe-Track-Werkzeug ist kein Ort
für Update-Fehlerdialoge.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable

REPO_URL = "https://github.com/georg-pitterle/PartFocus"

log = logging.getLogger(__name__)


@dataclass(frozen=True)
class PendingUpdate:
    version: str
    raw: object  # velopack UpdateInfo, unverändert zurückgereicht


def _velopack_manager(repo_url: str, prerelease: bool):
    import velopack

    return velopack.UpdateManager(velopack.GithubSource(repo_url, None, prerelease))


def start_velopack() -> None:
    """Velopack zuerst die Kontrolle geben, damit Install- und Update-Hooks laufen.

    Muss vor dem QApplication-Konstruktor kommen, sonst scheitert ein Update.
    Außerhalb eines installierten Bundles tut es nichts.
    """
    try:
        import velopack

        velopack.App().run()
    except Exception as error:  # nicht installiert oder velopack fehlt
        log.info("velopack übersprungen: %s", error)


class UpdateService:
    """Sucht und installiert Updates - oder tut still gar nichts."""

    def __init__(self, repo_url: str = REPO_URL, prerelease: bool = False,
                 manager_factory: Callable[[], object] | None = None) -> None:
        self._factory = manager_factory or (lambda: _velopack_manager(repo_url, prerelease))
        self._manager: object | None = None
        self._tried = False

    def _get_manager(self):
        if not self._tried:
            self._tried = True
            try:
                self._manager = self._factory()
            except Exception as error:
                log.info("keine Updates möglich: %s", error)
                self._manager = None
        return self._manager

    def is_available(self) -> bool:
        return self._get_manager() is not None

    def check(self) -> PendingUpdate | None:
        manager = self._get_manager()
        if manager is None:
            return None
        try:
            info = manager.check_for_updates()
        except Exception as error:
            log.info("Update-Prüfung fehlgeschlagen: %s", error)
            return None
        if info is None:
            return None
        return PendingUpdate(version=str(info.TargetFullRelease.Version), raw=info)

    def download(self, update: PendingUpdate) -> bool:
        """Update in den Paketordner holen. Startet nie etwas neu."""
        manager = self._get_manager()
        if manager is None or update is None:
            return False
        try:
            manager.download_updates(update.raw)
        except Exception as error:
            log.warning("Update %s nicht geladen: %s", update.version, error)
            return False
        return True

    def restart_into(self, update: PendingUpdate) -> bool:
        """Geladenes Update anwenden und neu starten. True, wenn es so weit kam."""
        manager = self._get_manager()
        if manager is None or update is None:
            return False
        try:
            manager.apply_updates_and_restart(update.raw)
        except Exception as error:
            log.warning("Update %s nicht angewendet: %s", update.version, error)
            return False
        return True

    def install_on_exit(self, update: PendingUpdate) -> bool:
        """Velopack das Update nach dem Beenden still und ohne Neustart installieren lassen."""
        manager = self._get_manager()
        if manager is None or update is None:
            return False
        try:
            manager.wait_exit_then_apply_updates(update.raw, silent=True, restart=False)
        except Exception as error:
            log.warning("Update %s nicht eingeplant: %s", update.version, error)
            return False
        return True
