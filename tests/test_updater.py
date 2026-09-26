"""UpdateService muss in jedem Fehlerfall still bleiben."""
from types import SimpleNamespace

from partfocus.updater import PendingUpdate, UpdateService


class FakeManager:
    def __init__(self, info=None, fail=False):
        self.info, self.fail, self.calls = info, fail, []

    def check_for_updates(self):
        if self.fail:
            raise OSError("offline")
        return self.info

    def download_updates(self, raw):
        self.calls.append(("download", raw))

    def wait_exit_then_apply_updates(self, raw, silent, restart):
        self.calls.append(("exit", raw, silent, restart))


def test_not_installed_is_silent():
    def boom():
        raise RuntimeError("not installed")

    service = UpdateService(manager_factory=boom)
    assert not service.is_available()
    assert service.check() is None
    assert service.download(PendingUpdate("1.0.0", None)) is False


def test_check_reports_version():
    info = SimpleNamespace(TargetFullRelease=SimpleNamespace(Version="1.2.3"))
    service = UpdateService(manager_factory=lambda: FakeManager(info))
    assert service.check() == PendingUpdate("1.2.3", info)


def test_offline_check_is_silent():
    assert UpdateService(manager_factory=lambda: FakeManager(fail=True)).check() is None


def test_install_on_exit_is_silent_without_restart():
    manager = FakeManager()
    service = UpdateService(manager_factory=lambda: manager)
    update = PendingUpdate("2.0.0", "raw")
    assert service.download(update) and service.install_on_exit(update)
    assert manager.calls == [("download", "raw"), ("exit", "raw", True, False)]
