## Backup Pics

Automatically backup pictures. `config.json` defines image sources and secondary backup drives.
Workflow is to attach a phone or camera SD card. Any new pictures will be copied to a backup directory 
on the Raspberry Pi 5 SSD. Secondary backup drives can then be attached to the Raspberry Pi
and new pictures will be copied to those drives.

Created for Raspberry Pi 5 (RPi5) with 2 TB SSD.

Backup program automatically starts when RPi5 is booted.

Multiple external backup drives can be used, such as a travel SSD 
and a home based magnetic hard drive.

Optionally, deleting pictures from the photo/video source can be done after photos have been
backed up to RPi5 or backed up to a given external backup drive.

---

- **Autostart**: backup currently runs `main.py`.

- **Menu-based control** (in progress):
  - `menu.py` displays a menu and starts the backup process defined in `backup_process.py`.
  - `backup_process.py` starts/stops `main.py`.
  - `pic_quality_review.py` is a placeholder for quality review.

---

## Image quality scoring and scene duplicate detection

Image quality scoring and scene-duplicate detection are now provided by the shared
`image_analysis_lib` package, which is used by both `backup_pics` and `process_images`.

### Installation (shared library)

`image_analysis_lib` requires **Python 3.10 or newer**. Use a 3.10+ interpreter to create the venv.

**From this project directory**, using `requirements.txt` (pulls the library from GitHub):

```bash
# macOS with Homebrew Python 3.12 (Apple Silicon path):
/opt/homebrew/opt/python@3.12/bin/python3.12 -m venv .venv
. .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

On Raspberry Pi OS Bookworm, `python3.11` or `python3.12` is usually available; use that instead of `python3` if the default is 3.9.

**If you have `image_analysis_lib` as a local clone** (e.g. sibling directory or submodule), you can install in editable mode:

```bash
pip install -e ../image_analysis_lib
```

That exposes the `image-analysis` CLI and uses your local library code.

### MUSIQ scoring on Raspberry Pi 5

To score all JPEGs under a directory (for example a day folder created by `backup_pics`):

```bash
python image_evaluator_musiq.py /home/dgarrett/Documents/pictures/MEDIA_BACKUP/yyyy-mm-dd_backup \
  --max-size 1024 0 \
  --output-prefix image_evaluation_musiq_results
```

- `--max-size 1024 0` evaluates at 1024px long side and at full resolution.
- The script uses `image_analysis_lib.musiq` under the hood and writes:
  - `image_evaluation_musiq_results_1024.csv`
  - `image_evaluation_musiq_results_full.csv`

You can also call the shared CLI directly instead of the script:

```bash
image-analysis score /home/dgarrett/Documents/pictures/MEDIA_BACKUP/yyyy-mm-dd_backup \
  --max-size 1024 0 \
  --output-prefix image_evaluation_musiq_results
```

On Raspberry Pi 5, you may prefer smaller sizes (e.g. `512`) to speed up scoring.

### Scene duplicate detection

After MUSIQ scores have been generated for a given day directory, you can find scene duplicates:

```bash
python scene_duplicates_by_score.py /home/dgarrett/Documents/pictures/MEDIA_BACKUP/yyyy-mm-dd_backup \
  --musiq-csv-size 1024 \
  --threshold 0.65 \
  --gps-radius-meters 200
```

or via the CLI:

```bash
image-analysis dedupe /home/dgarrett/Documents/pictures/MEDIA_BACKUP/yyyy-mm-dd_backup \
  --musiq-csv-size 1024 \
  --threshold 0.65 \
  --gps-radius-meters 200
```

This will:

- Read the appropriate MUSIQ CSV (e.g. `image_evaluation_musiq_results_1024.csv`).
- Use CNN encodings plus optional GPS radius to detect “same scene, lower score” duplicates.
- Write:
  - `scene_duplicates_report.json` with keeper/duplicate mappings.
  - `image_scores_and_status.csv` with MUSIQ scores, EXIF extras, and status (`best`, `good`, `dup`, `poor quality`, `TBD`).
  - `_by_status/` folders that group images by status.

You can also get a simple list of duplicates for removal scripts:

```bash
image-analysis dedupe /home/dgarrett/Documents/pictures/MEDIA_BACKUP/yyyy-mm-dd_backup \
  --musiq-csv-size 1024 \
  --threshold 0.65 \
  --list-remove
```

### Pi + MacBook workflow with `process_images`

Typical use across devices:

1. **On Raspberry Pi 5**:
   - Run `backup_pics` to copy images from phone/SD card into dated backup folders.
   - Optionally run MUSIQ scoring and scene-duplicate detection (as above) on one or more day folders.
2. **On MacBook Air (or Pi)**:
   - Mount or copy the same day folders.
   - (Optional) Re-run `image-analysis score` or `image-analysis dedupe` with different thresholds
     for faster experimentation; outputs stay compatible.
3. **In `process_images`**:
   - Open the same day folders as a collection.
   - `process_images` reads the MUSIQ scores (`musiq_rating`) and any pre-labeled statuses
     produced by `image_scores_and_status.csv`.
   - Use the GUI to refine statuses, review duplicates, and select the best photos.

