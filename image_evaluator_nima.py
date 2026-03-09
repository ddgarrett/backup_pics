#!/usr/bin/env python3
"""
Image Evaluator (NIMA) — evaluate images (e.g. 4080×3071 JPEGs, 2–4 MB) with NIMA.

Takes a directory path, walks main and subdirectories for JPEGs, and saves detailed
evaluation results to a .json file. Writes the JSON after each image so that if the
process is stopped, no data is lost. Re-runs only process images not previously evaluated.

Usage:
  python image_evaluator_nima.py /path/to/images
  python image_evaluator_nima.py /path/to/images --output results_nima.json
  python image_evaluator_nima.py /path/to/images --device cuda
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import numpy as np

# Image discovery and loading
try:
    from PIL import Image
except ImportError:
    print("Install Pillow: pip install Pillow", file=sys.stderr)
    sys.exit(1)

# NIMA via pyiqa (uses PyTorch)
try:
    import torch
    import pyiqa
except ImportError as e:
    print("Install PyTorch and pyiqa for NIMA: pip install torch pyiqa", file=sys.stderr)
    sys.exit(1)

# Result file name (stored in the evaluated directory)
DEFAULT_RESULTS_BASENAME = "image_evaluation_nima_results.json"
# JPEG extensions
JPEG_EXTENSIONS = {".jpg", ".jpeg", ".JPG", ".JPEG"}


def find_jpeg_files(root: Path) -> list[Path]:
    """Return all JPEG file paths under root (main and subdirectories)."""
    out = []
    for p in root.rglob("*"):
        if p.is_file() and p.suffix in JPEG_EXTENSIONS:
            out.append(p)
    return sorted(out)


def relative_path(path: Path, root: Path) -> str:
    """Path relative to root, using forward slashes."""
    return path.relative_to(root).as_posix()


def collect_file_info(image_path: Path, root: Path) -> dict:
    """Basic file and image metadata."""
    stat = image_path.stat()
    try:
        with Image.open(image_path) as img:
            w, h = img.size
    except Exception:
        w, h = None, None
    return {
        "relative_path": relative_path(image_path, root),
        "file_size_bytes": stat.st_size,
        "file_size_mb": round(stat.st_size / (1024 * 1024), 4),
        "width": w,
        "height": h,
    }


def evaluate_nima(image_path: Path, nima_metric, device: str) -> dict:
    """
    Run NIMA on one image. Returns dict with nima_score, nima_details, nima_error.
    Uses pyiqa, which returns a PyTorch tensor (scalar or small vector).
    """
    try:
        # pyiqa accepts image path (str or Path)
        out = nima_metric(str(image_path))

        # Convert whatever we got to a PyTorch tensor on CPU
        if isinstance(out, (int, float)):
            score = float(out)
            details = {"mean": score, "raw": score}
        else:
            # Tensor, numpy array, or list -> tensor
            if hasattr(out, "detach"):
                t = out.detach().cpu()
            else:
                t = torch.as_tensor(out)
            t = t.float().cpu()

            if t.ndim == 0:
                score = float(t.item())
                details = {"mean": score, "raw": float(t.item())}
            else:
                flat = t.view(-1)
                # If we have exactly 10 values, treat as NIMA distribution over scores 1..10
                if flat.numel() == 10:
                    probs = flat / (flat.sum() + 1e-8)
                    ratings = torch.arange(1, 11, dtype=probs.dtype)
                    score = float((probs * ratings).sum().item())
                    details = {
                        "mean": score,
                        "probs": probs.tolist(),
                        "raw": flat.tolist(),
                    }
                else:
                    # Fallback: average all values
                    score = float(flat.mean().item())
                    details = {
                        "mean": score,
                        "raw": flat.tolist(),
                    }

        return {
            "nima_score": round(score, 6) if score is not None else None,
            "nima_details": details,
            "nima_error": None,
        }
    except Exception as e:
        return {
            "nima_score": None,
            "nima_details": None,
            "nima_error": str(e),
        }


def load_existing_results(results_path: Path) -> dict[str, dict]:
    """Load existing results JSON: map relative_path -> record."""
    if not results_path.exists():
        return {}
    try:
        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    if isinstance(data, dict) and "results" in data:
        list_results = data["results"]
    elif isinstance(data, list):
        list_results = data
    else:
        return {}
    return {r["relative_path"]: r for r in list_results if "relative_path" in r}


def compute_stats(records: list[dict]) -> dict:
    """Compute basic stats for evaluation times and NIMA scores from results list."""
    times_sec = []
    scores = []
    for r in records:
        t = r.get("evaluation_time_seconds")
        if t is not None:
            try:
                times_sec.append(float(t))
            except (TypeError, ValueError):
                pass
        s = r.get("nima_score")
        if s is not None:
            try:
                scores.append(float(s))
            except (TypeError, ValueError):
                pass

    def stats(values: list[float]) -> dict:
        if not values:
            return {"count": 0, "min": None, "max": None, "mean": None, "std": None}
        n = len(values)
        mean = sum(values) / n
        variance = sum((x - mean) ** 2 for x in values) / n if n > 0 else 0
        std = variance ** 0.5
        return {
            "count": n,
            "min": round(min(values), 6),
            "max": round(max(values), 6),
            "mean": round(mean, 6),
            "std": round(std, 6),
        }

    return {
        "evaluation_times_seconds": stats(times_sec),
        "nima_scores": stats(scores),
    }


def save_results(results_path: Path, records: list[dict], root: Path) -> None:
    """
    Write full results JSON with metadata and stats.
    Saves after each image so that stopping the process loses no data.
    Uses atomic write (temp + rename).
    total_run_time_seconds is computed as sum of evaluation_time_seconds across all records.
    """
    stats_dict = compute_stats(records)
    total_run_time_seconds = (
        sum(r.get("evaluation_time_seconds") or 0 for r in records) if records else None
    )
    payload = {
        "directory": str(root.resolve()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_images": len(records),
        "total_run_time_seconds": round(total_run_time_seconds, 4) if total_run_time_seconds is not None else None,
        "stats": stats_dict,
        "results": records,
    }
    tmp_path = results_path.with_suffix(results_path.suffix + ".tmp")
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)
        f.flush()
        os.fsync(f.fileno())
    tmp_path.replace(results_path)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate images with NIMA; save detailed results (incremental by path, save after each image)."
    )
    parser.add_argument(
        "directory",
        type=Path,
        help="Root directory to scan for JPEGs (main and subdirectories)",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help=f"Results JSON path (default: <directory>/{DEFAULT_RESULTS_BASENAME})",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
        choices=("cpu", "cuda", "mps"),
        help="Device for NIMA (PyTorch)",
    )
    args = parser.parse_args()

    root = args.directory.resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 1

    results_path = (args.output or root / DEFAULT_RESULTS_BASENAME).resolve()
    existing = load_existing_results(results_path)

    all_jpegs = find_jpeg_files(root)
    to_process = [p for p in all_jpegs if relative_path(p, root) not in existing]
    print(f"Found {len(all_jpegs)} JPEG(s); {len(to_process)} new to process.")

    # Create NIMA metric once and reuse
    try:
        nima_metric = pyiqa.create_metric("nima", device=args.device)
    except Exception as e:
        print(f"Failed to create NIMA metric: {e}", file=sys.stderr)
        return 1

    results_by_path = dict(existing)
    order = [relative_path(p, root) for p in all_jpegs]
    ordered_records = [results_by_path[r] for r in order if r in results_by_path]

    for i, image_path in enumerate(to_process):
        rel = relative_path(image_path, root)
        print(f"[{i+1}/{len(to_process)}] {rel}")

        rec = collect_file_info(image_path, root)
        rec["evaluated_at"] = datetime.now(timezone.utc).isoformat()

        t0 = time.perf_counter()
        nima_out = evaluate_nima(image_path, nima_metric, args.device)
        elapsed = time.perf_counter() - t0

        rec["evaluation_time_seconds"] = round(elapsed, 4)
        rec.update(nima_out)

        results_by_path[rel] = rec
        ordered_records = [results_by_path[r] for r in order if r in results_by_path]

        save_results(results_path, ordered_records, root)
        print(f"  -> NIMA: {rec.get('nima_score')}, {elapsed:.2f}s - saved ({len(ordered_records)} results)")

    # If nothing was processed this run, refresh JSON once with current stats and total run time from all records
    if not to_process and ordered_records:
        save_results(results_path, ordered_records, root)

    print(f"Done. {results_path} has {len(ordered_records)} images.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
