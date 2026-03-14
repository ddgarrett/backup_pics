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
import csv
import json
import sys
from pathlib import Path

# image_evaluator_musiq.py output: prefix_size.csv (e.g. image_evaluation_musiq_results_1024.csv)
MUSIQ_CSV_PREFIX = "image_evaluation_musiq_results"
MUSIQ_CSV_DEFAULT_SIZE = 1024

# Score below this: "poor quality", excluded from duplicate checking
POOR_QUALITY_THRESHOLD = 4.0

# Approximate meters per degree (flat-earth; fine for ~200 m)
_METERS_PER_DEG_LAT = 111_320


# exifread tag names: "IFD TagName" (same as process_images/image_collection_metadata.csv).
# GPS: standard EXIF only defines GPSLatitude/GPSLongitude + Ref; we try these.
# DateTime: try in order; add EXIF DateTimeDigitized and GPS GPSDateStamp as fallbacks.
_EXIFREAD_LAT_TAGS = ["GPS GPSLatitude", "GPS GPSLatitudeRef"]
_EXIFREAD_LON_TAGS = ["GPS GPSLongitude", "GPS GPSLongitudeRef"]
_EXIFREAD_DATETIME_TAGS = [
    "EXIF DateTimeOriginal",
    "EXIF DateTimeDigitized",
    "Image DateTime",
    "GPS GPSDate",
    "GPS GPSDateStamp",
]
# Camera, dimensions, orientation, exposure (from process_images/image_collection_metadata.csv + EXIF standard)
_EXIFREAD_MAKE_TAGS = ["Image Make"]
_EXIFREAD_MODEL_TAGS = ["Image Model"]
_EXIFREAD_IMAGE_WIDTH_TAGS = ["Image ImageWidth", "EXIF ExifImageWidth"]
_EXIFREAD_IMAGE_LENGTH_TAGS = ["Image ImageLength", "EXIF ExifImageLength"]
_EXIFREAD_ORIENTATION_TAGS = ["Image Orientation"]
_EXIFREAD_EXPOSURE_TIME_TAGS = ["EXIF ExposureTime"]
_EXIFREAD_FNUMBER_TAGS = ["EXIF FNumber"]
_EXIFREAD_ISO_SPEED_TAGS = ["EXIF ISOSpeedRatings"]


def _exifread_component_to_float(v) -> float:
    """Convert one DMS component from exifread (Rational or number) to float."""
    if v is None:
        return 0.0
    if hasattr(v, "num") and hasattr(v, "den"):
        return float(v.num) / float(v.den) if v.den else 0.0
    try:
        return float(v)
    except (TypeError, ValueError):
        return 0.0


def _exifread_first_value(tags: dict, tag_names: list[str]) -> str:
    """Return first found tag value as string; empty string if none. Handles .values and rationals."""
    for name in tag_names:
        if name not in tags:
            continue
        tag = tags[name]
        if not hasattr(tag, "values"):
            return str(tag)
        val = tag.values
        if isinstance(val, (list, tuple)):
            if len(val) == 1:
                val = val[0]
            elif len(val) == 2:
                n = _exifread_component_to_float(val[0])
                d = _exifread_component_to_float(val[1])
                if not d:
                    return str(int(n)) if n == int(n) else str(n)
                if n == int(n) and d == int(d) and int(d) > 1:
                    return f"{int(n)}/{int(d)}"
                return f"{n / d:.4g}"
        if val is None:
            return ""
        if hasattr(val, "num") and hasattr(val, "den"):
            return str(_exifread_component_to_float(val))
        return str(val)
    return ""


def get_exif_extras(image_path: Path) -> dict[str, str]:
    """
    Read camera, dimensions, orientation, exposure from EXIF via exifread.
    Returns dict with keys: img_make, img_model, exif_image_width, exif_image_length,
    img_orientation, exif_exposure_time, exif_f_number, exif_iso_speed_ratings.
    """
    out: dict[str, str] = {
        "img_make": "",
        "img_model": "",
        "exif_image_width": "",
        "exif_image_length": "",
        "img_orientation": "",
        "exif_exposure_time": "",
        "exif_f_number": "",
        "exif_iso_speed_ratings": "",
    }
    try:
        import exifread
        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
    except Exception:
        return out
    out["img_make"] = _exifread_first_value(tags, _EXIFREAD_MAKE_TAGS)
    out["img_model"] = _exifread_first_value(tags, _EXIFREAD_MODEL_TAGS)
    out["exif_image_width"] = _exifread_first_value(tags, _EXIFREAD_IMAGE_WIDTH_TAGS)
    out["exif_image_length"] = _exifread_first_value(tags, _EXIFREAD_IMAGE_LENGTH_TAGS)
    out["img_orientation"] = _exifread_first_value(tags, _EXIFREAD_ORIENTATION_TAGS)
    out["exif_exposure_time"] = _exifread_first_value(tags, _EXIFREAD_EXPOSURE_TIME_TAGS)
    out["exif_f_number"] = _exifread_first_value(tags, _EXIFREAD_FNUMBER_TAGS)
    out["exif_iso_speed_ratings"] = _exifread_first_value(tags, _EXIFREAD_ISO_SPEED_TAGS)
    return out


