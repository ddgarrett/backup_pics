#!/bin/bash

# Check if both source and destination directories are provided as arguments
if [ -z "$1" ] || [ -z "$2" ] || [ -z "$3" ]; then
  echo "Usage: $0 <source_directory> <destination_directory> <exclude_file>"
  exit 1
fi

SOURCE_DIR="$1"
DEST_DIR="$2"
EXCLUDE_FILE="$3"

# Check if source directory exists
if [ ! -d "$SOURCE_DIR" ]; then
  echo "Error: Source directory '$SOURCE_DIR' does not exist."
  exit 1
fi

# Ensure destination directory exists
if [ ! -d "$DEST_DIR" ]; then
    echo "Error: Desination directory '$DEST_DIR' not found."
    exit 1
fi

# Ensure exclude file exists
if [ ! -f "$EXCLUDE_FILE" ]; then
    echo "Error: Exclude file '$EXCLUDE_FILE' not found."
    exit 1
fi

# Use rsync to copy new or updated files
# -a: archive mode (preserves permissions, timestamps, ownership, etc.)
# -u: update (skip files that are newer in dest)
# -v: verbose (show files being transferred)
# --progress: show progress during transfer
# --exclude-from= specify file with patterns to exclude
# --dry-run: (optional) for testing, remove to perform actual copy
#rsync -auv --progress "$SOURCE_DIR"/ "$DEST_DIR"
rsync -ahv --size-only --progress --exclude-from="$EXCLUDE_FILE" "$SOURCE_DIR"/ "$DEST_DIR"
# echo "New or updated files copied from '$SOURCE_DIR' to '$DEST_DIR'."