import os
import time
import subprocess

"""
generate python class that looks for a particular file path and 
if it is not found, waits for 5 seconds and then retries
"""

class FileWatcher:
    """
    A class to monitor a file path, retrying if the file is not found.
    """

    def __init__(self, volume, directory, retry_interval=5, max_retries=3):
        """
        Initializes the FileWatcher.

        Args:
            volume (str): The mount point or volume name of external storage.
            directory (str): The directory within the volume.
            retry_interval (int): The number of seconds to wait between retries.
            max_retries (int): The maximum number of times to retry.
        """
        self.volume = volume
        self.file_path = os.path.join(volume, directory)

        self.retry_interval = retry_interval
        self.max_retries = max_retries

    def find_file(self):
        """
        Attempts to find the directory, retrying if necessary.

        Returns:
            bool: True if the file is found, False otherwise.
        """
        for attempt in range(self.max_retries + 1):
            if os.path.exists(self.file_path):
                print(f"File found at: {self.file_path}")
                return True
            else:
                if attempt < self.max_retries:
                    print(f"File not found. Retrying in {self.retry_interval} seconds... (Attempt {attempt + 1}/{self.max_retries})")
                    time.sleep(self.retry_interval)
                else:
                    print(f"File not found after {self.max_retries} attempts.")
                    return False

    def dismount(self):
        """
        Dismounts the volume.
        """

        try:
            # Use gio to dismount the MTP device
            result = subprocess.run(['gio', 'mount', '-u', self.volume], capture_output=True, text=True, check=True)
            print(f"Successfully unmounted: {self.volume}")
            print(result.stdout)
        except subprocess.CalledProcessError as e:
            print(f"Error unmounting {self.volume}:")
            print(e.stderr)
        except FileNotFoundError:
            print("Error: 'gio' command not found. Ensure GVFS tools are installed.")

# Example Usage:
if __name__ == "__main__":
    # Create a dummy file for testing purposes
    # dummy_file_path = "test_file.txt"
    # with open(dummy_file_path, "w") as f:
    #     f.write("This is a test file.")

    # Watch for the external drive #1 = Google Pixel 8 PrInternal shared storage/DCIM/Camerao
    print("Watching for Google Pixel 8 Pro..." )
    watcher = FileWatcher("/run/user/1000/gvfs/mtp:host=Google_Pixel_8_Pro_42230DLJG0014Y",
                          "Internal shared storage/DCIM/Camera", 
                           retry_interval=5, max_retries=20000)
    if watcher.find_file():
        print("waiting 5 seconds before dismounting...")
        time.sleep(5)
        watcher.dismount()
        print("dismounted")

    # Watch for T7 drive
    print
    watcher = FileWatcher("/media/dgarrett/T7",
                          "MEDIA_BACKUP", 
                           retry_interval=5, max_retries=20000)
    if watcher.find_file():
        print("waiting 5 seconds before dismounting...")
        time.sleep(5)
        watcher.dismount()
        print("dismounted")

    # /run/user/1000/gvfs/mtp:host=Google_Pixel_8_Pro_42230DLJG0014Y
    # gio mount -u "/run/user/1000/gvfs/mtp:host=Google_Pixel_8_Pro_42230DLJG0014Y"
    # gio mount -u "/media/dgarrett/T7"
    # Watch for a non-existent file
    # non_existent_file_path = "non_existent_file.txt"
    # non_existent_watcher = FileWatcher(non_existent_file_path, retry_interval=3, max_retries=3)
    # non_existent_watcher.find_file()

    # Clean up the dummy file
    # os.remove(dummy_file_path)