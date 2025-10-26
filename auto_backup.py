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

import os
import threading
import time
from file_watcher import FileWatcher
from json_config_reader import JsonConfigReader
from blink_red_led import TogglePowerLed
from directory_synchronizer import DirectorySynchronizer

class AutoBackup(threading.Thread):
    def __init__(self, local_backup_directory, sources, backups, backup_subdir, exclude_files, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.local_backup_directory = local_backup_directory
        self._stop_event = threading.Event()
        self.sources = sources
        self.backups = backups
        self.backup_subdir = backup_subdir
        self.exclude_files = exclude_files

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

        for backup in backups:
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
        while not self.stopped():
            # Check each source for files
            for source in sources:
                watcher = source.get("watcher")
                if watcher.find_file():
                    print(f"Source '{source.get('descr', 'No description')}' found.")

                    # Create and start the thread to blink red LED
                    thread = TogglePowerLed(interval=0.5)
                    thread.start()

                    # Backup new files from source to local backup directory
                    DirectorySynchronizer(
                        os.path.join(watcher.mounted_path, watcher.directory, self.backup_subdir),
                        os.path.join(self.local_backup_directory, self.backup_subdir),
                        exclude_files=self.exclude_files
                    ).synchronize_new_files()

                    watcher.dismount()
                    print("dismounted")

                    # Stop thread from the main thread
                    thread.stop()
                    thread.join()

            # Check each backup for files
            for backup in backups:
                watcher = backup.get("watcher")
                if watcher.find_file():
                    print(f"Backup '{backup.get('descr', 'No description')}' found.")

                   # Create and start the thread to blink red LED
                    thread = TogglePowerLed(interval=0.5)
                    thread.start()

                    # TODO: Add code to backup new files from local backup directory to backup volume
                    print("waiting 5 seconds before dismounting since copy not yet in place...")
                    time.sleep(5)

                    watcher.dismount()
                    print("dismounted")

                    # Stop thread from the main thread
                    thread.stop()
                    thread.join()

if __name__ == "__main__":
    config = JsonConfigReader("config.json")
    local_backup_directory = config.get("local_backup_directory")
    backup_subdir = config.get("backup_subdirectory", "yyyy-mm-dd_backup")
    backups = config.get("backups", [])
    sources = config.get("sources", [])
    exclude_files = set(config.get("exclude", []))

    thread = AutoBackup(local_backup_directory,sources, backups, backup_subdir, exclude_files)
    thread.start()

    # Let thread run for a bit
    # To stop early, use [Ctrl]-c IF not in middle of a file copy
    time.sleep(1000)

    # Stop thread from the main thread
    print("\nMain thread: Signalling Worker to stop...")
    thread.stop()

    # Wait for the thread to finish its execution
    thread.join()

    print("\nMain thread: All threads have stopped.")