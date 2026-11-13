"""
MainWindow for PyStudio – integrates Toolbar, Activity Bar, Sidebar,
Tabbed Python Editor, Bottom Output/Terminal/Problems Panel, Status Bar,
File Manager, and Python Subprocess Runner.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QCloseEvent, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from core.file_manager import FileManager
from core.problems_analyzer import analyze_python_source
from core.python_runner import PythonRunner
from ui.editor import EditorArea, PythonCodeEditor
from ui.output_panel import OutputPanel
from ui.settings_dialog import SettingsDialog
from ui.sidebar import ActivityBar, SidebarPanel
from ui.status_bar import IdeStatusBar
from ui.toolbar import TopToolbar


class MainWindow(QMainWindow):
    """Primary desktop window for PyStudio IDE."""

    def __init__(self, base_dir: Path) -> None:
        super().__init__()
        self.base_dir = base_dir
        self.icons_dir = base_dir / "assets" / "icons"
        self.resources_dir = base_dir / "resources"
        self.default_workspace = base_dir / "workspace"
        self.default_workspace.mkdir(parents=True, exist_ok=True)

        self.theme = "dark"
        self.font_size = 13
        self.tab_width = 4

        self.file_manager = FileManager(self.default_workspace)
        self.runner = PythonRunner(self)

        self.setWindowTitle("PyStudio – Python IDE")
        self.resize(1360, 860)

        self._build_ui()
        self._connect_signals()
        self._register_shortcuts()
        self.apply_theme(self.theme)

        starter = self.default_workspace / "hello_pystudio.py"
        if starter.exists():
            self.open_file_from_path(starter)
        else:
            self.new_untitled_file()

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.toolbar = TopToolbar(self.icons_dir, self)
        root_layout.addWidget(self.toolbar)

        workspace_row = QHBoxLayout()
        workspace_row.setContentsMargins(0, 0, 0, 0)
        workspace_row.setSpacing(0)

        self.activity_bar = ActivityBar(self.icons_dir, self)
        workspace_row.addWidget(self.activity_bar)

        self.h_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.sidebar = SidebarPanel(self.file_manager, self.icons_dir, self)
        self.h_splitter.addWidget(self.sidebar)

        self.v_splitter = QSplitter(Qt.Orientation.Vertical)
        self.editor_area = EditorArea(self)
        self.output_panel = OutputPanel(self)
        self.v_splitter.addWidget(self.editor_area)
        self.v_splitter.addWidget(self.output_panel)
        self.v_splitter.setStretchFactor(0, 3)
        self.v_splitter.setStretchFactor(1, 1)
        self.v_splitter.setSizes([560, 230])

        self.h_splitter.addWidget(self.v_splitter)
        self.h_splitter.setStretchFactor(0, 0)
        self.h_splitter.setStretchFactor(1, 1)
        self.h_splitter.setSizes([250, 1060])

        workspace_row.addWidget(self.h_splitter, 1)
        root_layout.addLayout(workspace_row, 1)

        self.status_bar = IdeStatusBar(self)
        self.setStatusBar(self.status_bar)

    def _connect_signals(self) -> None:
        self.toolbar.new_file_clicked.connect(self.new_untitled_file)
        self.toolbar.open_file_clicked.connect(self.open_file_dialog)
        self.toolbar.save_file_clicked.connect(self.save_current_file)
        self.toolbar.run_clicked.connect(self.run_current_file)
        self.toolbar.stop_clicked.connect(self.runner.stop)
        self.toolbar.settings_clicked.connect(self.open_settings)

        self.activity_bar.view_changed.connect(self._on_activity_selected)
        self.activity_bar.settings_requested.connect(self.open_settings)

        self.sidebar.file_activated.connect(self.open_file_from_path)
        self.sidebar.search_result_activated.connect(self._open_and_jump)
        self.sidebar.open_folder_requested.connect(self.open_folder_dialog)

        self.editor_area.active_editor_changed.connect(self._on_active_editor_changed)
        self.editor_area.editor_text_changed.connect(self._on_editor_text_changed)
        self.editor_area.cursor_changed.connect(self.status_bar.set_cursor_position)
        self.editor_area.tab_close_requested.connect(self._handle_close_tab)

        self.output_panel.stdin_submitted.connect(self.runner.send_input)
        self.output_panel.jump_to_line_requested.connect(self._jump_from_panel)

        self.runner.started.connect(self._on_process_started)
        self.runner.stdout_received.connect(self.output_panel.append_stdout)
        self.runner.stderr_received.connect(self.output_panel.append_stderr)
        self.runner.runtime_error_detected.connect(self.output_panel.add_runtime_error)
        self.runner.finished.connect(self._on_process_finished)

    def _register_shortcuts(self) -> None:
        QShortcut(QKeySequence("Ctrl+N"), self, self.new_untitled_file)
        QShortcut(QKeySequence("Ctrl+O"), self, self.open_file_dialog)
        QShortcut(QKeySequence("Ctrl+S"), self, self.save_current_file)
        QShortcut(QKeySequence("F5"), self, self.run_current_file)
        QShortcut(QKeySequence("Shift+F5"), self, self.runner.stop)
        QShortcut(QKeySequence("Ctrl+F"), self, self.editor_area.find_bar.open_bar)
        QShortcut(QKeySequence("Ctrl+B"), self, self.toggle_sidebar)
        QShortcut(QKeySequence("Ctrl+,"), self, self.open_settings)

    def apply_theme(self, theme: str) -> None:
        self.theme = theme
        qss_file = self.resources_dir / ("styles_light.qss" if theme == "light" else "styles_dark.qss")
        if qss_file.exists():
            QApplication.instance().setStyleSheet(qss_file.read_text(encoding="utf-8"))
        self.editor_area.apply_settings(theme, self.font_size, self.tab_width)

    def toggle_sidebar(self) -> None:
        self.sidebar.setVisible(not self.sidebar.isVisible())

    def _on_activity_selected(self, view_index: int) -> None:
        if not self.sidebar.isVisible():
            self.sidebar.show()
        self.sidebar.set_active_page(view_index)

    def new_untitled_file(self) -> None:
        editor = self.editor_area.open_tab(None, '# New Python Script\nprint("Hello, PyStudio!")\n')
        self._update_problems(editor)

    def open_file_dialog(self) -> None:
        file_str, _ = QFileDialog.getOpenFileName(
            self,
            "Open Python File",
            str(self.file_manager.workspace_root),
            "Python Files (*.py *.pyw);;All Files (*)",
        )
        if file_str:
            self.open_file_from_path(Path(file_str))

    def open_folder_dialog(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Open Project Folder",
            str(self.file_manager.workspace_root),
        )
        if folder:
            self.file_manager.set_workspace(Path(folder))
            self.sidebar.refresh_tree()
            self.status_bar.set_app_status(f"Workspace: {folder}")

    def open_file_from_path(self, path: Path) -> None:
        try:
            content = self.file_manager.read_file(path)
        except OSError as exc:
            QMessageBox.critical(self, "Error Opening File", str(exc))
            return
        editor = self.editor_area.open_tab(path, content)
        self._update_problems(editor)

    def _open_and_jump(self, path: Path, line: int) -> None:
        self.open_file_from_path(path)
        editor = self.editor_area.current_editor()
        if editor:
            editor.goto_line(line)

    def _jump_from_panel(self, file_ref: str, line: int) -> None:
        if file_ref:
            candidate = Path(file_ref)
            if candidate.exists():
                self._open_and_jump(candidate, line)
                return
        editor = self.editor_area.current_editor()
        if editor:
            editor.goto_line(line)

    def save_current_file(self) -> bool:
        editor = self.editor_area.current_editor()
        if not editor:
            return False
        return self._save_editor(editor)

    def _save_editor(self, editor: PythonCodeEditor) -> bool:
        target = editor.file_path
        if target is None:
            file_str, _ = QFileDialog.getSaveFileName(
                self,
                "Save Python File",
                str(self.file_manager.workspace_root / "untitled.py"),
                "Python Files (*.py)",
            )
            if not file_str:
                return False
            target = Path(file_str)
            if target.suffix.lower() != ".py":
                target = target.with_suffix(".py")

        try:
            self.file_manager.write_file(target, editor.toPlainText())
        except OSError as exc:
            QMessageBox.critical(self, "Error Saving File", str(exc))
            return False

        self.editor_area.mark_saved(editor, target)
        self.sidebar.refresh_tree()
        self.status_bar.set_file_name(target.name)
        self.status_bar.set_app_status(f"Saved {target.name}")
        return True

    def run_current_file(self) -> None:
        editor = self.editor_area.current_editor()
        if not editor:
            return

        if editor.file_path is None or editor.document().isModified():
            if not self._save_editor(editor):
                return

        assert editor.file_path is not None
        self._update_problems(editor)
        self.runner.run_script(editor.file_path, self.file_manager.workspace_root)

    def _on_process_started(self, script_path: str) -> None:
        self.toolbar.set_running(True)
        name = Path(script_path).name
        self.output_panel.start_run(name)
        self.status_bar.set_app_status(f"Running {name}...")

    def _on_process_finished(self, exit_code: int, was_stopped: bool) -> None:
        self.toolbar.set_running(False)
        self.output_panel.finish_run(exit_code, was_stopped)
        if was_stopped:
            self.status_bar.set_app_status("Execution stopped")
        elif exit_code == 0:
            self.status_bar.set_app_status("Execution completed (exit code 0)")
        else:
            self.status_bar.set_app_status(f"Execution failed (exit code {exit_code})")

    def _on_active_editor_changed(self, editor: Optional[PythonCodeEditor]) -> None:
        if editor is None:
            self.status_bar.set_file_name("No file open")
            self.output_panel.set_problems([])
            return
        name = editor.file_path.name if editor.file_path else "untitled.py"
        self.status_bar.set_file_name(name)
        self._update_problems(editor)

    def _on_editor_text_changed(self, editor: PythonCodeEditor) -> None:
        if editor is self.editor_area.current_editor():
            self._update_problems(editor)

    def _update_problems(self, editor: PythonCodeEditor) -> None:
        name = editor.file_path.name if editor.file_path else "untitled.py"
        problems = analyze_python_source(editor.toPlainText(), name)
        self.output_panel.set_problems(problems)

    def _handle_close_tab(self, index: int) -> None:
        widget = self.editor_area.tabs.widget(index)
        if not isinstance(widget, PythonCodeEditor):
            self.editor_area.close_tab(index)
            return

        if widget.document().isModified():
            name = widget.file_path.name if widget.file_path else "untitled.py"
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                f"Save changes to '{name}' before closing?",
                QMessageBox.StandardButton.Save
                | QMessageBox.StandardButton.Discard
                | QMessageBox.StandardButton.Cancel,
            )
            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.Save:
                if not self._save_editor(widget):
                    return

        self.editor_area.close_tab(index)

    def open_settings(self) -> None:
        dialog = SettingsDialog(
            current_theme=self.theme,
            font_size=self.font_size,
            tab_width=self.tab_width,
            python_executable=self.runner.python_executable,
            parent=self,
        )
        if dialog.exec():
            self.font_size = dialog.selected_font_size()
            self.tab_width = dialog.selected_tab_width()
            self.runner.set_python_executable(dialog.selected_python())
            self.apply_theme(dialog.selected_theme())

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802
        for idx in range(self.editor_area.tabs.count()):
            ed = self.editor_area.tabs.widget(idx)
            if isinstance(ed, PythonCodeEditor) and ed.document().isModified():
                name = ed.file_path.name if ed.file_path else "untitled.py"
                reply = QMessageBox.question(
                    self,
                    "Unsaved Changes",
                    f"Save changes to '{name}' before exiting PyStudio?",
                    QMessageBox.StandardButton.Save
                    | QMessageBox.StandardButton.Discard
                    | QMessageBox.StandardButton.Cancel,
                )
                if reply == QMessageBox.StandardButton.Cancel:
                    event.ignore()
                    return
                if reply == QMessageBox.StandardButton.Save:
                    if not self._save_editor(ed):
                        event.ignore()
                        return

        if self.runner.is_running():
            self.runner.stop()
        event.accept()
