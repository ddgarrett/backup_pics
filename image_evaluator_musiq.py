#!/usr/bin/env python3
"""
Image Evaluator (MUSIQ only) — evaluate images (e.g. 4080×3071 JPEGs) with MUSIQ.

Takes a directory path, walks main and subdirectories for JPEGs, and saves CSV
results. Supports evaluating at multiple resize max-sizes in a single run; for
each max-size value, a separate CSV file is written whose name is suffixed
with the max-size (e.g. 1024.csv).

Usage examples:

  # Default, evaluate with TensorFlow MUSIQ at max-size 1024 only
  python image_evaluator_musiq.py /path/to/images

  # Evaluate at multiple sizes (e.g. 256, 512, full-res)
  python image_evaluator_musiq.py /path/to/images --max-size 256 512 0

  # Custom output prefix
  python image_evaluator_musiq.py /path/to/images --output-prefix my_musiq_results
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from image_analysis_lib import musiq
from image_analysis_lib.config import default_config


# Default CSV basename prefix
DEFAULT_RESULTS_PREFIX = default_config.musiq_csv_prefix


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate images with MUSIQ only (TensorFlow); save CSV results for one "
            "or more resize max-size values (separate CSV per size)."
        )
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Root directory to scan for JPEGs (main and subdirectories).",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        nargs="+",
        default=[1024],
        metavar="N",
        help=(
            "One or more max-size values in pixels for resizing the longest side. "
            "Use 0 for full resolution (no resize). Default: 1024."
        ),
    )
    parser.add_argument(
        "--output-prefix",
        type=str,
        default=DEFAULT_RESULTS_PREFIX,
        help=(
            "Prefix for output CSV files. For each max-size value, a CSV named "
            "<prefix>_<size>.csv will be created in the directory being evaluated."
        ),
    )
    return parser.parse_args(argv)


def main(argv: Optional[List[str]] = None) -> int:
    args = parse_args(argv)

    root = args.directory.resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 1

    images = musiq.find_jpeg_files(root)
    print(f"Found {len(images)} JPEG image(s) under {root}")

    max_sizes = [int(v) for v in args.max_size]
    musiq.write_scores_csv_for_sizes(
        root=root,
        images=images,
        max_sizes=max_sizes,
        output_prefix=args.output_prefix,
        config=default_config,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

