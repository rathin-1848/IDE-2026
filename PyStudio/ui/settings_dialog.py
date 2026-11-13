"""
Settings dialog for PyStudio.
Allows toggling Dark/Light theme, editor font size, tab width, and Python interpreter path.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)


class SettingsDialog(QDialog):
    """Modal configuration dialog for PyStudio preferences."""

    def __init__(
        self,
        current_theme: str,
        font_size: int,
        tab_width: int,
        python_executable: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("PyStudio Settings")
        self.setMinimumWidth(440)

        layout = QVBoxLayout(self)
        form = QFormLayout()
        form.setSpacing(12)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText("Light" if current_theme == "light" else "Dark")

        self.font_spin = QSpinBox()
        self.font_spin.setRange(10, 24)
        self.font_spin.setValue(font_size)

        self.tab_spin = QSpinBox()
        self.tab_spin.setRange(2, 8)
        self.tab_spin.setValue(tab_width)

        py_row = QHBoxLayout()
        self.python_edit = QLineEdit(python_executable)
        btn_browse = QPushButton("Browse...")
        btn_browse.clicked.connect(self._browse_python)
        py_row.addWidget(self.python_edit)
        py_row.addWidget(btn_browse)

        form.addRow("Color Theme:", self.theme_combo)
        form.addRow("Editor Font Size:", self.font_spin)
        form.addRow("Tab Width (spaces):", self.tab_spin)
        form.addRow("Python Interpreter:", py_row)
        layout.addLayout(form)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_python(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Select Python Executable")
        if path:
            self.python_edit.setText(path)

    def selected_theme(self) -> str:
        return self.theme_combo.currentText().lower()

    def selected_font_size(self) -> int:
        return self.font_spin.value()

    def selected_tab_width(self) -> int:
        return self.tab_spin.value()

    def selected_python(self) -> str:
        return self.python_edit.text().strip()
