"""
PyStudio – Professional Python Desktop IDE
Entry point for launching the PySide6 desktop application on Windows 10/11, macOS, and Linux.
"""

from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("PyStudio")
    app.setOrganizationName("PyStudio")

    base_dir = Path(__file__).resolve().parent
    window = MainWindow(base_dir)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
