"""
Activity Bar and Sidebar (File Explorer & Workspace Search) for PyStudio.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMenu,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QToolButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.file_manager import FileManager, WorkspaceItem


class ActivityBar(QFrame):
    """Leftmost narrow vertical bar with Explorer, Search, and Settings buttons."""

    view_changed = Signal(int)  # 0 = Explorer, 1 = Search
    settings_requested = Signal()

    def __init__(self, icons_dir: Path, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("ActivityBar")
        self.setFixedWidth(48)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 8, 0, 8)
        layout.setSpacing(4)

        self.group = QButtonGroup(self)
        self.group.setExclusive(True)

        self.btn_explorer = self._make_btn(icons_dir / "file-code.svg", "Explorer (Ctrl+Shift+E)")
        self.btn_search = self._make_btn(icons_dir / "search.svg", "Search Workspace (Ctrl+Shift+F)")
        self.btn_settings = self._make_btn(icons_dir / "settings.svg", "Settings (Ctrl+,)", checkable=False)

        self.btn_explorer.setChecked(True)
        self.group.addButton(self.btn_explorer, 0)
        self.group.addButton(self.btn_search, 1)

        layout.addWidget(self.btn_explorer)
        layout.addWidget(self.btn_search)
        layout.addStretch(1)
        layout.addWidget(self.btn_settings)

        self.group.idClicked.connect(self.view_changed.emit)
        self.btn_settings.clicked.connect(self.settings_requested.emit)

    def _make_btn(self, icon_path: Path, tooltip: str, checkable: bool = True) -> QToolButton:
        btn = QToolButton()
        btn.setProperty("class", "ActivityBtn")
        btn.setIcon(QIcon(str(icon_path)))
        btn.setIconSize(QSize(20, 20))
        btn.setFixedSize(48, 44)
        btn.setCheckable(checkable)
        btn.setToolTip(tooltip)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        return btn


class SidebarPanel(QFrame):
    """Collapsible, resizable sidebar containing File Explorer and Search panels."""

    file_activated = Signal(Path)
    search_result_activated = Signal(Path, int)
    open_folder_requested = Signal()

    def __init__(
        self,
        file_manager: FileManager,
        icons_dir: Path,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("SidebarPanel")
        self.file_manager = file_manager
        self.icons_dir = icons_dir
        self.setMinimumWidth(200)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack)

        # Page 0: Explorer
        explorer_page = QWidget()
        exp_layout = QVBoxLayout(explorer_page)
        exp_layout.setContentsMargins(0, 0, 0, 0)
        exp_layout.setSpacing(0)

        header_row = QWidget()
        header_layout = QHBoxLayout(header_row)
        header_layout.setContentsMargins(12, 6, 8, 6)
        header_layout.setSpacing(4)

        header_lbl = QLabel("EXPLORER")
        header_lbl.setObjectName("SidebarHeader")
        header_lbl.setContentsMargins(0, 0, 0, 0)

        btn_new_file = QPushButton("+ File")
        btn_new_file.setProperty("class", "ToolbarBtn")
        btn_new_file.setToolTip("Create new Python file in workspace")
        btn_new_file.clicked.connect(self.prompt_new_file)

        btn_open_folder = QPushButton("Folder")
        btn_open_folder.setProperty("class", "ToolbarBtn")
        btn_open_folder.setToolTip("Open project folder")
        btn_open_folder.clicked.connect(self.open_folder_requested.emit)

        header_layout.addWidget(header_lbl)
        header_layout.addStretch(1)
        header_layout.addWidget(btn_new_file)
        header_layout.addWidget(btn_open_folder)
        exp_layout.addWidget(header_row)

        self.tree = QTreeWidget()
        self.tree.setHeaderHidden(True)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.itemDoubleClicked.connect(self._on_tree_double_click)
        self.tree.itemActivated.connect(self._on_tree_double_click)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        exp_layout.addWidget(self.tree)

        # Page 1: Search
        search_page = QWidget()
        srch_layout = QVBoxLayout(search_page)
        srch_layout.setContentsMargins(10, 8, 10, 8)
        srch_layout.setSpacing(8)

        srch_lbl = QLabel("SEARCH WORKSPACE")
        srch_lbl.setObjectName("SidebarHeader")
        srch_layout.addWidget(srch_lbl)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search in Python files...")
        self.search_input.returnPressed.connect(self.run_workspace_search)
        self.search_input.textChanged.connect(self.run_workspace_search)
        srch_layout.addWidget(self.search_input)

        self.search_results = QListWidget()
        self.search_results.itemClicked.connect(self._on_search_item_clicked)
        srch_layout.addWidget(self.search_results)

        self.stack.addWidget(explorer_page)
        self.stack.addWidget(search_page)

        self.refresh_tree()

    def set_active_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        if index == 1:
            self.search_input.setFocus()

    def refresh_tree(self) -> None:
        self.tree.clear()
        root_name = self.file_manager.workspace_root.name or str(self.file_manager.workspace_root)
        root_item = QTreeWidgetItem([root_name])
        root_item.setData(0, Qt.ItemDataRole.UserRole, self.file_manager.workspace_root)
        root_item.setData(0, Qt.ItemDataRole.UserRole + 1, True)
        root_item.setIcon(0, QIcon(str(self.icons_dir / "folder-open.svg")))
        self.tree.addTopLevelItem(root_item)

        for child in self.file_manager.list_tree():
            self._append_tree_item(root_item, child)
        root_item.setExpanded(True)

    def _append_tree_item(self, parent_item: QTreeWidgetItem, node: WorkspaceItem) -> None:
        item = QTreeWidgetItem([node.name])
        item.setData(0, Qt.ItemDataRole.UserRole, node.path)
        item.setData(0, Qt.ItemDataRole.UserRole + 1, node.is_dir)
        icon_name = "folder-open.svg" if node.is_dir else "file-code.svg"
        item.setIcon(0, QIcon(str(self.icons_dir / icon_name)))
        parent_item.addChild(item)

        for sub in node.children:
            self._append_tree_item(item, sub)

    def _on_tree_double_click(self, item: QTreeWidgetItem) -> None:
        path: Optional[Path] = item.data(0, Qt.ItemDataRole.UserRole)
        is_dir: bool = bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
        if path and not is_dir:
            self.file_activated.emit(path)

    def _show_context_menu(self, pos) -> None:
        item = self.tree.itemAt(pos)
        target_dir = self.file_manager.workspace_root
        target_path: Optional[Path] = None
        is_dir = True

        if item:
            target_path = item.data(0, Qt.ItemDataRole.UserRole)
            is_dir = bool(item.data(0, Qt.ItemDataRole.UserRole + 1))
            if target_path:
                target_dir = target_path if is_dir else target_path.parent

        menu = QMenu(self)
        act_new = menu.addAction("New Python File...")
        act_folder = menu.addAction("New Folder...")
        act_delete = None
        if target_path and target_path != self.file_manager.workspace_root:
            menu.addSeparator()
            act_delete = menu.addAction(f"Delete {target_path.name}")

        chosen = menu.exec(self.tree.viewport().mapToGlobal(pos))
        if chosen == act_new:
            self.prompt_new_file(target_dir)
        elif chosen == act_folder:
            name, ok = QInputDialog.getText(self, "New Folder", "Folder name:")
            if ok and name.strip():
                self.file_manager.create_folder(target_dir, name)
                self.refresh_tree()
        elif act_delete and chosen == act_delete and target_path:
            confirm = QMessageBox.question(
                self,
                "Delete Item",
                f"Are you sure you want to delete '{target_path.name}'?",
            )
            if confirm == QMessageBox.StandardButton.Yes:
                self.file_manager.delete_path(target_path)
                self.refresh_tree()

    def prompt_new_file(self, directory: Optional[Path] = None) -> None:
        target_dir = directory if isinstance(directory, Path) else self.file_manager.workspace_root
        filename, ok = QInputDialog.getText(self, "New Python File", "File name (e.g. script.py):")
        if ok and filename.strip():
            try:
                created = self.file_manager.create_python_file(target_dir, filename)
                self.refresh_tree()
                self.file_activated.emit(created)
            except FileExistsError as exc:
                QMessageBox.warning(self, "File Exists", str(exc))

    def run_workspace_search(self) -> None:
        self.search_results.clear()
        query = self.search_input.text()
        if not query.strip():
            return
        matches = self.file_manager.search_in_workspace(query)
        for path, line_num, snippet in matches:
            rel = path.relative_to(self.file_manager.workspace_root)
            item = QListWidgetItem(f"{rel}:{line_num}  —  {snippet}")
            item.setData(Qt.ItemDataRole.UserRole, (path, line_num))
            self.search_results.addItem(item)

    def _on_search_item_clicked(self, item: QListWidgetItem) -> None:
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            path, line_num = data
            self.search_result_activated.emit(path, line_num)
