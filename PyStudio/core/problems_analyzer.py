"""
Python syntax and static problem analyzer for PyStudio.
Uses Python's built-in `ast` module to detect SyntaxError and IndentationError
without executing user code.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from typing import List


@dataclass
class CodeProblem:
    """Represents a syntax or structural issue detected in a Python source file."""

    file_name: str
    line: int
    column: int
    severity: str  # "Error" | "Warning"
    message: str


def analyze_python_source(source: str, file_name: str = "<untitled>") -> List[CodeProblem]:
    """Parse Python source with `ast.parse` and return structured problems."""
    problems: List[CodeProblem] = []
    try:
        ast.parse(source, filename=file_name)
    except SyntaxError as exc:
        line = exc.lineno or 1
        col = exc.offset or 1
        msg = exc.msg or "Invalid Python syntax"
        problems.append(
            CodeProblem(
                file_name=file_name,
                line=line,
                column=col,
                severity="Error",
                message=msg,
            )
        )
    except Exception as exc:  # noqa: BLE001
        problems.append(
            CodeProblem(
                file_name=file_name,
                line=1,
                column=1,
                severity="Error",
                message=str(exc),
            )
        )
    return problems
