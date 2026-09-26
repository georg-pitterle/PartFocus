"""Einstiegsskript für PyInstaller.

PyInstaller braucht ein einfaches Skript; die Module des Pakets importieren
relativ und funktionieren nur als Teil des Pakets.
"""

from partfocus.gui import main

if __name__ == "__main__":
    raise SystemExit(main())
