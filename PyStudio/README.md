# PyStudio – Professional Python Desktop IDE

PyStudio is a lightweight, modern desktop Integrated Development Environment built exclusively for Python using **Python 3.10+** and **PySide6**.

## Windows 10 & Windows 11 Installation

1. Install **Python 3.10+** from [python.org](https://www.python.org/downloads/) (check **"Add Python to PATH"** during setup).
2. Open **PowerShell** or **Command Prompt** inside the `PyStudio/` folder:
   ```powershell
   python -m venv .venv
   .venv\Scripts\activate
   pip install -r requirements.txt
   python main.py
   ```

## Module Architecture

- `main.py` — Initializes `QApplication`, sets app metadata, and launches `MainWindow`.
- `core/file_manager.py` — Uses `pathlib.Path` to scan project directories, read/write UTF-8 `.py` files, create files/folders, and search across the workspace.
- `core/python_runner.py` — Executes scripts in a separate unbuffered `QProcess` (`python -u`) so the UI never freezes, streams `stdout`/`stderr`, forwards interactive `stdin` for `input()`, terminates infinite loops safely, and parses tracebacks.
- `core/problems_analyzer.py` — Uses Python's built-in `ast.parse` to detect syntax and indentation errors without running user code.
- `ui/main_window.py` — Orchestrates the toolbar, activity bar, resizable `QSplitter` panels, keyboard shortcuts, theme switching, and save confirmation dialogs.
- `ui/toolbar.py` — Top command strip with New, Open, Save, Run (`F5`), Stop (`Shift+F5`), and Settings.
- `ui/sidebar.py` — Activity Bar (Explorer, Search, Settings) and File Explorer tree / workspace search list.
- `ui/editor.py` — Multi-tab `PythonCodeEditor` with syntax highlighting, line numbers, indentation guides, auto-indent, bracket pairing, `QCompleter` autocompletion, and Find & Replace.
- `ui/output_panel.py` — Bottom panel with Output, Interactive Terminal (`stdin`), Problems, and Runtime Errors (with click-to-jump-to-line).
- `ui/status_bar.py` — Shows active file, `Ln/Col`, `UTF-8`, Python version, and execution status.
- `ui/settings_dialog.py` — Configures Dark/Light theme, font size, tab width, and Python interpreter path.
- `resources/styles_dark.qss` & `resources/styles_light.qss` — Qt Style Sheets for the Dark Professional and Light themes.
