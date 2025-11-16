'''
    Backup Photos on Cell Phone, SD Cards and iOS Devices

    config.json lists the sources to watch for 
    and backup destinations and folders.

'''
import os

from auto_backup import AutoBackup
from json_config_reader import JsonConfigReader
from terminal_tailer import TerminalTailer


if __name__ == "__main__":
    config = JsonConfigReader("config.json")
    local_backup_dir = config.get("local_backup_dir")
    backup_subdir = config.get("backup_subdir")
    backups = config.get("backups", [])
    sources = config.get("sources", [])
    exclude_file = config.get("exclude")
    rsync_log_file = config.get("rsync_log_file", os.path.join(local_backup_dir, "rsync_log.txt"))

    # show rsync log in terminal window
    tailer = TerminalTailer(rsync_log_file, terminal_emulator="lxterminal") # Use "xterm" or "gnome-terminal" if lxterminal is not available
    tailer.start_tailing()

    # Create and start the AutoBackup thread
    thread = AutoBackup(local_backup_dir,sources, backups, backup_subdir, exclude_file, rsync_log_file)
    thread.start()

    # run until user hits Enter
    input("Press Enter to end auto backup...\n\n")

    # Stop thread from the main thread
    print("\nMain thread: Signalling Worker to stop...")
    thread.stop()

    # Wait for the thread to finish its execution
    thread.join()

    # Stop tailing
    tailer.stop_tailing()
    
    print("\nMain thread: All threads have stopped.")