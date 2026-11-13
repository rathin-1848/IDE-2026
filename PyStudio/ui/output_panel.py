"""
Bottom Output Panel for PyStudio.
Includes tabs for:
- Output (read-only formatted run output & exit code)
- Terminal (interactive console with stdin input() support)
- Problems (real-time AST syntax error list)
- Runtime Errors (parsed Python traceback with click-to-jump-to-line)
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont, QTextCharFormat, QTextCursor
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.problems_analyzer import CodeProblem
from core.python_runner import RuntimeErrorInfo


class OutputPanel(QFrame):
    """Tabbed bottom panel hosting Output, Interactive Terminal, Problems, and Runtime Errors."""

    stdin_submitted = Signal(str)
    jump_to_line_requested = Signal(str, int)  # (file_path_or_name, line)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("BottomPanel")
        self.setMinimumHeight(140)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QHBoxLayout()
        header.setContentsMargins(8, 4, 8, 4)

        self.tabs = QTabWidget()

        mono_font = QFont("JetBrains Mono", 11)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)

        # Tab 0: Output
        self.output_view = QPlainTextEdit()
        self.output_view.setReadOnly(True)
        self.output_view.setFont(mono_font)
        self.tabs.addTab(self.output_view, "Output")

        # Tab 1: Interactive Terminal (stdin + stdout/stderr)
        terminal_container = QWidget()
        term_layout = QVBoxLayout(terminal_container)
        term_layout.setContentsMargins(0, 0, 0, 0)
        term_layout.setSpacing(0)

        self.terminal_view = QPlainTextEdit()
        self.terminal_view.setReadOnly(True)
        self.terminal_view.setFont(mono_font)
        term_layout.addWidget(self.terminal_view)

        input_row = QFrame()
        input_layout = QHBoxLayout(input_row)
        input_layout.setContentsMargins(8, 6, 8, 6)
        input_layout.setSpacing(8)
        prompt_lbl = QLabel("stdin >")
        prompt_lbl.setFont(mono_font)
        self.stdin_input = QLineEdit()
        self.stdin_input.setPlaceholderText("Type input for Python input() and press Enter...")
        self.stdin_input.setFont(mono_font)
        self.stdin_input.returnPressed.connect(self._submit_stdin)

        self.btn_send_stdin = QPushButton("Send")
        self.btn_send_stdin.setProperty("class", "ToolbarBtn")
        self.btn_send_stdin.clicked.connect(self._submit_stdin)

        btn_clear = QPushButton("Clear")
        btn_clear.setProperty("class", "ToolbarBtn")
        btn_clear.clicked.connect(self.clear_all_output)

        input_layout.addWidget(prompt_lbl)
        input_layout.addWidget(self.stdin_input)
        input_layout.addWidget(self.btn_send_stdin)
        input_layout.addWidget(btn_clear)
        term_layout.addWidget(input_row)

        self.tabs.addTab(terminal_container, "Terminal")

        # Tab 2: Problems
        self.problems_list = QListWidget()
        self.problems_list.itemClicked.connect(self._on_problem_clicked)
        self.tabs.addTab(self.problems_list, "Problems (0)")

        # Tab 3: Runtime Errors
        self.errors_list = QListWidget()
        self.errors_list.itemClicked.connect(self._on_error_clicked)
        self.tabs.addTab(self.errors_list, "Runtime Errors (0)")

        layout.addWidget(self.tabs)

    def start_run(self, script_name: str) -> None:
        self.output_view.clear()
        self.errors_list.clear()
        self.tabs.setTabText(3, "Runtime Errors (0)")
        header = f"--- Running {script_name} ---\n"
        self._append_colored(self.output_view, header, "#38BDF8")
        self._append_colored(self.terminal_view, f"\n$ python {script_name}\n", "#38BDF8")
        self.tabs.setCurrentIndex(1)  # Switch to interactive Terminal so input() works seamlessly
        self.stdin_input.setFocus()

    def append_stdout(self, text: str) -> None:
        self._append_colored(self.output_view, text, "#E5E7EB")
        self._append_colored(self.terminal_view, text, "#E5E7EB")

    def append_stderr(self, text: str) -> None:
        self._append_colored(self.output_view, text, "#F87171")
        self._append_colored(self.terminal_view, text, "#F87171")

    def finish_run(self, exit_code: int, was_stopped: bool) -> None:
        if was_stopped:
            msg = "\n[Process terminated by user]\n"
            color = "#FBBF24"
        elif exit_code == 0:
            msg = f"\n[Process finished with exit code {exit_code}]\n"
            color = "#34D399"
        else:
            msg = f"\n[Process exited with code {exit_code}]\n"
            color = "#F87171"

        self._append_colored(self.output_view, msg, color)
        self._append_colored(self.terminal_view, msg, color)

    def set_problems(self, problems: List[CodeProblem]) -> None:
        self.problems_list.clear()
        self.tabs.setTabText(2, f"Problems ({len(problems)})")
        for prob in problems:
            text = f"[{prob.severity}] {prob.file_name}:{prob.line}:{prob.column} — {prob.message}"
            item = QListWidgetItem(text)
            item.setForeground(QColor("#F87171"))
            item.setData(Qt.ItemDataRole.UserRole, (prob.file_name, prob.line))
            self.problems_list.addItem(item)

    def add_runtime_error(self, info: RuntimeErrorInfo) -> None:
        text = (
            f"{info.error_type}: {info.message}\n"
            f"  Location: {info.file_path or '<script>'} (Line {info.line})"
        )
        item = QListWidgetItem(text)
        item.setForeground(QColor("#FCA5A5"))
        item.setData(Qt.ItemDataRole.UserRole, (info.file_path, info.line))
        self.errors_list.addItem(item)
        self.tabs.setTabText(3, f"Runtime Errors ({self.errors_list.count()})")
        self.tabs.setCurrentIndex(3)

    def clear_all_output(self) -> None:
        self.output_view.clear()
        self.terminal_view.clear()

    def _submit_stdin(self) -> None:
        text = self.stdin_input.text()
        self.stdin_input.clear()
        self._append_colored(self.terminal_view, f"{text}\n", "#93C5FD")
        self.stdin_submitted.emit(text)

    def _on_problem_clicked(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.jump_to_line_requested.emit(data[0], data[1])

    def _on_error_clicked(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.jump_to_line_requested.emit(data[0], data[1])

    @staticmethod
    def _append_colored(view: QPlainTextEdit, text: str, hex_color: str) -> None:
        cursor = view.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(hex_color))
        cursor.insertText(text, fmt)
        view.setTextCursor(cursor)
        view.ensureCursorVisible()
