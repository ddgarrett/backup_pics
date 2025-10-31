import subprocess
import time
import os
import signal

class TerminalTailer:
    def __init__(self, filename, terminal_emulator="lxterminal"):
        """
        Initializes the TerminalTailer.

        Args:
            filename (str): The path to the file to be tailed.
            terminal_emulator (str): The terminal emulator to use (e.g., "lxterminal", "xterm", "gnome-terminal").
        """
        self.filename = filename
        self.terminal_emulator = terminal_emulator
        self.process = None

    def start_tailing(self):
        """
        Opens a new terminal and starts tailing the specified file.
        """
        if not os.path.exists(self.filename):
            print(f"Error: File '{self.filename}' not found.")
            return

        command = [self.terminal_emulator, '-e', f'tail -f {self.filename}']
        try:
            self.process = subprocess.Popen(command)
            print(f"Tailing '{self.filename}' in a new {self.terminal_emulator} window.")
            
        except FileNotFoundError:
            print(f"Error: Terminal emulator '{self.terminal_emulator}' not found. "
                  "Please ensure it is installed and in your PATH.")
        except Exception as e:
            print(f"An error occurred while starting the terminal: {e}")

    def stop_tailing(self):
        """
        Terminates the terminal process if it's running.
        """
        if self.process:
            self.process.terminate()
            print("Terminal process terminated.")
            self.process = None

# Example Usage:
if __name__ == "__main__":
    log_file = "/home/dgarrett/Documents/pictures/MEDIA_BACKUP/rsync_log.txt"


    tailer = TerminalTailer(log_file, terminal_emulator="lxterminal") # Use "xterm" or "gnome-terminal" if lxterminal is not available

    # Start tailing the file
    tailer.start_tailing()

    input("Press Enter to end tailing...")

    # Stop tailing
    tailer.stop_tailing()
