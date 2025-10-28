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
    
    This class uses Python's subprocess module to run a bash script with
    specified source, destination, and exclude file arguments.
    """
    def __init__(self, script_path: str):
        """
        Initializes the DirSync instance.
        
        Args:
            script_path (str): The full path to the dir_sync.sh script.
        """
        if not os.path.isfile(script_path):
            raise FileNotFoundError(f"The script file was not found: {script_path}")
        self.script_path = script_path
        
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

        print(f"Executing command: {' '.join(command)}")
        
        try:
            # Use subprocess.run for a straightforward, high-level approach.
            # `check=True` will raise an exception if the script fails.
            # `capture_output=True` captures stdout and stderr.
            # `text=True` decodes output to strings.
            result = subprocess.run(
                command,
                capture_output=True,
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
            print(f"Standard output: {e.stdout}")
            print(f"Standard error: {e.stderr}")
            raise

# --- Example Usage ---

if __name__ == "__main__":
    # Create a dummy shell script for demonstration
    with open("dir_sync.sh", "w") as f:
        f.write("#!/bin/bash\n\n")
        f.write("echo \"Running sync from $1 to $2\"\n")
        f.write("if [ -n \"$3\" ]; then\n")
        f.write("    echo \"Using exclude file: $3\"\n")
        f.write("fi\n")
        f.write("echo \"Sync complete.\"\n")
    
    # Make the script executable
    os.chmod("dir_sync.sh", 0o755)

    # Initialize the class with the script path
    sync_manager = DirSync("./dir_sync.sh")

    # Example 1: Execute the script with all arguments
    try:
        source = "/path/to/source"
        destination = "/path/to/destination"
        exclude_file = "exclude.txt"
        sync_manager.run_sync(source, destination, exclude_file)
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Example 1 failed.")

    print("-" * 20)

    # Example 2: Execute the script without the exclude file
    try:
        sync_manager.run_sync("/path/to/source2", "/path/to/destination2")
    except (FileNotFoundError, subprocess.CalledProcessError):
        print("Example 2 failed.")
        
    # Clean up the dummy script
    os.remove("dir_sync.sh")