def get_gps_from_exif(image_path: Path) -> tuple[float, float] | None:
    """
    Read EXIF GPS using exifread; tag names from process_images/image_collection_metadata.csv (img_lat / img_lon).
    """
    try:
        import exifread
    except ImportError:
        return None
    try:
        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
    except Exception:
        return None
    lat_tag = next((t for t in _EXIFREAD_LAT_TAGS if t in tags and "Ref" not in t), None)
    lat_ref_tag = next((t for t in _EXIFREAD_LAT_TAGS if t in tags and "Ref" in t), None)
    lon_tag = next((t for t in _EXIFREAD_LON_TAGS if t in tags and "Ref" not in t), None)
    lon_ref_tag = next((t for t in _EXIFREAD_LON_TAGS if t in tags and "Ref" in t), None)
    if not lat_tag or not lon_tag:
        return None
    try:
        lat_vals = tags[lat_tag].values
        lon_vals = tags[lon_tag].values
        if len(lat_vals) != 3 or len(lon_vals) != 3:
            return None
        lat_dec = _exifread_component_to_float(lat_vals[0]) + _exifread_component_to_float(lat_vals[1]) / 60.0 + _exifread_component_to_float(lat_vals[2]) / 3600.0
        lon_dec = _exifread_component_to_float(lon_vals[0]) + _exifread_component_to_float(lon_vals[1]) / 60.0 + _exifread_component_to_float(lon_vals[2]) / 3600.0
        lat_ref = tags.get(lat_ref_tag)
        lon_ref = tags.get(lon_ref_tag)
        if lat_ref is not None and hasattr(lat_ref, "values"):
            ref_val = lat_ref.values
            ref_s = ref_val[0] if ref_val else "N"
            if ref_s in ("S", "s"):
                lat_dec = -lat_dec
        if lon_ref is not None and hasattr(lon_ref, "values"):
            ref_val = lon_ref.values
            ref_s = ref_val[0] if ref_val else "E"
            if ref_s in ("W", "w"):
                lon_dec = -lon_dec
        return (lat_dec, lon_dec)
    except (KeyError, TypeError, IndexError, ZeroDivisionError):
        return None


def _debug_print_gps_ifd(image_path: Path) -> None:
    """Print raw GPS tags using exifread for debugging."""
    try:
        import exifread
        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
        gps_tags = [(k, v) for k, v in tags.items() if k.startswith("GPS ")]
        if not gps_tags:
            print(f"  [debug-gps] No GPS tags in {image_path}", file=sys.stderr)
            return
        print(f"  [debug-gps] GPS tags:", file=sys.stderr)
        for name, tag in gps_tags:
            if hasattr(tag, "values"):
                print(f"    {name}: {tag.values}", file=sys.stderr)
            else:
                print(f"    {name}: {tag!r}", file=sys.stderr)
    except Exception as e:
        print(f"  [debug-gps] Error: {e}", file=sys.stderr)


