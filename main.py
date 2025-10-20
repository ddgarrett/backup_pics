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

import time
from file_watcher import FileWatcher
from json_config_reader import JsonConfigReader
from blink_red_led import TogglePowerLed

config = JsonConfigReader("config.json")
backup_subdir = config.get("backup_subdirectory", "yyyy-mm-dd_backup")
backups = config.get("backups", [])
sources = config.get("sources", [])
exclude_files = set(config.get("exclude", []))

def create_file_watchers():
    # Create File Watchers for each source and backup volume
    for source in sources:
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

create_file_watchers()
# print(sources)
# print(backups)

while True:
    # Check each source for files
    for source in sources:
        watcher = source.get("watcher")
        if watcher.find_file():
            print(f"Source '{source.get('descr', 'No description')}' found.")
            # TODO: Add code to backup new files from source to local backup directory
            print("waiting 5 seconds before dismounting...")
            time.sleep(5)
            watcher.dismount()
            print("dismounted")

    # Check each backup for files
    for backup in backups:
        watcher = backup.get("watcher")
        if watcher.find_file():
            print(f"Backup '{backup.get('descr', 'No description')}' found.")
            # TODO: Add code to backup new files from local backup directory to backup volume
            print("waiting 5 seconds before dismounting...")
            time.sleep(5)
            watcher.dismount()
            print("dismounted")