'''
    Backup Photos on Cell Phone and SD Cards

    config.json lists the sources to watch for and backup destinations and folders.

    Program:
    1. Wait for the external drive to be mounted
    2. When found,
        if drive is a source volume copy new photos and videos to local backup directory
        if drive is a backup volume, copy from new photos and videos in local backup directory to backup volume
    3. Dismount the external drive

'''

from datetime import datetime
import os
import threading
import time
from file_watcher import FileWatcher
from json_config_reader import JsonConfigReader
from blink_led import ToggleLed
from dir_sync import DirSync
from terminal_tailer import TerminalTailer

class AutoBackup(threading.Thread):
    def __init__(self, local_backup_dir, sources, backups, backup_subdir, exclude_file, rsync_log_file, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local_backup_dir = local_backup_dir
        self._stop_event = threading.Event()
        self.sources = sources
        self.backups = backups
        self.backup_subdir = backup_subdir
        self.exclude_file = exclude_file

        self.sync_manager = DirSync(log_file=rsync_log_file)

        self.red_led_blink_rate = 0.25 
        self.green_led_blink_rate = 0.75

        self.create_file_watchers()

    def create_file_watchers(self):
        # Create File Watchers for each source and backup volume
        for source in self.sources:
            source_volume = source.get("volume")
            source_directory = source.get("directory")
            source_descr = source.get("descr", "No description")

            print(f"Watching for {source_descr}...")
            watcher = FileWatcher(source_volume,source_directory)
            source["watcher"] = watcher

        for backup in self.backups:
            backup_volume = backup.get("volume")
            backup_directory = backup.get("directory")
            backup_descr = backup.get("descr", "No description")

            print(f"Watching for {backup_descr}...")
            watcher = FileWatcher(backup_volume,backup_directory)
            backup["watcher"] = watcher

    def stop(self):
        """Sets the internal flag to signal the thread to stop."""
        self._stop_event.set()

    def stopped(self):
        """Checks if the stop event has been set."""
        return self._stop_event.is_set()
    
    def run(self):

        # Start Green Slow blink LED
        blink_led = ToggleLed(color="green", rate=self.green_led_blink_rate)

        while not self.stopped():
            # Wait between checks
            time.sleep(3)
            
            # Check each source for files
            for source in self.sources:
                watcher = source.get("watcher")
                if watcher.find_file():
                    start_dt = datetime.now()
                    print((f"\n-------- {start_dt:%m-%d-%Y %H:%M} {'-'*40}"))
                    print(f"Source '{source.get('descr', 'No description')}' found.")

                    # Stop Green LED blink and start red LED blink
                    blink_led.stop()
                    blink_led = ToggleLed(color="red", rate=self.red_led_blink_rate)

                    # Backup new files from source to local backup directory
                    dst = os.path.join(self.local_backup_dir, self.backup_subdir)
                    print(f"Backing up new files from '{watcher.file_path}' to '{dst}'...")

                    try:
                        self.sync_manager.run_sync(watcher.file_path, dst, self.exclude_file)
                    except Exception as e:
                        print(f"Error occurred while syncing: {e}")

                    watcher.dismount()
                    print(f"Source '{source.get('descr', 'No description')}' copied to local backup directory.")
                    print(f"Source '{source.get('descr', 'No description')}' dismounted.")
                    print("Waiting for new media source or backup...")

                    # Stop red blinking and restart green blink
                    blink_led.stop()
                    blink_led = ToggleLed(color="green", rate=self.green_led_blink_rate)

            # Check each backup for files
            for backup in self.backups:
                watcher = backup.get("watcher")
                if watcher.find_file():
                    start_dt = datetime.now()
                    print((f"\n-------- {start_dt:%m-%d-%Y %H:%M} {'-'*40}"))
                    print(f"Backup '{backup.get('descr', 'No description')}' found.")

                    # Stop Green LED blink and start red LED blink
                    blink_led.stop()
                    blink_led = ToggleLed(color="red", rate=self.red_led_blink_rate)

                    # Backup new files from local backup directory to backup volume
                    src = os.path.join(self.local_backup_dir, self.backup_subdir)
                    dst = os.path.join(watcher.file_path, self.backup_subdir)
                    print(f"Backing up from '{src}' to '{dst}'...")

                    self.sync_manager.run_sync(src, dst, self.exclude_file)

                    watcher.dismount()
                    print(f"Local backup copied to '{backup.get('descr', 'No description')}'")
                    print(f"Backup '{backup.get('descr', 'No description')}' dismounted.")
                    print("Waiting for new media source or backup...")

                    # Stop red blinking and restart green blink
                    blink_led.stop()
                    blink_led = ToggleLed(color="green", rate=self.green_led_blink_rate)
            

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