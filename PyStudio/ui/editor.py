"""
Advanced Python Code Editor for PyStudio.
Features:
- Python syntax highlighting (keywords, builtins, strings, triple-quoted docstrings, comments, numbers, decorators)
- Line number gutter & current line highlight
- Indentation guides (every 4 spaces)
- Smart auto-indentation after ':' and Tab/Backtab handling
- Bracket and quote auto-pairing
- Python keyword/builtin/identifier autocompletion (QCompleter)
- Multi-tab editor manager with dirty state (*) and Find & Replace bar
"""

from __future__ import annotations

import builtins
import keyword
import re
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import QRect, QSize, QStringListModel, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QKeyEvent,
    QPainter,
    QPen,
    QSyntaxHighlighter,
    QTextCharFormat,
    QTextCursor,
    QTextDocument,
)
from PySide6.QtWidgets import (
    QCompleter,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


PYTHON_COMPLETIONS = sorted(
    set(keyword.kwlist)
    | set(dir(builtins))
    | {
        "__name__",
        "__main__",
        "self",
        "cls",
        "Optional",
        "List",
        "Dict",
        "Tuple",
        "Path",
        "dataclass",
        "enumerate",
        "isinstance",
        "range",
        "print",
        "input",
    }
)


class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter tailored exclusively for Python."""

    def __init__(self, document: QTextDocument, theme: str = "dark") -> None:
        super().__init__(document)
        self.theme = theme
        self._build_rules()

    def set_theme(self, theme: str) -> None:
        self.theme = theme
        self._build_rules()
        self.rehighlight()

    def _build_rules(self) -> None:
        dark = self.theme == "dark"

        self.fmt_keyword = self._fmt("#60A5FA" if dark else "#1D4ED8", bold=True)
        self.fmt_builtin = self._fmt("#38BDF8" if dark else "#0369A1")
        self.fmt_def_name = self._fmt("#FBBF24" if dark else "#B45309", bold=True)
        self.fmt_decorator = self._fmt("#C084FC" if dark else "#7E22CE")
        self.fmt_string = self._fmt("#34D399" if dark else "#15803D")
        self.fmt_comment = self._fmt("#6B7280" if dark else "#64748B", italic=True)
        self.fmt_number = self._fmt("#F472B6" if dark else "#BE185D")

        self.rules: list[tuple[re.Pattern[str], QTextCharFormat, int]] = []

        kw_pattern = r"\b(" + "|".join(re.escape(k) for k in keyword.kwlist) + r")\b"
        self.rules.append((re.compile(kw_pattern), self.fmt_keyword, 0))

        bi_names = [b for b in dir(builtins) if not b.startswith("_")]
        bi_pattern = r"\b(" + "|".join(re.escape(b) for b in bi_names) + r")\b"
        self.rules.append((re.compile(bi_pattern), self.fmt_builtin, 0))

        self.rules.append((re.compile(r"\b(?:def|class)\s+([A-Za-z_][A-Za-z0-9_]*)"), self.fmt_def_name, 1))
        self.rules.append((re.compile(r"@[A-Za-z_][A-Za-z0-9_.]*"), self.fmt_decorator, 0))
        self.rules.append((re.compile(r"\b\d+(?:\.\d+)?\b"), self.fmt_number, 0))
        self.rules.append((re.compile(r'"[^"\\]*(?:\\.[^"\\]*)*"'), self.fmt_string, 0))
        self.rules.append((re.compile(r"'[^'\\]*(?:\\.[^'\\]*)*'"), self.fmt_string, 0))
        self.rules.append((re.compile(r"#[^\n]*"), self.fmt_comment, 0))

        self.tri_double = re.compile(r'"""')
        self.tri_single = re.compile(r"'''")

    @staticmethod
    def _fmt(color_hex: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color_hex))
        if bold:
            fmt.setFontWeight(QFont.Weight.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def highlightBlock(self, text: str) -> None:  # noqa: N802
        for pattern, fmt, group in self.rules:
            for match in pattern.finditer(text):
                start, end = match.span(group)
                self.setFormat(start, end - start, fmt)

        self.setCurrentBlockState(0)
        if not self._highlight_multiline(text, self.tri_double, 1):
            self._highlight_multiline(text, self.tri_single, 2)

    def _highlight_multiline(self, text: str, delimiter: re.Pattern[str], state_id: int) -> bool:
        if self.previousBlockState() == state_id:
            start = 0
            add = 0
        else:
            m = delimiter.search(text)
            if not m:
                return False
            start = m.start()
            add = m.end() - m.start()

        while start >= 0:
            end_match = delimiter.search(text, start + add)
            if end_match:
                length = end_match.end() - start
                self.setFormat(start, length, self.fmt_string)
                next_match = delimiter.search(text, end_match.end())
                if next_match:
                    start = next_match.start()
                    add = next_match.end() - next_match.start()
                else:
                    return False
            else:
                self.setCurrentBlockState(state_id)
                self.setFormat(start, len(text) - start, self.fmt_string)
                return True
        return False


class LineNumberArea(QWidget):
    """Left gutter widget displaying line numbers synchronized with PythonCodeEditor."""

    def __init__(self, editor: "PythonCodeEditor") -> None:
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self) -> QSize:  # noqa: N802
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:  # noqa: N802
        self.editor.paint_line_numbers(event)


