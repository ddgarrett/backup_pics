"""
Manages starting and stopping the backup pictures process (main.py) in a visible terminal.

Used by the menu GUI on Raspberry Pi 5. The backup runs in lxterminal, xterm, or gnome-terminal
so that backup messages are visible to the user.
"""
import os
import shutil
import signal
import subprocess
import sys


def _shell_escape(s):
    """Escape a string for use inside double quotes in a shell command."""
    return s.replace("\\", "\\\\").replace('"', '\\"')


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


class BackupProcess:
    """Starts and stops the backup pictures process (main.py) in a new visible terminal."""

    def __init__(self, script_dir=None):
        self.script_dir = script_dir or os.path.dirname(os.path.abspath(__file__))
        self.main_py = os.path.join(self.script_dir, "main.py")
        self._process = None

    def is_running(self):
        """Return True if the backup process is currently running."""
        return self._process is not None and self._process.poll() is None

    def _terminal_argv(self):
        """Return argv to run the backup in a new visible terminal (lxterminal, xterm, or gnome-terminal)."""
        esc_dir = _shell_escape(self.script_dir)
        esc_main = _shell_escape(self.main_py)
        bash_cmd = f'bash -c "cd \\"{esc_dir}\\" && {sys.executable} \\"{esc_main}\\"; exec bash"'
        run_cmd = f'cd "{self.script_dir}" && {sys.executable} "{self.main_py}"; exec bash'

        for term in ["lxterminal", "xterm", "gnome-terminal"]:
            if shutil.which(term):
                if term == "gnome-terminal":
                    return ["gnome-terminal", "--", "bash", "-c", run_cmd]
                return [term, "-e", bash_cmd]
        # fallback: assume lxterminal (Raspberry Pi)
        return ["lxterminal", "-e", bash_cmd]

    def start(self):
        """
        Start the backup process in a new visible terminal.

        Returns None on success.
        Returns (error_title, error_message) on failure for the caller to show in a messagebox.
        """
        if self.is_running():
            return ("Already running", "Backup is already running.")
        try:
            argv = self._terminal_argv()
            self._process = subprocess.Popen(
                argv,
                cwd=self.script_dir,
                start_new_session=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return None
        except FileNotFoundError:
            return ("Error", f"Could not find:\n{self.main_py}")
        except Exception as e:
            return ("Error", f"Failed to start backup:\n{e}")

    def stop(self):
        """Stop the backup process if it is running."""
        if not self.is_running():
            self._process = None
            return
        _kill_process_and_children(self._process)
        self._process = None

    def poll(self):
        """
        Return the process exit code if it has ended, or None if still running.
        Convenience for the menu to detect when the process has exited on its own.
        """
        if self._process is None:
            return None
        return self._process.poll()
