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

Usage:
  python scene_duplicates_by_score.py /path/to/day_directory
  python scene_duplicates_by_score.py /path/to/day_directory --gps-radius-meters 200
  python scene_duplicates_by_score.py /path/to/day_directory --output duplicates_report.json

Reads scores from image_evaluator_musiq CSV only (e.g. image_evaluation_musiq_results_1024.csv).
  Use --musiq-csv-size to match the max-size you used (default 1024; use 0 for 'full').
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

# image_evaluator_musiq.py output: prefix_size.csv (e.g. image_evaluation_musiq_results_1024.csv)
MUSIQ_CSV_PREFIX = "image_evaluation_musiq_results"
MUSIQ_CSV_DEFAULT_SIZE = 1024

# Score below this: "poor quality", excluded from duplicate checking
POOR_QUALITY_THRESHOLD = 4.0

# Earth radius in meters for haversine
_EARTH_RADIUS_METERS = 6_371_000


def _dms_to_decimal(dms: tuple, ref: str, positive_ref: str) -> float | None:
    """Convert EXIF (deg, min, sec) rationals to decimal degrees. ref is e.g. 'N' or 'E'."""
    if not dms or len(dms) != 3:
        return None
    try:
        d = float(dms[0][0]) / float(dms[0][1]) if dms[0][1] else 0.0
        m = float(dms[1][0]) / float(dms[1][1]) if dms[1][1] else 0.0
        s = float(dms[2][0]) / float(dms[2][1]) if dms[2][1] else 0.0
        decimal = d + (m / 60.0) + (s / 3600.0)
        return decimal if ref == positive_ref else -decimal
    except (TypeError, ZeroDivisionError):
        return None


def get_gps_from_exif(image_path: Path) -> tuple[float, float] | None:
    """
    Read EXIF GPS from an image file. Returns (latitude, longitude) in decimal degrees or None.
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        with Image.open(image_path) as img:
            exif = img.getexif()
            if not exif:
                return None
            # GPS IFD tag id
            gps_tag_id = next((tid for tid, name in TAGS.items() if name == "GPSInfo"), None)
            if gps_tag_id is None:
                return None
            gps = exif.get_ifd(gps_tag_id)
            if not gps:
                return None
            lat_dms = gps.get(2)  # GPSLatitude
            lat_ref = gps.get(1, "N")  # GPSLatitudeRef
            lon_dms = gps.get(4)  # GPSLongitude
            lon_ref = gps.get(3, "E")  # GPSLongitudeRef
            if not lat_dms or not lon_dms:
                return None
            lat_ref_s = lat_ref.decode("ascii", errors="ignore") if isinstance(lat_ref, bytes) else (lat_ref or "N")
            lon_ref_s = lon_ref.decode("ascii", errors="ignore") if isinstance(lon_ref, bytes) else (lon_ref or "E")
            if not isinstance(lat_ref_s, str):
                lat_ref_s = "N"
            if not isinstance(lon_ref_s, str):
                lon_ref_s = "E"
            lat = _dms_to_decimal(lat_dms, lat_ref_s, "N")
            lon = _dms_to_decimal(lon_dms, lon_ref_s, "E")
            if lat is None or lon is None:
                return None
            return (lat, lon)
    except Exception:
        return None


def haversine_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance between two (lat, lon) points in meters."""
    import math

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlam = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlam / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return _EARTH_RADIUS_METERS * c


def build_gps_cache(image_root: Path, relative_paths: list[str]) -> dict[str, tuple[float, float] | None]:
    """Return map relative_path -> (lat, lon) or None if no GPS."""
    out: dict[str, tuple[float, float] | None] = {}
    for rel in relative_paths:
        full = image_root / rel
        out[rel] = get_gps_from_exif(full) if full.is_file() else None
    return out


def get_datetime_taken(image_path: Path) -> str:
    """
    Return date/time the photo was taken: EXIF DateTimeOriginal or DateTime, else file mtime (ISO).
    """
    try:
        from PIL import Image
        from PIL.ExifTags import TAGS

        with Image.open(image_path) as img:
            exif = img.getexif()
            if exif:
                # DateTimeOriginal = 36867, DateTime = 306
                for tag_id in (36867, 306):
                    val = exif.get(tag_id)
                    if val and isinstance(val, str):
                        # EXIF format "YYYY:MM:DD HH:MM:SS" -> convert to ISO
                        val = val.strip()
                        if len(val) >= 19 and ":" in val:
                            date_part = val[:10].replace(":", "-")
                            time_part = val[11:19]
                            return f"{date_part}T{time_part}"
                        return val
    except Exception:
        pass
    # Fallback: file modification time
    try:
        from datetime import datetime, timezone
        mtime = image_path.stat().st_mtime
        return datetime.fromtimestamp(mtime, tz=timezone.utc).isoformat()
    except Exception:
        return ""