def distance_meters_flat(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distance between two (lat, lon) points in meters (flat-earth; fine for ~200 m)."""
    import math

    dlat_deg = lat2 - lat1
    dlon_deg = lon2 - lon1
    lat_mid_rad = math.radians((lat1 + lat2) / 2)
    dlat_m = dlat_deg * _METERS_PER_DEG_LAT
    dlon_m = dlon_deg * _METERS_PER_DEG_LAT * math.cos(lat_mid_rad)
    return math.sqrt(dlat_m * dlat_m + dlon_m * dlon_m)


def build_gps_cache(image_root: Path, relative_paths: list[str]) -> dict[str, tuple[float, float] | None]:
    """Return map relative_path -> (lat, lon) or None if no GPS."""
    out: dict[str, tuple[float, float] | None] = {}
    for rel in relative_paths:
        full = image_root / rel
        out[rel] = get_gps_from_exif(full) if full.is_file() else None
    return out


def get_datetime_taken(image_path: Path) -> str:
    """
    Return date/time the photo was taken using exifread; tag names from
    process_images/image_collection_metadata.csv img_date_time exif_tags
    (EXIF DateTimeOriginal, Image DateTime, GPS GPSDate). Fallback: file mtime (ISO).
    """
    try:
        import exifread
        with open(image_path, "rb") as f:
            tags = exifread.process_file(f, details=False)
        for tag_name in _EXIFREAD_DATETIME_TAGS:
            if tag_name not in tags:
                continue
            tag = tags[tag_name]
            if not hasattr(tag, "values"):
                continue
            val = tag.values
            if isinstance(val, (list, tuple)) and len(val) == 1:
                val = val[0]
            if not val:
                continue
            s = str(val).strip()
            if len(s) >= 19 and ":" in s:
                date_part = s[:10].replace(":", "-")
                time_part = s[11:19]
                return f"{date_part}T{time_part}"
            return s
    except Exception:
        pass
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
    verbose: bool = False,
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
        keeper_score = ordered[keeper_idx][1]
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
                    dist = distance_meters_flat(keeper_gps[0], keeper_gps[1], other_gps[0], other_gps[1])
                    if dist > gps_radius_meters:
                        continue  # too far; don't run duplicate test

            sim = cosine_similarity(keeper_enc, encodings[other_path])
            if sim >= min_similarity_threshold:
                duplicate_to_keeper[other_path] = keeper_path
                keeper_to_duplicates.setdefault(keeper_path, []).append(other_path)

        if verbose:
            n_dups = len(keeper_to_duplicates.get(keeper_path, []))
            print(f"  Processing highest-scoring image (score {keeper_score:.4f}): {keeper_path} - {n_dups} duplicate(s) found")

    if verbose:
        n_dups = len(duplicate_to_keeper)
        n_remain = len(ordered) - n_dups
        print(f"  Duplicates found: {n_dups}")
        print(f"  Non-duplicate images remaining: {n_remain}")

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


_EXIF_EXTRAS_KEYS = [
    "img_make",
    "img_model",
    "exif_image_width",
    "exif_image_length",
    "img_orientation",
    "exif_exposure_time",
    "exif_f_number",
    "exif_iso_speed_ratings",
]


def write_status_csv(
    image_root: Path,
    rows: list[dict[str, str]],
    duplicate_to_keeper: dict[str, str],
) -> Path:
    """
    Write CSV with same fields as input MUSIQ CSV plus: gps_latitude, gps_longitude,
    date_time_taken, EXIF extras (make, model, dimensions, orientation, exposure), status, dup_photo.
    """
    if not rows:
        return image_root / STATUS_CSV_BASENAME
    paths = [r.get("relative_path", "").strip() for r in rows if r.get("relative_path", "").strip()]
    gps_cache = build_gps_cache(image_root, paths)
    extras_cache: dict[str, dict[str, str]] = {}
    for rel in paths:
        full = image_root / rel if rel else None
        extras_cache[rel] = get_exif_extras(full) if full and full.is_file() else {k: "" for k in _EXIF_EXTRAS_KEYS}
    out_path = image_root / STATUS_CSV_BASENAME
    input_keys = list(rows[0].keys())
    extra_keys = [
        "gps_latitude", "gps_longitude", "date_time_taken",
        * _EXIF_EXTRAS_KEYS,
        "status", "dup_photo",
    ]
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
            extras = extras_cache.get(rel) or {k: "" for k in _EXIF_EXTRAS_KEYS}
            out_row = dict(row)
            out_row["gps_latitude"] = gps_lat
            out_row["gps_longitude"] = gps_lon
            out_row["date_time_taken"] = date_time_taken
            for k in _EXIF_EXTRAS_KEYS:
                out_row[k] = extras.get(k, "")
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
        "--verbose",
        "-v",
        action="store_true",
        help="Show progress: directory, picture counts, highest-scoring images as processed, duplicate and non-duplicate counts.",
    )
    parser.add_argument(
        "--debug-gps",
        action="store_true",
        help="Print raw GPS EXIF for the first image (to debug missing coordinates, e.g. Pixel phone).",
    )
    args = parser.parse_args()

    image_root = args.day_directory.resolve()
    if not image_root.is_dir():
        print(f"Not a directory: {image_root}", file=sys.stderr)
        return 1

    # Default: save outputs in the same directory as the photos
    report_path = args.output if args.output is not None else image_root / "scene_duplicates_report.json"

    musiq_rows = load_full_musiq_csv(image_root, size=args.musiq_csv_size)
    if args.debug_gps and musiq_rows:
        first_rel = musiq_rows[0].get("relative_path", "").strip()
        if first_rel:
            print(f"[debug-gps] First image: {first_rel}", file=sys.stderr)
            _debug_print_gps_ifd(image_root / first_rel)
    if args.verbose:
        print(f"Processing directory: {image_root}")
        print(f"Pictures found in MUSIQ score CSV: {len(musiq_rows)}")
        scores = load_scores(image_root, musiq_csv_size=args.musiq_csv_size)
        n_rejected = sum(1 for _, s in scores.items() if s is not None and s < POOR_QUALITY_THRESHOLD)
        print(f"Pictures rejected (poor quality, score < {POOR_QUALITY_THRESHOLD}): {n_rejected}")
        if scores:
            print("Checking for duplicates (highest-scoring images first):")

    gps_radius = None if args.gps_radius_meters == 0 else args.gps_radius_meters
    try:
        keeper_to_dups, dup_to_keeper = find_duplicates_by_score(
            image_root,
            min_similarity_threshold=args.threshold,
            gps_radius_meters=gps_radius,
            musiq_csv_size=args.musiq_csv_size,
            verbose=args.verbose,
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
        status_csv_path = write_status_csv(image_root, musiq_rows, dup_to_keeper)
        print(f"Wrote {status_csv_path.name} (all fields) to {image_root}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
