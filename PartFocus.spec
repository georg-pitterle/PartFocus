# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller-Build. Ein Ordner statt einer Datei: Velopack aktualisiert einen
Ordner, und eine One-File-exe würde bei jedem Start über hundert Megabyte entpacken."""

from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs

# PySide6-Essentials bringt mehr mit, als die App braucht.
EXCLUDES = [
    "PySide6.QtQml",
    "PySide6.QtQuick",
    "PySide6.QtQuickWidgets",
    "PySide6.QtSql",
    "PySide6.QtTest",
    "PySide6.QtDesigner",
    "PySide6.QtHelp",
    "PySide6.QtUiTools",
    "PySide6.QtNetwork",
    "PySide6.QtOpenGL",
    "PySide6.QtPdf",
    "tkinter",
    "unittest",
    "pytest",
    "PIL",
]

# Qt schleppt DLLs mit, die das Bundle nie lädt. Nach der Analyse entfernen ist
# der verlässliche Weg: Das Python-Modul auszuschließen lässt die DLL liegen.
DROP_BINARIES = ("qt6quick", "qt6qml", "qt6quickwidgets", "qt6pdf", "qt6opengl", "qt6network")
KEEP_TRANSLATIONS = ("_de.qm", "_en.qm")


def _keep_binary(entry) -> bool:
    return not Path(entry[0]).name.lower().startswith(DROP_BINARIES)


def _keep_data(entry) -> bool:
    dest = entry[0].replace("\\", "/").lower()
    return "/translations/" not in dest or dest.endswith(KEEP_TRANSLATIONS)


a = Analysis(
    ["main.py"],
    # Eine editable-Installation läuft über einen Finder-Hook, dem PyInstaller
    # nicht folgen kann; darum direkt auf den Quellbaum zeigen.
    pathex=[SPECPATH],
    binaries=collect_dynamic_libs("velopack"),
    datas=[("assets/partfocus.ico", "assets")],
    hiddenimports=["velopack"],
    excludes=EXCLUDES,
    noarchive=False,
)

a.binaries = [entry for entry in a.binaries if _keep_binary(entry)]
a.datas = [entry for entry in a.datas if _keep_data(entry)]

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PartFocus",
    console=False,
    icon="assets/partfocus.ico",
    disable_windowed_traceback=False,
)

coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="PartFocus")
