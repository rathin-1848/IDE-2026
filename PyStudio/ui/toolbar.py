"""
Top Toolbar widget for PyStudio.
Provides branding and quick actions: New, Open, Save, Run, Stop, and Settings.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton, QWidget


class TopToolbar(QFrame):
    """Main top action bar inspired by VS Code's clean command strip."""

    new_file_clicked = Signal()
    open_file_clicked = Signal()
    save_file_clicked = Signal()
    run_clicked = Signal()
    stop_clicked = Signal()
    settings_clicked = Signal()

    def __init__(self, icons_dir: Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("TopToolbar")
        self.setFixedHeight(48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 4, 12, 4)
        layout.setSpacing(6)

        brand = QLabel("PyStudio")
        brand.setObjectName("BrandLabel")
        layout.addWidget(brand)

        self.btn_new = self._make_button("New File", icons_dir / "file-plus.svg", "Ctrl+N")
        self.btn_open = self._make_button("Open", icons_dir / "folder-open.svg", "Ctrl+O")
        self.btn_save = self._make_button("Save", icons_dir / "save.svg", "Ctrl+S")

        self.btn_run = QPushButton("Run")
        self.btn_run.setObjectName("RunBtn")
        self.btn_run.setIcon(QIcon(str(icons_dir / "play.svg")))
        self.btn_run.setToolTip("Run current Python file (F5)")
        self.btn_run.setCursor(Qt.CursorShape.PointingHandCursor)

        self.btn_stop = QPushButton("Stop")
        self.btn_stop.setObjectName("StopBtn")
        self.btn_stop.setIcon(QIcon(str(icons_dir / "square.svg")))
        self.btn_stop.setToolTip("Terminate running Python process (Shift+F5)")
        self.btn_stop.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_stop.setEnabled(False)

        self.btn_settings = self._make_button("Settings", icons_dir / "settings.svg", "Ctrl+,")

        layout.addWidget(self.btn_new)
        layout.addWidget(self.btn_open)
        layout.addWidget(self.btn_save)
        layout.addStretch(1)
        layout.addWidget(self.btn_run)
        layout.addWidget(self.btn_stop)
        layout.addWidget(self.btn_settings)

        self.btn_new.clicked.connect(self.new_file_clicked.emit)
        self.btn_open.clicked.connect(self.open_file_clicked.emit)
        self.btn_save.clicked.connect(self.save_file_clicked.emit)
        self.btn_run.clicked.connect(self.run_clicked.emit)
        self.btn_stop.clicked.connect(self.stop_clicked.emit)
        self.btn_settings.clicked.connect(self.settings_clicked.emit)

    def _make_button(self, text: str, icon_path: Path, shortcut_hint: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setProperty("class", "ToolbarBtn")
        btn.setIcon(QIcon(str(icon_path)))
        btn.setToolTip(f"{text} ({shortcut_hint})")
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn

    def set_running(self, running: bool) -> None:
        """Toggle Run/Stop enabled state while a Python subprocess is active."""
        self.btn_run.setEnabled(not running)
        self.btn_stop.setEnabled(running)
