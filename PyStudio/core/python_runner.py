"""
Subprocess-based Python execution engine for PyStudio.
Executes user scripts in an isolated Python process via QProcess so the GUI
stays responsive, supports interactive stdin for input(), captures stdout/stderr,
and safely terminates infinite loops on Windows 10/11, macOS, and Linux.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QProcess, QProcessEnvironment, QTimer, Signal


TRACEBACK_LINE_RE = re.compile(r'File "([^"]+)", line (\d+)')


@dataclass
class RuntimeErrorInfo:
    """Structured representation of a Python runtime exception."""

    file_path: str
    line: int
    error_type: str
    message: str
    raw_traceback: str


def parse_traceback(stderr_text: str) -> Optional[RuntimeErrorInfo]:
    """Extract the final file, line number, and exception summary from a Python traceback."""
    if not stderr_text.strip():
        return None

    matches = TRACEBACK_LINE_RE.findall(stderr_text)
    file_path = ""
    line_num = 1
    if matches:
        file_path, line_str = matches[-1]
        line_num = int(line_str)

    lines = [line.strip() for line in stderr_text.strip().splitlines() if line.strip()]
    summary = lines[-1] if lines else "Runtime Error"
    if ":" in summary:
        err_type, err_msg = summary.split(":", 1)
    else:
        err_type, err_msg = summary, ""

    return RuntimeErrorInfo(
        file_path=file_path,
        line=line_num,
        error_type=err_type.strip(),
        message=err_msg.strip(),
        raw_traceback=stderr_text.strip(),
    )


class PythonRunner(QObject):
    """Runs Python scripts in a dedicated non-blocking QProcess."""

    started = Signal(str)
    stdout_received = Signal(str)
    stderr_received = Signal(str)
    finished = Signal(int, bool)  # (exit_code, was_stopped)
    runtime_error_detected = Signal(object)  # RuntimeErrorInfo

    def __init__(self, parent: Optional[QObject] = None) -> None:
        super().__init__(parent)
        self._process: Optional[QProcess] = None
        self._was_stopped: bool = False
        self._stderr_buffer: list[str] = []
        self._python_executable: str = sys.executable

    @property
    def python_executable(self) -> str:
        return self._python_executable

    def set_python_executable(self, executable: str) -> None:
        if executable.strip():
            self._python_executable = executable.strip()

    def is_running(self) -> bool:
        return self._process is not None and self._process.state() != QProcess.ProcessState.NotRunning

    def run_script(self, script_path: Path, working_dir: Optional[Path] = None) -> None:
        """Launch the script in an unbuffered (-u) Python subprocess."""
        if self.is_running():
            return

        self._was_stopped = False
        self._stderr_buffer.clear()

        proc = QProcess(self)
        self._process = proc

        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONUNBUFFERED", "1")
        env.insert("PYTHONIOENCODING", "utf-8")
        proc.setProcessEnvironment(env)

        cwd = str((working_dir or script_path.parent).resolve())
        proc.setWorkingDirectory(cwd)

        proc.readyReadStandardOutput.connect(self._on_stdout)
        proc.readyReadStandardError.connect(self._on_stderr)
        proc.finished.connect(self._on_finished)
        proc.errorOccurred.connect(self._on_process_error)

        self.started.emit(str(script_path))
        proc.start(self._python_executable, ["-u", str(script_path)])

    def send_input(self, text: str) -> None:
        """Write a line of interactive stdin to the running Python process."""
        if self._process and self.is_running():
            payload = (text + "\n").encode("utf-8")
            self._process.write(payload)

    def stop(self) -> None:
        """Terminate the running process gracefully, then force-kill if needed."""
        if not self._process or not self.is_running():
            return

        self._was_stopped = True
        self._process.terminate()

        proc_ref = self._process
        QTimer.singleShot(1500, lambda: self._force_kill_if_alive(proc_ref))

    def _force_kill_if_alive(self, proc: QProcess) -> None:
        if proc and proc.state() != QProcess.ProcessState.NotRunning:
            proc.kill()

    def _on_stdout(self) -> None:
        if not self._process:
            return
        data = bytes(self._process.readAllStandardOutput()).decode("utf-8", errors="replace")
        if data:
            self.stdout_received.emit(data)

    def _on_stderr(self) -> None:
        if not self._process:
            return
        data = bytes(self._process.readAllStandardError()).decode("utf-8", errors="replace")
        if data:
            self._stderr_buffer.append(data)
            self.stderr_received.emit(data)

    def _on_finished(self, exit_code: int, _exit_status: QProcess.ExitStatus) -> None:
        self._on_stdout()
        self._on_stderr()

        full_stderr = "".join(self._stderr_buffer)
        if full_stderr.strip() and not self._was_stopped:
            parsed = parse_traceback(full_stderr)
            if parsed:
                self.runtime_error_detected.emit(parsed)

        self._process = None
        self.finished.emit(exit_code, self._was_stopped)

    def _on_process_error(self, error: QProcess.ProcessError) -> None:
        if error == QProcess.ProcessError.FailedToStart:
            self.stderr_received.emit(
                f"Failed to start Python interpreter: {self._python_executable}\n"
            )
            self._process = None
            self.finished.emit(1, False)
