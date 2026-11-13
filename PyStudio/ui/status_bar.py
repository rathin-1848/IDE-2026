"""
Status Bar widget for PyStudio.
Displays Python interpreter version, active filename, cursor line/column,
file encoding, and application execution status.
"""

from __future__ import annotations

import platform
from typing import Optional

from PySide6.QtWidgets import QLabel, QStatusBar, QWidget


class IdeStatusBar(QStatusBar):
    """Clean developer status bar with permanent right-aligned telemetry."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)

        self.status_label = QLabel("Ready")
        self.file_label = QLabel("No file open")
        self.cursor_label = QLabel("Ln 1, Col 1")
        self.encoding_label = QLabel("UTF-8")
        self.python_label = QLabel(f"Python {platform.python_version()}")

        self.addWidget(self.status_label, 1)
        self.addPermanentWidget(self.file_label)
        self.addPermanentWidget(self._sep())
        self.addPermanentWidget(self.cursor_label)
        self.addPermanentWidget(self._sep())
        self.addPermanentWidget(self.encoding_label)
        self.addPermanentWidget(self._sep())
        self.addPermanentWidget(self.python_label)

    @staticmethod
    def _sep() -> QLabel:
        lbl = QLabel("  |  ")
        lbl.setStyleSheet("color: #6B7280;")
        return lbl

    def set_app_status(self, text: str) -> None:
        self.status_label.setText(text)

    def set_file_name(self, name: str) -> None:
        self.file_label.setText(name or "Untitled")

    def set_cursor_position(self, line: int, col: int) -> None:
        self.cursor_label.setText(f"Ln {line}, Col {col}")

    def set_python_version(self, version_text: str) -> None:
        self.python_label.setText(version_text)
