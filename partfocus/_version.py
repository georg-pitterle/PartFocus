"""Einzige Quelle der Version zur Laufzeit.

Ein PyInstaller-Bundle hat kein dist-info, importlib.metadata hilft dort nicht.
release-please hält die Zeile unten mit pyproject.toml gleich.
"""

__version__ = "0.2.0"  # x-release-please-version
