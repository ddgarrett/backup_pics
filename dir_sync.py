import subprocess
import os
from typing import Optional

''' 
  Google Search Prompt:
    generate a python class to execute a bash script named dir_sync.sh 
    passing the script source and destination directory names 
    and name of file with exclude statements
'''

class DirSync:
    """
    A class to execute the dir_sync.sh bash script.
    
    This class uses Python's subprocess module to run a bash script to
    synchronize directories, with specified source, destination, and exclude file arguments.
    """
    def __init__(self, script_path=None, log_file="rsync_log.txt"):
        """
        Initializes the DirSync instance.
        
        Args:
            script_path (str): The full path to the dir_sync.sh script.
        """
        if script_path is None:
            script_dir = os.path.dirname(os.path.realpath(__file__))
            script_path = os.path.join(script_dir, "dir_sync.sh")

        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"The script file was not found: {script_path}")
        
        self.script_path = script_path
        self.log_file = log_file
        
    def run_sync(self, source_dir: str, dest_dir: str, exclude_file: Optional[str] = None):
        """
        Executes the dir_sync.sh script with the specified arguments.
        
        Args:
            source_dir (str): The source directory for the sync.
            dest_dir (str): The destination directory for the sync.
            exclude_file (Optional[str]): The name of the file containing exclude statements.
                If None, the exclude file argument is omitted.
        
        Returns:
            subprocess.CompletedProcess: The result of the completed process.
        
        Raises:
            subprocess.CalledProcessError: If the script returns a non-zero exit code.
        """
        # Construct the command as a list of strings for security
        # This prevents shell injection vulnerabilities.
        command = [self.script_path, source_dir, dest_dir]

        if exclude_file:
            command.append(exclude_file)

        print(command)
        print(f"Executing command: {' '.join(command)}.")
        print(f"--Check log file at {self.log_file} for details.")

        try:
            with open(self.log_file, 'a') as log:
                # Use subprocess.run for a straightforward, high-level approach.
                # `check=True` will raise an exception if the script fails.
                # `capture_output=True` captures stdout and stderr.
                # `text=True` decodes output to strings.
                result = subprocess.run(
                    command,
                    capture_output=False,
                    stdout=log,
                    stderr=log,
                    text=True,
                    check=True
                )
                print("Script executed successfully.")
                return result
        except FileNotFoundError:
            print("Error: The script or one of the directories was not found.")
            raise
        except subprocess.CalledProcessError as e:
            print("Error: Script execution failed.")
            print(f"Return code: {e.returncode}")
            print(f"rsync command failed with error: {e}")
            print(f"Error output can be found in {self.log_file}")
            raise

# --- Example Usage ---

if __name__ == "__main__":

    ''' Requires Pixel and T7 SSD to be connected 
        Exlcudes 3 pictures always kept on Pixel
        and any .trashed pixel pictures
    '''

    # Initialize the class with the script path
    sync_manager = DirSync(log_file="/home/dgarrett/Documents/pictures/MEDIA_BACKUP/rsync_log.txt")
    exclude_file = "sync_exclude.txt"

    # source = "/run/user/1000/gvfs/mtp:host=Google_Pixel_8_Pro_42230DLJG0014Y/Internal shared storage/DCIM/Camera"
    # destination = "/home/dgarrett/Documents/pictures/MEDIA_BACKUP/yyyy-mm-dd_backup"
    # sync_manager.run_sync(source, destination, exclude_file)

    # print("Pixel backed up")

    source = "/home/dgarrett/Documents/pictures/MEDIA_BACKUP/yyyy-mm-dd_backup"
    destination = "/media/dgarrett/T7/pictures/MEDIA_BACKUP/yyyy-mm-dd_backup"
    sync_manager.run_sync(source, destination, exclude_file)

    print("RPi 5 Backed up to T7")