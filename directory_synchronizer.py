import os
import shutil

"""
    Python class to compare two directories and add new files from directory 1 to directory 2. 
    Note that in some cases directory 2 may be very large while directory 1 will be small 
    or both may be very large. Therefore the program should first create a set with all of the 
    files in directory 2.
"""

class DirectorySynchronizer:
    def __init__(self, source_dir, destination_dir):
        """
        Initializes the DirectorySynchronizer.

        Args:
            source_dir (str): The path to the source directory (Directory 1).
            destination_dir (str): The path to the destination directory (Directory 2).
        """
        self.source_dir = os.path.abspath(source_dir)
        self.destination_dir = os.path.abspath(destination_dir)

    def _get_all_files_in_directory(self, directory_path):
        """
        Recursively collects all file paths within a given directory and returns them as a set.
        Paths are relative to the given directory_path.

        Args:
            directory_path (str): The path to the directory to scan.

        Returns:
            set: A set of relative file paths within the directory.
        """
        all_files = set()
        for root, _, files in os.walk(directory_path):
            for file in files:
                relative_path = os.path.relpath(os.path.join(root, file), directory_path)
                all_files.add(relative_path)
        return all_files

    def synchronize_new_files(self):
        """
        Compares the source and destination directories and copies new files
        from the source to the destination.
        """
        if not os.path.isdir(self.source_dir):
            print(f"Error: Source directory '{self.source_dir}' does not exist.")
            return
        if not os.path.isdir(self.destination_dir):
            print(f"Error: Destination directory '{self.destination_dir}' does not exist.")
            return

        print(f"Scanning destination directory '{self.destination_dir}'...")
        destination_files = self._get_all_files_in_directory(self.destination_dir)
        print(f"Found {len(destination_files)} files in destination directory.")

        print(f"Scanning source directory '{self.source_dir}' and comparing...")
        files_copied_count = 0
        for root, _, files in os.walk(self.source_dir):
            for file in files:
                source_file_relative_path = os.path.relpath(os.path.join(root, file), self.source_dir)

                if source_file_relative_path not in destination_files:
                    source_file_full_path = os.path.join(root, file)
                    destination_file_full_path = os.path.join(self.destination_dir, source_file_relative_path)

                    # Create necessary subdirectories in the destination
                    os.makedirs(os.path.dirname(destination_file_full_path), exist_ok=True)

                    # print(f"Copying new file: '{source_file_relative_path}'")
                    shutil.copy2(source_file_full_path, destination_file_full_path)
                    files_copied_count += 1
        
        print(f"Synchronization complete. Copied {files_copied_count} new files.")

# Example Usage:
if __name__ == "__main__":
    '''
    # Create dummy directories and files for testing
    os.makedirs("dir1/subdir", exist_ok=True)
    os.makedirs("dir2/subdir", exist_ok=True)

    with open("dir1/fileA.txt", "w") as f:
        f.write("Content A")
    with open("dir1/subdir/fileB.txt", "w") as f:
        f.write("Content B")
    with open("dir2/fileC.txt", "w") as f:
        f.write("Content C")
    with open("dir2/subdir/fileD.txt", "w") as f:
        f.write("Content D")
    with open("dir1/new_file.txt", "w") as f:
        f.write("New content")
    with open("dir1/subdir/another_new_file.txt", "w") as f:
        f.write("Another new content")

    synchronizer = DirectorySynchronizer("dir1", "dir2")
    synchronizer.synchronize_new_files()

    # Clean up dummy directories
    shutil.rmtree("dir1")
    shutil.rmtree("dir2")
    '''

    synchronizer = DirectorySynchronizer("/home/dgarrett/Documents/pictures", 
                                         "/media/dgarrett/T7/test_backup")
    synchronizer.synchronize_new_files()