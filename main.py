"""
Rathin
PyCode Studio: a Python-only desktop code editor.
Uses only Python standard-library modules.
Run with: python pycode_studio.py
"""

import keyword
import os
import re
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import filedialog, messagebox


class PyCodeStudio:
    BG = "#1e1e1e"
    PANEL = "#252526"
    FG = "#d4d4d4"
    ACCENT = "#007acc"

    def __init__(self, root):
        self.root = root
        self.root.title("Untitled.py - PyCode Studio")
        self.root.geometry("1050x700")
        self.root.minsize(750, 500)
        self.root.configure(bg=self.BG)

        self.current_file = None
        self.process = None
        self.closing = False
        self.highlight_job = None

        self.make_menu()
        self.make_toolbar()
        self.make_editor()
        self.make_output()

        self.root.bind("<Control-n>", lambda e: self.new_file())
        self.root.bind("<Control-o>", lambda e: self.open_file())
        self.root.bind("<Control-s>", lambda e: self.save_file())
        self.root.bind("<F5>", lambda e: self.run_code())
        self.root.bind("<Shift-F5>", lambda e: self.stop_code())
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)
        self.update_line_numbers()

    def make_menu(self):
        menu = tk.Menu(self.root, bg=self.PANEL, fg=self.FG)
        file_menu = tk.Menu(menu, tearoff=0, bg=self.PANEL, fg=self.FG)
        file_menu.add_command(label="New", accelerator="Ctrl+N", command=self.new_file)
        file_menu.add_command(label="Open...", accelerator="Ctrl+O", command=self.open_file)
        file_menu.add_command(label="Save", accelerator="Ctrl+S", command=self.save_file)
        file_menu.add_command(label="Save As...", command=self.save_as)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.close_app)
        menu.add_cascade(label="File", menu=file_menu)

        run_menu = tk.Menu(menu, tearoff=0, bg=self.PANEL, fg=self.FG)
        run_menu.add_command(label="Run Python File", accelerator="F5", command=self.run_code)
        run_menu.add_command(label="Stop", accelerator="Shift+F5", command=self.stop_code)
        menu.add_cascade(label="Run", menu=run_menu)
        self.root.config(menu=menu)

    def make_toolbar(self):
        bar = tk.Frame(self.root, bg=self.PANEL, height=46)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        tk.Label(bar, text="  PyCode Studio", bg=self.PANEL, fg="white",
                 font=("Segoe UI", 12, "bold")).pack(side="left", padx=(4, 14))

        self.add_button(bar, "New", self.new_file)
        self.add_button(bar, "Open", self.open_file)
        self.add_button(bar, "Save", self.save_file)
        self.add_button(bar, "▶ Run", self.run_code, accent=True)
        self.add_button(bar, "■ Stop", self.stop_code)
        self.file_label = tk.Label(bar, text="Untitled.py", bg=self.PANEL,
                                   fg="#aaaaaa", font=("Segoe UI", 9))
        self.file_label.pack(side="right", padx=14)

    def add_button(self, parent, text, command, accent=False):
        tk.Button(parent, text=text, command=command, relief="flat",
                  bg=self.ACCENT if accent else "#383838", fg="white",
                  activebackground="#1683c7", activeforeground="white",
                  padx=11, pady=4, cursor="hand2",
                  font=("Segoe UI", 9)).pack(side="left", padx=3, pady=7)

    def make_editor(self):
        area = tk.Frame(self.root, bg=self.BG)
        area.pack(fill="both", expand=True)

        self.gutter = tk.Text(area, width=4, padx=8, takefocus=0, border=0,
                              bg="#252526", fg="#858585", state="disabled",
                              font=("Consolas", 11), wrap="none")
        self.gutter.pack(side="left", fill="y")

        self.editor = tk.Text(area, undo=True, wrap="none", border=0,
                              bg=self.BG, fg=self.FG, insertbackground="white",
                              selectbackground="#264f78", font=("Consolas", 11),
                              padx=10, pady=8, tabs=("4c",))
        self.editor.pack(side="left", fill="both", expand=True)

        self.vbar = tk.Scrollbar(area, orient="vertical", command=self.scroll_editor)
        self.vbar.pack(side="right", fill="y")
        self.editor.configure(yscrollcommand=self.editor_scrolled)

        hbar = tk.Scrollbar(self.root, orient="horizontal", command=self.editor.xview)
        hbar.pack(fill="x")
        self.editor.configure(xscrollcommand=hbar.set)

        self.editor.tag_configure("keyword", foreground="#c586c0")
        self.editor.tag_configure("string", foreground="#ce9178")
        self.editor.tag_configure("comment", foreground="#6a9955")
        self.editor.tag_configure("number", foreground="#b5cea8")
        self.editor.tag_configure("builtin", foreground="#4ec9b0")
        self.editor.tag_configure("function", foreground="#dcdcaa")

        self.editor.bind("<<Modified>>", self.modified)
        self.editor.bind("<KeyRelease>", self.schedule_highlight)
        self.editor.bind("<Tab>", self.insert_tab)
        self.editor.bind("<Return>", self.auto_indent)
        self.editor.bind("<MouseWheel>", self.update_line_numbers)

    def make_output(self):
        panel = tk.Frame(self.root, bg=self.PANEL, height=175)
        panel.pack(side="bottom", fill="x")
        panel.pack_propagate(False)

        header = tk.Frame(panel, bg=self.PANEL)
        header.pack(fill="x")
        tk.Label(header, text="  OUTPUT / TERMINAL", bg=self.PANEL,
                 fg="#4ec9b0", font=("Segoe UI", 9, "bold")).pack(side="left", pady=7)
        tk.Button(header, text="Clear", command=self.clear_output, relief="flat",
                  bg="#383838", fg=self.FG, activebackground="#444444",
                  activeforeground="white", padx=10).pack(side="right", padx=8, pady=3)

        self.output = tk.Text(panel, height=7, state="disabled", wrap="word",
                              bg="#111111", fg=self.FG, font=("Consolas", 10),
                              border=0, padx=10, pady=6)
        self.output.pack(fill="both", expand=True, padx=5, pady=(0, 5))
        self.output.tag_configure("error", foreground="#f48771")
        self.output.tag_configure("success", foreground="#4ec9b0")

        input_bar = tk.Frame(panel, bg=self.PANEL)
        input_bar.pack(fill="x", padx=5, pady=(0, 5))
        tk.Label(input_bar, text="INPUT >", bg=self.PANEL, fg="#4ec9b0",
                 font=("Segoe UI", 9, "bold")).pack(side="left", padx=(5, 8))
        self.input_entry = tk.Entry(input_bar, bg="#111111", fg=self.FG,
                                    insertbackground="white", relief="flat",
                                    font=("Consolas", 10))
        self.input_entry.pack(side="left", fill="x", expand=True, ipady=5)
        self.input_entry.bind("<Return>", self.send_input)
        tk.Button(input_bar, text="Send", command=self.send_input,
                  relief="flat", bg=self.ACCENT, fg="white",
                  activebackground="#1683c7", activeforeground="white",
                  padx=12, cursor="hand2").pack(side="left", padx=(6, 2))

    def scroll_editor(self, *args):
        self.editor.yview(*args)
        self.gutter.yview(*args)

    def editor_scrolled(self, first, last):
        self.vbar.set(first, last)
        self.gutter.yview_moveto(first)
        self.update_line_numbers()

    def update_line_numbers(self, event=None):
        if not hasattr(self, "editor"):
            return
        count = int(self.editor.index("end-1c").split(".")[0])
        lines = "\n".join(str(n) for n in range(1, count + 1))
        self.gutter.configure(state="normal")
        self.gutter.delete("1.0", "end")
        self.gutter.insert("1.0", lines)
        self.gutter.configure(state="disabled")
        self.gutter.yview_moveto(self.editor.yview()[0])

    def modified(self, event=None):
        if self.editor.edit_modified():
            self.editor.edit_modified(False)
            self.update_title()

    def update_title(self):
        name = os.path.basename(self.current_file) if self.current_file else "Untitled.py"
        self.file_label.configure(text=name)
        self.root.title(f"{name} - PyCode Studio")

    def schedule_highlight(self, event=None):
        if self.highlight_job:
            self.root.after_cancel(self.highlight_job)
        self.highlight_job = self.root.after(180, self.highlight_syntax)
        self.update_line_numbers()

    def highlight_syntax(self):
        self.highlight_job = None
        source = self.editor.get("1.0", "end-1c")
        for tag in ("keyword", "string", "comment", "number", "builtin", "function"):
            self.editor.tag_remove(tag, "1.0", "end")

        patterns = [
            ("comment", r"#[^\n]*"),
            ("string", r'"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'|"""[\s\S]*?"""|\'\'\'[\s\S]*?\'\'\''),
            ("number", r"\b\d+(?:\.\d+)?\b"),
            ("keyword", r"\b(?:" + "|".join(map(re.escape, keyword.kwlist)) + r")\b"),
            ("builtin", r"\b(?:print|input|len|range|int|float|str|list|dict|set|tuple|sum|min|max|abs|open|type|enumerate|zip)\b"),
            ("function", r"\b[A-Za-z_]\w*(?=\s*\()"),
        ]
        for tag, pattern in patterns:
            for match in re.finditer(pattern, source):
                start = f"1.0 + {match.start()} chars"
                end = f"1.0 + {match.end()} chars"
                self.editor.tag_add(tag, start, end)

    def insert_tab(self, event=None):
        self.editor.insert("insert", "    ")
        return "break"

    def auto_indent(self, event=None):
        line = self.editor.get("insert linestart", "insert")
        indent = re.match(r"[ \t]*", line).group(0)
        if line.rstrip().endswith(":"):
            indent += "    "
        self.editor.insert("insert", "\n" + indent)
        return "break"

    def ask_save_changes(self):
        if not self.editor.edit_modified():
            return True
        answer = messagebox.askyesnocancel("Unsaved changes",
                                           "Save changes before continuing?")
        if answer is None:
            return False
        if answer:
            return bool(self.save_file())
        return True

    def new_file(self):
        if not self.ask_save_changes():
            return
        self.editor.delete("1.0", "end")
        self.current_file = None
        self.editor.edit_modified(False)
        self.update_title()
        self.update_line_numbers()

    def open_file(self):
        if not self.ask_save_changes():
            return
        path = filedialog.askopenfilename(
            title="Open Python file",
            filetypes=[("Python files", "*.py")]
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as file:
                contents = file.read()
            self.editor.delete("1.0", "end")
            self.editor.insert("1.0", contents)
            self.current_file = path
            self.editor.edit_modified(False)
            self.update_title()
            self.highlight_syntax()
            self.update_line_numbers()
        except (OSError, UnicodeError) as error:
            messagebox.showerror("Open error", str(error))

    def save_file(self):
        if self.current_file is None:
            return self.save_as()
        try:
            with open(self.current_file, "w", encoding="utf-8") as file:
                file.write(self.editor.get("1.0", "end-1c"))
            self.editor.edit_modified(False)
            self.update_title()
            self.write_output(f"Saved: {self.current_file}\n", "success")
            return True
        except OSError as error:
            messagebox.showerror("Save error", str(error))
            return False

    def save_as(self):
        path = filedialog.asksaveasfilename(
            title="Save Python file", defaultextension=".py",
            filetypes=[("Python files", "*.py")]
        )
        if not path:
            return False
        if not path.lower().endswith(".py"):
            path += ".py"
        self.current_file = path
        return self.save_file()

    def write_output(self, text, tag=None):
        self.output.configure(state="normal")
        self.output.insert("end", text, tag or ())
        self.output.see("end")
        self.output.configure(state="disabled")

    def clear_output(self):
        self.output.configure(state="normal")
        self.output.delete("1.0", "end")
        self.output.configure(state="disabled")

    def send_input(self, event=None):
        process = self.process
        if process is None or process.poll() is not None or process.stdin is None:
            self.write_output("\nNo running program is waiting for input. Click Run first.\n", "error")
            return "break"

        value = self.input_entry.get()
        self.input_entry.delete(0, "end")
        try:
            process.stdin.write(value + "\n")
            process.stdin.flush()
            self.write_output(value + "\n")
        except (BrokenPipeError, OSError, ValueError):
            self.write_output("\nCould not send input: the program may have ended.\n", "error")
        self.input_entry.focus_set()
        return "break"

    def run_code(self):
        if self.process and self.process.poll() is None:
            messagebox.showinfo("Program running", "Stop the current program first.")
            return
        if not self.save_file() or not self.current_file:
            return

        self.clear_output()
        self.write_output(f"Running {os.path.basename(self.current_file)}...\n\n", "success")
        self.input_entry.delete(0, "end")

        def execute():
            process = None
            try:
                process = subprocess.Popen(
                    [sys.executable, "-u", self.current_file],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    cwd=os.path.dirname(self.current_file) or None,
                    bufsize=1
                )
                self.process = process

                # Display prompts immediately, even when they have no newline.
                while True:
                    char = process.stdout.read(1)
                    if char == "":
                        break
                    if not self.closing:
                        self.root.after(0, self.write_output, char)

                code = process.wait()
                if not self.closing:
                    if code == 0:
                        self.root.after(0, self.write_output,
                                        "\nProcess finished successfully.\n", "success")
                    else:
                        self.root.after(0, self.write_output,
                                        f"\nProcess exited with code {code}.\n", "error")
            except Exception as error:
                if not self.closing:
                    self.root.after(0, self.write_output,
                                    f"\nExecution error: {error}\n", "error")
            finally:
                if self.process is process:
                    self.process = None

        threading.Thread(target=execute, daemon=True).start()

    def stop_code(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.write_output("\nProgram stopped by user.\n", "error")
        else:
            self.write_output("No program is currently running.\n")

    def close_app(self):
        if not self.ask_save_changes():
            return
        self.closing = True
        if self.process and self.process.poll() is None:
            self.process.terminate()
        self.root.destroy()


def main():
    root = tk.Tk()
    PyCodeStudio(root)
    root.mainloop()


if __name__ == "__main__":
    main()