def load_scores_from_musiq_csv(
    image_root: Path,
    size: int = MUSIQ_CSV_DEFAULT_SIZE,
    prefix: str = MUSIQ_CSV_PREFIX,
) -> dict[str, float]:
    """Load (relative_path -> musiq_score) from image_evaluator_musiq output: {prefix}_{size}.csv."""
    size_label = "full" if size == 0 else str(size)
    csv_path = image_root / f"{prefix}_{size_label}.csv"
    if not csv_path.exists():
        return {}
    out: dict[str, float] = {}
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rel = row.get("relative_path", "").strip()
            if not rel:
                continue
            raw = row.get("musiq_score")
            if raw is None or raw == "":
                continue
            try:
                out[rel] = float(raw)
            except ValueError:
                pass
    return out


def load_full_musiq_csv(
    image_root: Path,
    size: int = MUSIQ_CSV_DEFAULT_SIZE,
    prefix: str = MUSIQ_CSV_PREFIX,
) -> list[dict[str, str]]:
    """Load all rows from image_evaluator_musiq CSV as list of dicts (same column names)."""
    size_label = "full" if size == 0 else str(size)
    csv_path = image_root / f"{prefix}_{size_label}.csv"
    if not csv_path.exists():
        return []
    rows: list[dict[str, str]] = []
    with open(csv_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames or []
        for row in reader:
            # Normalize to str values for consistent CSV write
            out_row = {k: ("" if v is None else str(v).strip()) for k, v in row.items()}
            rows.append(out_row)
    return rows


def load_scores(
    image_root: Path,
    musiq_csv_size: int = MUSIQ_CSV_DEFAULT_SIZE,
) -> dict[str, float]:
    """Load (relative_path -> musiq_score) from image_evaluator_musiq CSV."""
    return load_scores_from_musiq_csv(image_root, size=musiq_csv_size)


def get_scored_paths_in_order(
    image_root: Path,
    musiq_csv_size: int = MUSIQ_CSV_DEFAULT_SIZE,
) -> list[tuple[str, float]]:
    """Return list of (relative_path, score) sorted by score descending (best first)."""
    scores = load_scores(image_root, musiq_csv_size=musiq_csv_size)
    if not scores:
        return []
    ordered = sorted(scores.items(), key=lambda x: (x[1], x[0]), reverse=True)
    return ordered


def build_encoding_map_for_paths(
    image_root: Path,
    relative_paths: list[str],
) -> dict[str, "np.ndarray"]:
    """Build CNN encoding map for the given relative paths. Keys = relative_path."""
    from imagededup.methods import CNN

    cnn = CNN()
    encodings: dict[str, "np.ndarray"] = {}
    for rel in relative_paths:
        full = image_root / rel
        if not full.is_file():
            continue
        enc = cnn.encode_image(image_file=str(full))
        if enc is not None:
            encodings[rel] = enc
    return encodings


def cosine_similarity(a: "np.ndarray", b: "np.ndarray") -> float:
    import numpy as np

    a = np.asarray(a).flatten().astype(float)
    b = np.asarray(b).flatten().astype(float)
    dot = float(np.dot(a, b))
    na = float(np.linalg.norm(a))
    nb = float(np.linalg.norm(b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def find_duplicates_by_score(
    image_root: Path,
    min_similarity_threshold: float = 0.65,
    gps_radius_meters: float | None = 200.0,
    musiq_csv_size: int = MUSIQ_CSV_DEFAULT_SIZE,
) -> tuple[dict[str, list[str]], dict[str, str]]:
    """
    For each image in score-desc order, mark lower-scoring images as duplicates if same scene.

    When both keeper and candidate have EXIF GPS, the duplicate test is run only if
    the candidate is within gps_radius_meters of the keeper. If gps_radius_meters is
    None or 0, no GPS filter is applied.

    Returns:
      keeper_to_duplicates: keeper relative_path -> list of duplicate relative_paths
      duplicate_to_keeper: duplicate relative_path -> keeper relative_path
    """
    from imagededup.methods import CNN

    ordered_all = get_scored_paths_in_order(image_root, musiq_csv_size=musiq_csv_size)
    # Exclude poor-quality (score < 4) from duplicate checking
    ordered = [(p, s) for p, s in ordered_all if s >= POOR_QUALITY_THRESHOLD]
    if not ordered:
        return {}, {}

    paths = [p for p, _ in ordered]
    use_gps = gps_radius_meters is not None and gps_radius_meters > 0
    gps_cache: dict[str, tuple[float, float] | None] = {}
    if use_gps:
        gps_cache = build_gps_cache(image_root, paths)

    # Encode only images we have scores for
    encodings = build_encoding_map_for_paths(image_root, paths)
    if len(encodings) < 2:
        return {}, {}

    # Index by position in score order (0 = best)
    path_to_idx = {p: i for i, (p, _) in enumerate(ordered)}
    keeper_to_duplicates: dict[str, list[str]] = {}
    duplicate_to_keeper: dict[str, str] = {}

    for keeper_path in paths:
        if keeper_path not in encodings:
            continue
        keeper_idx = path_to_idx[keeper_path]
        keeper_enc = encodings[keeper_path]
        keeper_gps = gps_cache.get(keeper_path) if use_gps else None

        for other_path in paths:
            if other_path == keeper_path or other_path not in encodings:
                continue
            if path_to_idx[other_path] <= keeper_idx:
                continue  # same or higher score: do not mark as duplicate of this keeper
            if other_path in duplicate_to_keeper:
                continue  # already marked as duplicate of a higher-scoring keeper

            # If both have GPS and we're using the filter, skip unless within radius
            if use_gps and keeper_gps is not None:
                other_gps = gps_cache.get(other_path)
                if other_gps is not None:
                    dist = haversine_meters(keeper_gps[0], keeper_gps[1], other_gps[0], other_gps[1])
                    if dist > gps_radius_meters:
                        continue  # too far; don't run duplicate test

            sim = cosine_similarity(keeper_enc, encodings[other_path])
            if sim >= min_similarity_threshold:
                duplicate_to_keeper[other_path] = keeper_path
                keeper_to_duplicates.setdefault(keeper_path, []).append(other_path)

    return keeper_to_duplicates, duplicate_to_keeper


# Output CSV name (same folder as images)
STATUS_CSV_BASENAME = "image_scores_and_status.csv"


def _parse_score(raw: str) -> float | None:
    """Parse musiq_score from CSV; return None if missing/invalid."""
    if raw is None or str(raw).strip() == "":
        return None
    try:
        return float(raw)
    except (TypeError, ValueError):
        return None


def _status_for_row(
    relative_path: str,
    score: float | None,
    duplicate_to_keeper: dict[str, str],
) -> tuple[str, str]:
    """Return (status, dup_photo). dup_photo only set when status is 'dup'."""
    if score is not None and score < POOR_QUALITY_THRESHOLD:
        return "poor quality", ""
    if relative_path in duplicate_to_keeper:
        return "dup", duplicate_to_keeper[relative_path]
    if score is not None:
        if score > 6:
            return "best", ""
        if score > 5:
            return "good", ""
    return "TBD", ""


def write_status_csv(
    image_root: Path,
    rows: list[dict[str, str]],
    duplicate_to_keeper: dict[str, str],
) -> Path:
    """
    Write CSV with same fields as input MUSIQ CSV plus: gps_latitude, gps_longitude,
    date_time_taken, status, dup_photo. Uses POOR_QUALITY_THRESHOLD and score bands for status.
    """
    if not rows:
        return image_root / STATUS_CSV_BASENAME
    paths = [r.get("relative_path", "").strip() for r in rows if r.get("relative_path", "").strip()]
    gps_cache = build_gps_cache(image_root, paths)
    out_path = image_root / STATUS_CSV_BASENAME
    # Input columns (preserve order from first row)
    input_keys = list(rows[0].keys())
    extra_keys = ["gps_latitude", "gps_longitude", "date_time_taken", "status", "dup_photo"]
    fieldnames = input_keys + extra_keys

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            rel = row.get("relative_path", "").strip()
            score = _parse_score(row.get("musiq_score"))
            status, dup_photo = _status_for_row(rel, score, duplicate_to_keeper)
            gps = gps_cache.get(rel) if rel else None
            gps_lat = f"{gps[0]:.6f}" if gps else ""
            gps_lon = f"{gps[1]:.6f}" if gps else ""
            full = image_root / rel if rel else None
            date_time_taken = get_datetime_taken(full) if full and full.is_file() else ""
            out_row = dict(row)
            out_row["gps_latitude"] = gps_lat
            out_row["gps_longitude"] = gps_lon
            out_row["date_time_taken"] = date_time_taken
            out_row["status"] = status
            out_row["dup_photo"] = dup_photo
            writer.writerow(out_row)
    return out_path


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
        help="Write JSON report here: keeper -> list of duplicate paths and duplicate -> keeper",
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
    args = parser.parse_args()

    image_root = args.day_directory.resolve()
    if not image_root.is_dir():
        print(f"Not a directory: {image_root}", file=sys.stderr)
        return 1

    gps_radius = None if args.gps_radius_meters == 0 else args.gps_radius_meters
    try:
        keeper_to_dups, dup_to_keeper = find_duplicates_by_score(
            image_root,
            min_similarity_threshold=args.threshold,
            gps_radius_meters=gps_radius,
            musiq_csv_size=args.musiq_csv_size,
        )
    except ImportError as e:
        print("Install imagededup: pip install imagededup", file=sys.stderr)
        print(f"Error: {e}", file=sys.stderr)
        return 1

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

    if args.output:
        report = {
            "day_directory": str(image_root),
            "musiq_csv_size": args.musiq_csv_size,
            "threshold": args.threshold,
            "gps_radius_meters": args.gps_radius_meters if args.gps_radius_meters != 0 else None,
            "keeper_to_duplicates": keeper_to_dups,
            "duplicate_to_keeper": dup_to_keeper,
        }
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"Wrote report to {args.output}")

    # Write status CSV (same folder as images): MUSIQ CSV fields + gps_latitude, gps_longitude, date_time_taken, status, dup_photo
    musiq_rows = load_full_musiq_csv(image_root, size=args.musiq_csv_size)
    if musiq_rows:
        status_csv_path = write_status_csv(image_root, musiq_rows, dup_to_keeper)
        print(f"Wrote {status_csv_path.name} to {image_root}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
