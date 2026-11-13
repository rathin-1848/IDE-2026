"""
File management utilities for PyStudio using pathlib.
Handles workspace scanning, reading/writing UTF-8 Python files, and file operations.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional


IGNORED_DIRS = {"__pycache__", ".git", ".venv", "venv", ".mypy_cache", ".pytest_cache"}


@dataclass
class WorkspaceItem:
    """Represents a file or directory inside the active workspace."""

    name: str
    path: Path
    is_dir: bool
    children: List["WorkspaceItem"]


class FileManager:
    """Manages reading, writing, creating, and listing Python files in a workspace."""

    def __init__(self, workspace_root: Optional[Path] = None) -> None:
        self.workspace_root: Path = (workspace_root or Path.cwd()).resolve()

    def set_workspace(self, folder_path: Path) -> None:
        """Set the active project folder."""
        self.workspace_root = folder_path.resolve()

    def list_tree(self, directory: Optional[Path] = None) -> List[WorkspaceItem]:
        """Recursively build a sorted tree of folders and Python files."""
        target = (directory or self.workspace_root).resolve()
        if not target.exists() or not target.is_dir():
            return []

        items: List[WorkspaceItem] = []
        entries = sorted(target.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))

        for entry in entries:
            if entry.name in IGNORED_DIRS or entry.name.startswith("."):
                continue
            if entry.is_dir():
                children = self.list_tree(entry)
                items.append(
                    WorkspaceItem(
                        name=entry.name,
                        path=entry,
                        is_dir=True,
                        children=children,
                    )
                )
            elif entry.suffix.lower() in {".py", ".pyw", ".txt", ".md"}:
                items.append(
                    WorkspaceItem(
                        name=entry.name,
                        path=entry,
                        is_dir=False,
                        children=[],
                    )
                )
        return items

    def read_file(self, file_path: Path) -> str:
        """Read a text/Python file safely using UTF-8 encoding."""
        return file_path.read_text(encoding="utf-8")

    def write_file(self, file_path: Path, content: str) -> None:
        """Write content to disk using UTF-8 encoding, creating parent folders if needed."""
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8", newline="\n")

    def create_python_file(self, directory: Path, filename: str) -> Path:
        """Create a new Python file inside the chosen directory."""
        clean_name = filename.strip()
        if not clean_name.endswith(".py"):
            clean_name = f"{clean_name}.py"

        target = (directory / clean_name).resolve()
        if target.exists():
            raise FileExistsError(f"File already exists: {target.name}")

        template = f'"""{clean_name} - Created with PyStudio."""\n\n\ndef main() -> None:\n    print("Hello from {clean_name}!")\n\n\nif __name__ == "__main__":\n    main()\n'
        self.write_file(target, template)
        return target

    def create_folder(self, directory: Path, folder_name: str) -> Path:
        """Create a new subfolder inside the workspace."""
        target = (directory / folder_name.strip()).resolve()
        target.mkdir(parents=True, exist_ok=True)
        return target

    def delete_path(self, target: Path) -> None:
        """Delete a file or empty directory safely."""
        if target.is_file():
            target.unlink()
        elif target.is_dir():
            for child in target.iterdir():
                self.delete_path(child)
            target.rmdir()

    def search_in_workspace(self, query: str) -> List[tuple[Path, int, str]]:
        """Search all Python files in workspace for a case-insensitive text query."""
        results: List[tuple[Path, int, str]] = []
        needle = query.strip().lower()
        if not needle or not self.workspace_root.exists():
            return results

        for py_file in sorted(self.workspace_root.rglob("*.py")):
            if any(part in IGNORED_DIRS for part in py_file.parts):
                continue
            try:
                lines = py_file.read_text(encoding="utf-8").splitlines()
            except OSError:
                continue
            for idx, line in enumerate(lines, start=1):
                if needle in line.lower():
                    results.append((py_file, idx, line.strip()))
        return results
