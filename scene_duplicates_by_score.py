#!/usr/bin/env python3
"""
Find scene duplicates within a single day of photos, keeping the best by score.

After rating pictures with MUSIQ (AVA), sort by score and for each high-scoring
image treat it as the "keeper" for that scene. Any lower-scoring image that is
visually the same scene (different angle, composition, or zoom) is marked as a
duplicate of that keeper. Goal: one best shot per scene for travel albums.

Only compares images from the same day (single directory). Uses CNN embeddings
(imagededup) to detect "same scene, different view" duplicates.

When both the high-scoring (keeper) photo and the candidate have EXIF GPS, the
duplicate test is run only if the candidate is within --gps-radius-meters (default
200). Photos without GPS are always compared (no distance filter).

By default, saves a CSV in the same directory as the photos (image_scores_and_status.csv)
with all input MUSIQ CSV fields plus: gps_latitude, gps_longitude, date_time_taken, status, dup_photo.

Usage:
  python scene_duplicates_by_score.py /path/to/day_directory
  python scene_duplicates_by_score.py /path/to/day_directory --gps-radius-meters 200

Reads scores from image_evaluator_musiq CSV only (e.g. image_evaluation_musiq_results_1024.csv).
  Use --musiq-csv-size to match the max-size you used (default 1024; use 0 for 'full').
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from image_analysis_lib import duplicates
from image_analysis_lib.config import default_config


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Find scene duplicates within a single day: sort by MUSIQ/AVA score, "
            "then mark lower-scoring images that are the same scene (different angle/zoom) as duplicates."
        )
    )
    parser.add_argument(
        "day_directory",
        type=Path,
        help="Directory for one day of photos (must contain image_evaluation_musiq_results_<size>.csv from image_evaluator_musiq.py)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.65,
        metavar="T",
        help="Minimum cosine similarity to consider same scene (default 0.65). Lower = more pairs marked duplicate.",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Path for JSON duplicate report. Default: same directory as photos (scene_duplicates_report.json).",
    )
    parser.add_argument(
        "--list-remove",
        action="store_true",
        help="Print only the list of duplicate paths (one per line) for piping to removal scripts",
    )
    parser.add_argument(
        "--gps-radius-meters",
        type=float,
        default=200.0,
        metavar="M",
        help="When both photos have EXIF GPS, only test for duplicate if candidate is within M meters of keeper (default 200). Use 0 to disable GPS filtering.",
    )
    parser.add_argument(
        "--musiq-csv-size",
        type=int,
        default=MUSIQ_CSV_DEFAULT_SIZE,
        metavar="N",
        help=f"Max-size label for image_evaluator_musiq CSV: look for image_evaluation_musiq_results_N.csv (default {MUSIQ_CSV_DEFAULT_SIZE}). Use 0 for 'full'.",
    )
    parser.add_argument(
        "--poor-quality-threshold",
        type=float,
        default=POOR_QUALITY_THRESHOLD,
        metavar="S",
        help=f"Score below this is 'poor quality' and excluded from duplicate check (default {POOR_QUALITY_THRESHOLD}).",
    )
    parser.add_argument(
        "--copy-by-status",
        action="store_true",
        dest="copy_by_status",
        default=True,
        help="Copy images into image_root/_by_status/<status>/ subfolders (default).",
    )
    parser.add_argument(
        "--no-copy-by-status",
        action="store_false",
        dest="copy_by_status",
        help="Do not copy images by status.",
    )
    parser.add_argument(
        "--verbose",
        "-v",
        action="store_true",
        help="Show progress: directory, picture counts, highest-scoring images as processed, duplicate and non-duplicate counts.",
    )
    args = parser.parse_args()

    image_root = args.day_directory.resolve()
    if not image_root.is_dir():
        print(f"Not a directory: {image_root}", file=sys.stderr)
        return 1

    # Default: save outputs in the same directory as the photos
    report_path = args.output if args.output is not None else image_root / "scene_duplicates_report.json"

    musiq_rows = duplicates.load_full_musiq_csv(
        image_root,
        size=args.musiq_csv_size,
        prefix=default_config.musiq_csv_prefix,
    )
    if args.verbose:
        print(f"Processing directory: {image_root}")
        print(f"Pictures found in MUSIQ score CSV: {len(musiq_rows)}")
        scores = duplicates.load_scores_from_musiq_csv(
            image_root,
            size=args.musiq_csv_size,
            prefix=default_config.musiq_csv_prefix,
        )
        n_rejected = sum(
            1 for _, s in scores.items() if s is not None and s < args.poor_quality_threshold
        )
        print(
            f"Pictures rejected (poor quality, score < {args.poor_quality_threshold}): "
            f"{n_rejected}"
        )
        if scores:
            print("Checking for duplicates (highest-scoring images first):")

    gps_radius = None if args.gps_radius_meters == 0 else args.gps_radius_meters
    keeper_to_dups, dup_to_keeper = duplicates.find_duplicates_by_score(
        image_root,
        config=default_config,
        min_similarity_threshold=args.threshold,
        gps_radius_meters=gps_radius,
        musiq_csv_size=args.musiq_csv_size,
        poor_quality_threshold=args.poor_quality_threshold,
        verbose=args.verbose,
    )

    if args.list_remove:
        for dup in sorted(dup_to_keeper.keys()):
            print(dup)
        return 0

    # Report
    total_dups = sum(len(d) for d in keeper_to_dups.values())
    musiq_label = "full" if args.musiq_csv_size == 0 else str(args.musiq_csv_size)
    print(f"Day directory: {image_root}")
    print(f"MUSIQ CSV size: {musiq_label}")
    print(f"Similarity threshold: {args.threshold}")
    print(f"GPS radius (meters): {args.gps_radius_meters if args.gps_radius_meters != 0 else 'disabled'}")
    print(f"Keepers with at least one duplicate: {len(keeper_to_dups)}")
    print(f"Total images marked as duplicate (same scene, lower score): {total_dups}")
    print()

    if keeper_to_dups:
        print("=== Keepers and their duplicate(s) (same scene) ===")
        for keeper in sorted(keeper_to_dups.keys(), key=lambda k: (-len(keeper_to_dups[k]), k)):
            dups = keeper_to_dups[keeper]
            print(f"  Keeper: {keeper}")
            for d in sorted(dups):
                print(f"    duplicate: {d}")
            print()
    else:
        print("No scene duplicates found at this threshold.")

    report = {
        "day_directory": str(image_root),
        "musiq_csv_size": args.musiq_csv_size,
        "threshold": args.threshold,
        "gps_radius_meters": args.gps_radius_meters if args.gps_radius_meters != 0 else None,
        "keeper_to_duplicates": keeper_to_dups,
        "duplicate_to_keeper": dup_to_keeper,
    }
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"Wrote report to {report_path}")

    # Default output: CSV with all fields in the same directory as the photos
    if musiq_rows:
        status_csv_path = duplicates.write_status_csv(
            image_root,
            musiq_rows,
            dup_to_keeper,
            poor_quality_threshold=args.poor_quality_threshold,
        )
        print(f"Wrote {status_csv_path.name} (all fields) to {image_root}")
        if args.copy_by_status:
            duplicates.copy_images_by_status(
                image_root,
                musiq_rows,
                dup_to_keeper,
                poor_quality_threshold=args.poor_quality_threshold,
            )
            print(f"Copied images to {image_root / duplicates.BY_STATUS_DIR}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
