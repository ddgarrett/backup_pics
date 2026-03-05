"""
Menu GUI for backup_pics on Raspberry Pi 5.

- Starts main.py (backup) automatically when the menu is opened.
- Option 1: Start/Stop the backup process (main.py).
- Option 2: Start/Stop the Pic Quality Review process (placeholder).
- Option 3: Exit — stop all processes and close the program.

Prereq: pip install sv-ttk
"""
import os
import signal
import subprocess
import sys
import tkinter as tk
from tkinter import ttk, messagebox

# Optional modern theme (Raspberry Pi: pip install sv-ttk)
try:
    import sv_ttk
    HAS_SV_TTK = True
except ImportError:
    HAS_SV_TTK = False

# Project root = directory containing this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
MAIN_PY = os.path.join(SCRIPT_DIR, "main.py")
PIC_QUALITY_SCRIPT = os.path.join(SCRIPT_DIR, "pic_quality_review.py")


def _kill_process_and_children(proc):
    """Terminate process and its process group (so child processes like lxterminal are also stopped)."""
    if proc is None or proc.poll() is not None:
        return
    try:
        # Process was started with start_new_session=True, so we can kill the group
        os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
    except (ProcessLookupError, OSError):
        try:
            proc.terminate()
        except OSError:
            pass


class BackupMenuApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.backup_process = None
        self.pic_review_process = None
        self._poll_id = None

        self.title("Backup Pics – Menu")
        self.geometry("420x280")
        self.minsize(320, 220)

        if HAS_SV_TTK:
            sv_ttk.set_theme("light")

        main_frame = ttk.Frame(self, padding=24)
        main_frame.pack(fill="both", expand=True)

        ttk.Label(
            main_frame,
            text="Backup Pics",
            font=("Helvetica", 18, "bold"),
        ).pack(pady=(0, 20))

        # Option 1: Start/Stop Backup
        self.btn_backup = ttk.Button(
            main_frame,
            text="Stop Backup",
            command=self._toggle_backup,
            width=28,
        )
        self.btn_backup.pack(pady=8, fill="x")

        # Option 2: Start/Stop Pic Quality Review
        self.btn_pic_review = ttk.Button(
            main_frame,
            text="Start Pic Quality Review",
            command=self._toggle_pic_review,
            width=28,
        )
        self.btn_pic_review.pack(pady=8, fill="x")

        # Option 3: Exit
        ttk.Button(
            main_frame,
            text="Exit",
            command=self._exit_app,
            width=28,
        ).pack(pady=8, fill="x")

        self.status_label = ttk.Label(main_frame, text="Starting backup…", relief="flat")
        self.status_label.pack(side="bottom", fill="x", pady=(16, 0))

        self.protocol("WM_DELETE_WINDOW", self._exit_app)

        # Start backup process on launch
        self.after(100, self._start_backup)
        self._start_poll()

    def _start_poll(self):
        """Periodically update button labels if a process exits on its own."""
        self._update_labels_from_processes()
        self._poll_id = self.after(1000, self._start_poll)

    def _update_labels_from_processes(self):
        """Refresh Backup and Pic Review button text from actual process state."""
        if self.backup_process is not None and self.backup_process.poll() is not None:
            self.backup_process = None
            self.btn_backup.config(text="Start Backup")
            self.status_label.config(text="Backup stopped.")
        if self.pic_review_process is not None and self.pic_review_process.poll() is not None:
            self.pic_review_process = None
            self.btn_pic_review.config(text="Start Pic Quality Review")
            self.status_label.config(text="Pic Quality Review stopped.")

    def _toggle_backup(self):
        if self.backup_process is not None and self.backup_process.poll() is None:
            self._stop_backup()
        else:
            self._start_backup()

    def _start_backup(self):
        if self.backup_process is not None and self.backup_process.poll() is None:
            self.status_label.config(text="Backup already running.")
            return
        try:
            self.backup_process = subprocess.Popen(
                [sys.executable, MAIN_PY],
                cwd=SCRIPT_DIR,
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.btn_backup.config(text="Stop Backup")
            self.status_label.config(text="Backup running.")
        except FileNotFoundError:
            self.status_label.config(text="Error: main.py not found.")
            messagebox.showerror("Error", f"Could not find:\n{MAIN_PY}")
        except Exception as e:
            self.status_label.config(text="Error starting backup.")
            messagebox.showerror("Error", f"Failed to start backup:\n{e}")

    def _stop_backup(self):
        if self.backup_process is None or self.backup_process.poll() is not None:
            self.backup_process = None
            self.btn_backup.config(text="Start Backup")
            return
        _kill_process_and_children(self.backup_process)
        self.backup_process = None
        self.btn_backup.config(text="Start Backup")
        self.status_label.config(text="Backup stopped.")

    def _toggle_pic_review(self):
        if self.pic_review_process is not None and self.pic_review_process.poll() is None:
            self._stop_pic_review()
        else:
            self._start_pic_review()

    def _start_pic_review(self):
        if self.pic_review_process is not None and self.pic_review_process.poll() is None:
            self.status_label.config(text="Pic Quality Review already running.")
            return
        try:
            self.pic_review_process = subprocess.Popen(
                [sys.executable, PIC_QUALITY_SCRIPT],
                cwd=SCRIPT_DIR,
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            self.btn_pic_review.config(text="Stop Pic Quality Review")
            self.status_label.config(text="Pic Quality Review running.")
        except FileNotFoundError:
            self.status_label.config(text="Error: pic_quality_review.py not found.")
            messagebox.showerror("Error", f"Could not find:\n{PIC_QUALITY_SCRIPT}")
        except Exception as e:
            self.status_label.config(text="Error starting Pic Quality Review.")
            messagebox.showerror("Error", f"Failed to start Pic Quality Review:\n{e}")

    def _stop_pic_review(self):
        if self.pic_review_process is None or self.pic_review_process.poll() is not None:
            self.pic_review_process = None
            self.btn_pic_review.config(text="Start Pic Quality Review")
            return
        _kill_process_and_children(self.pic_review_process)
        self.pic_review_process = None
        self.btn_pic_review.config(text="Start Pic Quality Review")
        self.status_label.config(text="Pic Quality Review stopped.")

    def _exit_app(self):
        if self._poll_id is not None:
            self.after_cancel(self._poll_id)
            self._poll_id = None
        self.status_label.config(text="Stopping all processes…")
        self.update_idletasks()
        _kill_process_and_children(self.backup_process)
        _kill_process_and_children(self.pic_review_process)
        self.backup_process = None
        self.pic_review_process = None
        self.quit()
        self.destroy()


if __name__ == "__main__":
    app = BackupMenuApp()
    app.mainloop()
