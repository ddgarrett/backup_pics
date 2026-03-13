#!/usr/bin/env python3
"""
Image Evaluator (MUSIQ only) — evaluate images (e.g. 4080×3071 JPEGs) with MUSIQ.

Takes a directory path, walks main and subdirectories for JPEGs, and saves CSV
results. Supports evaluating at multiple resize max-sizes in a single run; for
each max-size value, a separate CSV file is written whose name is suffixed
with the max-size (e.g. image_evaluation_musiq_results_512.csv).

Usage examples:

  # Default, evaluate with TensorFlow MUSIQ at max-size 512 only
  python image_evaluator_musiq.py /path/to/images

  # Evaluate at multiple sizes (e.g. 256, 512, full-res)
  python image_evaluator_musiq.py /path/to/images --max-size 256 512 0

  # Custom output prefix
  python image_evaluator_musiq.py /path/to/images --output-prefix my_musiq_results
"""

from __future__ import annotations

import argparse
import csv
import io
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, List, Optional

import numpy as np

try:
    from PIL import Image
except ImportError:
    print("Install Pillow: pip install Pillow", file=sys.stderr)
    sys.exit(1)

try:
    import tensorflow as tf
    import tensorflow_hub as hub
except ImportError:
    print(
        "Install TensorFlow and TensorFlow Hub for MUSIQ: "
        "pip install tensorflow tensorflow_hub",
        file=sys.stderr,
    )
    sys.exit(1)


# Default CSV basename prefix
DEFAULT_RESULTS_PREFIX = "image_evaluation_musiq_results"
# JPEG extensions
JPEG_EXTENSIONS = {".jpg", ".jpeg", ".JPG", ".JPEG"}

_MUSIQ_TF = None


def _load_musiq_tf():
    """Lazy-load MUSIQ via TensorFlow Hub."""
    global _MUSIQ_TF
    if _MUSIQ_TF is not None:
        return _MUSIQ_TF
    # Official TF Hub model (AVA-trained, score 1–10)
    model = hub.load("https://tfhub.dev/google/musiq/ava/1")
    _MUSIQ_TF = model.signatures["serving_default"]
    return _MUSIQ_TF


def _resize_image(img: Image.Image, max_size: int) -> Image.Image:
    """Resize so longest side is at most max_size, keeping aspect ratio."""
    w, h = img.size
    if max(w, h) <= max_size:
        return img
    if w >= h:
        new_w, new_h = max_size, int(round(h * max_size / w))
    else:
        new_w, new_h = int(round(w * max_size / h)), max_size
    return img.resize((new_w, new_h), Image.Resampling.LANCZOS)


def _image_to_jpeg_bytes(path: Path, max_size: Optional[int] = None, quality: int = 85) -> bytes:
    """Load image, optionally resize, return as JPEG bytes (for MUSIQ)."""
    img = Image.open(path).convert("RGB")
    if max_size is not None and max_size > 0:
        img = _resize_image(img, max_size)
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=quality, optimize=False)
    return buf.getvalue()


def evaluate_musiq_tf(image_path: Path, max_size: Optional[int] = None) -> dict:
    """Run MUSIQ via TensorFlow Hub on one image (raw bytes)."""
    try:
        image_bytes = _image_to_jpeg_bytes(image_path, max_size=max_size)
        predict_fn = _load_musiq_tf()
        inp = tf.constant(image_bytes)
        out = predict_fn(inp)
        # Output may be dict with key like 'output_0' or 'predictions'
        if isinstance(out, dict):
            v = next(iter(out.values()))
        else:
            v = out
        score = float(tf.squeeze(v).numpy())
        return {"musiq_score": round(score, 4), "musiq_error": None}
    except Exception as e:  # noqa: BLE001
        return {"musiq_score": None, "musiq_error": str(e)}


def find_jpeg_files(root: Path) -> List[Path]:
    """Return all JPEG file paths under root (main and subdirectories)."""
    out: List[Path] = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in JPEG_EXTENSIONS:
            out.append(p)
    return sorted(out)


def relative_path(path: Path, root: Path) -> str:
    """Path relative to root, using forward slashes."""
    return path.relative_to(root).as_posix()


@dataclass
class ImageInfo:
    relative_path: str
    file_size_bytes: int
    file_size_mb: float
    width: Optional[int]
    height: Optional[int]


def collect_file_info(image_path: Path, root: Path) -> ImageInfo:
    """Basic file and image metadata."""
    stat = image_path.stat()
    try:
        with Image.open(image_path) as img:
            w, h = img.size
    except Exception:  # noqa: BLE001
        w, h = None, None
    return ImageInfo(
        relative_path=relative_path(image_path, root),
        file_size_bytes=stat.st_size,
        file_size_mb=round(stat.st_size / (1024 * 1024), 4),
        width=w,
        height=h,
    )


def run_musiq_for_sizes(
    root: Path,
    images: Iterable[Path],
    max_sizes: List[int],
    output_prefix: str,
) -> None:
    """
    Evaluate MUSIQ for each image at each requested max-size, writing one CSV per size.
    max_size == 0 means full resolution (no resize).
    """
    images = list(images)
    if not images:
        print("No JPEG images found; nothing to do.")
        return

    for max_size in max_sizes:
        size_label = "full" if max_size == 0 else str(max_size)
        csv_name = f"{output_prefix}_{size_label}.csv"
        csv_path = root / csv_name
        print(f"\nEvaluating MUSIQ at max-size={max_size} ({size_label})")
        print(f"Writing results to {csv_path}")

        total_time = 0.0
        count = 0

        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(
                [
                    "relative_path",
                    "file_size_bytes",
                    "file_size_mb",
                    "width",
                    "height",
                    "evaluated_at",
                    "evaluation_time_seconds",
                    "max_size",
                    "musiq_score",
                    "musiq_error",
                ]
            )

            for i, img_path in enumerate(images, start=1):
                info = collect_file_info(img_path, root)
                print(f"[{i}/{len(images)}] {info.relative_path}")

                t0 = time.perf_counter()
                musiq_out = evaluate_musiq_tf(
                    img_path,
                    max_size=max_size if max_size > 0 else None,
                )
                elapsed = time.perf_counter() - t0

                total_time += elapsed
                count += 1

                evaluated_at = datetime.now(timezone.utc).isoformat()
                writer.writerow(
                    [
                        info.relative_path,
                        info.file_size_bytes,
                        f"{info.file_size_mb:.4f}",
                        info.width if info.width is not None else "",
                        info.height if info.height is not None else "",
                        evaluated_at,
                        f"{elapsed:.4f}",
                        max_size,
                        musiq_out["musiq_score"] if musiq_out["musiq_score"] is not None else "",
                        musiq_out["musiq_error"] or "",
                    ]
                )

        avg_time = total_time / count if count > 0 else 0.0
        print(
            f"Done for max-size={max_size}. {count} images, "
            f"avg eval time: {avg_time:.4f}s. Results: {csv_path}"
        )


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
        default=[512],
        metavar="N",
        help=(
            "One or more max-size values in pixels for resizing the longest side. "
            "Use 0 for full resolution (no resize). Default: 512."
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

    images = find_jpeg_files(root)
    print(f"Found {len(images)} JPEG image(s) under {root}")

    max_sizes = [int(v) for v in args.max_size]
    run_musiq_for_sizes(
        root,
        images,
        max_sizes,
        args.output_prefix,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