class PythonCodeEditor(QPlainTextEdit):
    """Custom QPlainTextEdit with line numbers, indent guides, auto-indent, and autocompletion."""

    cursor_moved_pos = Signal(int, int)  # (line, column)

    def __init__(self, theme: str = "dark", font_size: int = 13, tab_width: int = 4) -> None:
        super().__init__()
        self.theme = theme
        self.tab_width = tab_width
        self.file_path: Optional[Path] = None

        font = QFont("Consolas" if hasattr(Qt, "Win") else "JetBrains Mono", font_size)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)

        self.highlighter = PythonHighlighter(self.document(), theme=theme)
        self.line_area = LineNumberArea(self)

        self._completer = QCompleter(PYTHON_COMPLETIONS, self)
        self._completer.setWidget(self)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.activated.connect(self._insert_completion)

        self.blockCountChanged.connect(self._update_line_area_width)
        self.updateRequest.connect(self._update_line_area)
        self.cursorPositionChanged.connect(self._on_cursor_changed)
        self.textChanged.connect(self._refresh_document_completions)

        self._update_line_area_width(0)
        self._highlight_current_line()

    def apply_settings(self, theme: str, font_size: int, tab_width: int) -> None:
        self.theme = theme
        self.tab_width = tab_width
        font = self.font()
        font.setPointSize(font_size)
        self.setFont(font)
        self.highlighter.set_theme(theme)
        self._highlight_current_line()
        self.line_area.update()
        self.viewport().update()

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        return 18 + self.fontMetrics().horizontalAdvance("9") * digits

    def _update_line_area_width(self, _count: int) -> None:
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def _update_line_area(self, rect: QRect, dy: int) -> None:
        if dy:
            self.line_area.scroll(0, dy)
        else:
            self.line_area.update(0, rect.y(), self.line_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self._update_line_area_width(0)

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_area.setGeometry(QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height()))

    def paint_line_numbers(self, event) -> None:
        painter = QPainter(self.line_area)
        bg = QColor("#111827") if self.theme == "dark" else QColor("#F8FAFC")
        fg = QColor("#6B7280") if self.theme == "dark" else QColor("#94A3B8")
        active_fg = QColor("#E5E7EB") if self.theme == "dark" else QColor("#0F172A")

        painter.fillRect(event.rect(), bg)
        current_block_num = self.textCursor().blockNumber()

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                painter.setPen(active_fg if block_number == current_block_num else fg)
                painter.drawText(
                    0,
                    top,
                    self.line_area.width() - 8,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    str(block_number + 1),
                )
            block = block.next()
            top = bottom
            bottom = top + round(self.blockBoundingRect(block).height())
            block_number += 1

    def paintEvent(self, event) -> None:  # noqa: N802
        super().paintEvent(event)
        # Draw subtle vertical indentation guides
        painter = QPainter(self.viewport())
        guide_color = QColor("#1F2937") if self.theme == "dark" else QColor("#E2E8F0")
        painter.setPen(QPen(guide_color, 1))
        space_width = self.fontMetrics().horizontalAdvance(" ")
        indent_px = space_width * self.tab_width

        block = self.firstVisibleBlock()
        top = round(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        height = round(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible():
                text = block.text()
                leading = len(text) - len(text.lstrip(" "))
                levels = leading // self.tab_width
                for level in range(1, levels + 1):
                    x = round(self.contentOffset().x()) + level * indent_px + 2
                    painter.drawLine(x, top, x, top + height)
            block = block.next()
            top += height

    def _on_cursor_changed(self) -> None:
        self._highlight_current_line()
        cursor = self.textCursor()
        self.cursor_moved_pos.emit(cursor.blockNumber() + 1, cursor.positionInBlock() + 1)

    def _highlight_current_line(self) -> None:
        selections = []
        if not self.isReadOnly():
            sel = QTextEdit.ExtraSelection()
            line_color = QColor("#17202C") if self.theme == "dark" else QColor("#EFF6FF")
            sel.format.setBackground(line_color)
            sel.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
            sel.cursor = self.textCursor()
            sel.cursor.clearSelection()
            selections.append(sel)
        self.setExtraSelections(selections)

    def goto_line(self, line_number: int) -> None:
        block = self.document().findBlockByLineNumber(max(0, line_number - 1))
        if block.isValid():
            cursor = QTextCursor(block)
            self.setTextCursor(cursor)
            self.centerCursor()
            self.setFocus()

    def _refresh_document_completions(self) -> None:
        words = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{2,}\b", self.toPlainText()))
        merged = sorted(set(PYTHON_COMPLETIONS) | words)
        model = self._completer.model()
        if isinstance(model, QStringListModel):
            model.setStringList(merged)

    def _insert_completion(self, completion: str) -> None:
        cursor = self.textCursor()
        extra = len(completion) - len(self._completer.completionPrefix())
        cursor.movePosition(QTextCursor.MoveOperation.Left)
        cursor.movePosition(QTextCursor.MoveOperation.EndOfWord)
        cursor.insertText(completion[-extra:] if extra > 0 else "")
        self.setTextCursor(cursor)

    def _word_under_cursor(self) -> str:
        cursor = self.textCursor()
        cursor.select(QTextCursor.SelectionType.WordUnderCursor)
        return cursor.selectedText()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802
        if self._completer.popup().isVisible():
            if event.key() in (
                Qt.Key.Key_Enter,
                Qt.Key.Key_Return,
                Qt.Key.Key_Escape,
                Qt.Key.Key_Tab,
                Qt.Key.Key_Backtab,
            ):
                event.ignore()
                return

        if event.key() == Qt.Key.Key_Tab:
            self.insertPlainText(" " * self.tab_width)
            return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cursor = self.textCursor()
            line_text = cursor.block().text()
            indent = len(line_text) - len(line_text.lstrip(" "))
            extra_indent = self.tab_width if line_text.rstrip().endswith(":") else 0
            super().keyPressEvent(event)
            self.insertPlainText(" " * (indent + extra_indent))
            return

        pairs = {"(": ")", "[": "]", "{": "}", '"': '"', "'": "'"}
        if event.text() in pairs and not self.textCursor().hasSelection():
            closing = pairs[event.text()]
            super().keyPressEvent(event)
            self.insertPlainText(closing)
            cursor = self.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Left)
            self.setTextCursor(cursor)
            return

        super().keyPressEvent(event)

        prefix = self._word_under_cursor()
        if len(prefix) >= 2 and (event.text().isalnum() or event.text() == "_"):
            self._completer.setCompletionPrefix(prefix)
            if self._completer.completionCount() > 0:
                cr = self.cursorRect()
                cr.setWidth(
                    self._completer.popup().sizeHintForColumn(0)
                    + self._completer.popup().verticalScrollBar().sizeHint().width()
                )
                self._completer.complete(cr)
                return
        self._completer.popup().hide()


class FindReplaceBar(QFrame):
    """Collapsible inline Find and Replace bar for the active editor."""

    def __init__(self, get_editor: Callable[[], Optional[PythonCodeEditor]], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("FindReplaceBar")
        self.get_editor = get_editor
        self.hide()

        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(6)

        self.find_input = QLineEdit()
        self.find_input.setPlaceholderText("Find...")
        self.replace_input = QLineEdit()
        self.replace_input.setPlaceholderText("Replace...")

        btn_next = QPushButton("Next")
        btn_prev = QPushButton("Prev")
        btn_replace = QPushButton("Replace")
        btn_replace_all = QPushButton("Replace All")
        btn_close = QPushButton("Close")

        for b in (btn_next, btn_prev, btn_replace, btn_replace_all, btn_close):
            b.setProperty("class", "ToolbarBtn")

        layout.addWidget(QLabel("Find:"))
        layout.addWidget(self.find_input)
        layout.addWidget(btn_prev)
        layout.addWidget(btn_next)
        layout.addWidget(QLabel("Replace:"))
        layout.addWidget(self.replace_input)
        layout.addWidget(btn_replace)
        layout.addWidget(btn_replace_all)
        layout.addWidget(btn_close)

        self.find_input.returnPressed.connect(self.find_next)
        btn_next.clicked.connect(self.find_next)
        btn_prev.clicked.connect(self.find_previous)
        btn_replace.clicked.connect(self.replace_one)
        btn_replace_all.clicked.connect(self.replace_all)
        btn_close.clicked.connect(self.hide)

    def open_bar(self) -> None:
        self.show()
        self.find_input.setFocus()
        self.find_input.selectAll()

    def find_next(self) -> None:
        ed = self.get_editor()
        term = self.find_input.text()
        if ed and term:
            if not ed.find(term):
                cursor = ed.textCursor()
                cursor.movePosition(QTextCursor.MoveOperation.Start)
                ed.setTextCursor(cursor)
                ed.find(term)

    def find_previous(self) -> None:
        ed = self.get_editor()
        term = self.find_input.text()
        if ed and term:
            ed.find(term, QTextDocument.FindFlag.FindBackward)

    def replace_one(self) -> None:
        ed = self.get_editor()
        term = self.find_input.text()
        if ed and term:
            cursor = ed.textCursor()
            if cursor.hasSelection() and cursor.selectedText() == term:
                cursor.insertText(self.replace_input.text())
            self.find_next()

    def replace_all(self) -> None:
        ed = self.get_editor()
        term = self.find_input.text()
        if ed and term:
            content = ed.toPlainText().replace(term, self.replace_input.text())
            ed.setPlainText(content)


class EditorArea(QWidget):
    """Tabbed code editor container managing multiple open Python files."""

    active_editor_changed = Signal(object)  # Optional[PythonCodeEditor]
    editor_text_changed = Signal(object)  # PythonCodeEditor
    cursor_changed = Signal(int, int)
    tab_close_requested = Signal(int)

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.theme = "dark"
        self.font_size = 13
        self.tab_width = 4

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self.find_bar = FindReplaceBar(self.current_editor, self)
        layout.addWidget(self.find_bar)

        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.setMovable(True)
        self.tabs.currentChanged.connect(self._on_current_tab_changed)
        self.tabs.tabCloseRequested.connect(self.tab_close_requested.emit)
        layout.addWidget(self.tabs)

    def current_editor(self) -> Optional[PythonCodeEditor]:
        widget = self.tabs.currentWidget()
        return widget if isinstance(widget, PythonCodeEditor) else None

    def open_tab(self, file_path: Optional[Path], content: str) -> PythonCodeEditor:
        if file_path is not None:
            for idx in range(self.tabs.count()):
                ed = self.tabs.widget(idx)
                if isinstance(ed, PythonCodeEditor) and ed.file_path == file_path:
                    self.tabs.setCurrentIndex(idx)
                    return ed

        editor = PythonCodeEditor(
            theme=self.theme,
            font_size=self.font_size,
            tab_width=self.tab_width,
        )
        editor.file_path = file_path
        editor.setPlainText(content)
        editor.document().setModified(False)

        title = file_path.name if file_path else "untitled.py"
        idx = self.tabs.addTab(editor, title)
        self.tabs.setCurrentIndex(idx)

        editor.modificationChanged.connect(lambda _mod, e=editor: self._update_tab_title(e))
        editor.cursor_moved_pos.connect(self.cursor_changed.emit)
        editor.textChanged.connect(lambda e=editor: self.editor_text_changed.emit(e))
        return editor

    def _update_tab_title(self, editor: PythonCodeEditor) -> None:
        idx = self.tabs.indexOf(editor)
        if idx < 0:
            return
        name = editor.file_path.name if editor.file_path else "untitled.py"
        if editor.document().isModified():
            self.tabs.setTabText(idx, f"● {name}")
        else:
            self.tabs.setTabText(idx, name)

    def mark_saved(self, editor: PythonCodeEditor, file_path: Path) -> None:
        editor.file_path = file_path
        editor.document().setModified(False)
        self._update_tab_title(editor)

    def close_tab(self, index: int) -> None:
        widget = self.tabs.widget(index)
        self.tabs.removeTab(index)
        if widget:
            widget.deleteLater()

    def apply_settings(self, theme: str, font_size: int, tab_width: int) -> None:
        self.theme = theme
        self.font_size = font_size
        self.tab_width = tab_width
        for idx in range(self.tabs.count()):
            ed = self.tabs.widget(idx)
            if isinstance(ed, PythonCodeEditor):
                ed.apply_settings(theme, font_size, tab_width)

    def _on_current_tab_changed(self, _index: int) -> None:
        ed = self.current_editor()
        self.active_editor_changed.emit(ed)
        if ed:
            cursor = ed.textCursor()
            self.cursor_changed.emit(cursor.blockNumber() + 1, cursor.positionInBlock() + 1)
