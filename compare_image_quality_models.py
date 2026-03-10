#!/usr/bin/env python3
"""
Compare image quality scores from three models:
- NIMA (image_evaluator_nima.py -> image_evaluation_nima_results.json)
- CLIP-IQA and MUSIQ (image_evaluator.py -> image_evaluation_results.json)

This script is meant to be run from the backup_pics project directory.

By default it operates on the fixed image directory on the Raspberry Pi:

  /home/dgarrett/Documents/pictures/2024-09_china/2024-09-10

You can override this by passing a different image directory as the first
command-line argument, e.g.:

  python compare_image_quality_models.py /path/to/other/images

If the JSON result files do not exist, it will automatically invoke the
corresponding evaluator scripts to generate them, then perform the comparison.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np


# Default image directory on the Raspberry Pi
DEFAULT_IMAGE_DIR = Path("/home/dgarrett/Documents/pictures/2024-09_china/2024-09-10")

NIMA_DEFAULT_BASENAME = "image_evaluation_nima_results.json"
CLIP_MUSIQ_DEFAULT_BASENAME = "image_evaluation_results.json"


@dataclass
class JoinedRecord:
    relative_path: str
    nima_score: Optional[float]
    clip_iqa_score: Optional[float]
    musiq_score: Optional[float]


def _load_results(path: Path) -> List[dict]:
    if not path.exists():
        raise FileNotFoundError(f"Results file not found: {path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "results" in data:
        return data["results"]
    if isinstance(data, list):
        return data
    raise ValueError(f"Unrecognized JSON structure in {path}")


def _index_by_relative_path(records: List[dict]) -> Dict[str, dict]:
    out: Dict[str, dict] = {}
    for r in records:
        rel = r.get("relative_path")
        if isinstance(rel, str):
            out[rel] = r
    return out


def join_results(
    nima_records: List[dict],
    cm_records: List[dict],
) -> List[JoinedRecord]:
    nima_idx = _index_by_relative_path(nima_records)
    cm_idx = _index_by_relative_path(cm_records)

    common_paths = sorted(set(nima_idx.keys()) & set(cm_idx.keys()))
    joined: List[JoinedRecord] = []
    for rel in common_paths:
        nr = nima_idx[rel]
        cr = cm_idx[rel]
        joined.append(
            JoinedRecord(
                relative_path=rel,
                nima_score=_safe_float(nr.get("nima_score")),
                clip_iqa_score=_safe_float(cr.get("clip_iqa_score")),
                musiq_score=_safe_float(cr.get("musiq_score")),
            )
        )
    return joined


def _safe_float(v) -> Optional[float]:
    if v is None:
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def extract_scores(
    joined: List[JoinedRecord], attr: str
) -> List[Tuple[str, float]]:
    out: List[Tuple[str, float]] = []
    for r in joined:
        score = getattr(r, attr)
        if score is not None:
            out.append((r.relative_path, score))
    return out


def compute_summary_stats(values: List[float]) -> dict:
    if not values:
        return {
            "count": 0,
            "min": None,
            "max": None,
            "mean": None,
            "median": None,
            "std": None,
        }
    vals = list(values)
    return {
        "count": len(vals),
        "min": min(vals),
        "max": max(vals),
        "mean": statistics.mean(vals),
        "median": statistics.median(vals),
        "std": statistics.pstdev(vals) if len(vals) > 1 else 0.0,
    }


def print_stats(name: str, scores: List[Tuple[str, float]]) -> None:
    vals = [s for _, s in scores]
    stats = compute_summary_stats(vals)
    print(f"\n=== {name} score distribution ===")
    print(f"Count  : {stats['count']}")
    print(f"Min    : {stats['min']:.6f}" if stats["min"] is not None else "Min    : None")
    print(f"Max    : {stats['max']:.6f}" if stats["max"] is not None else "Max    : None")
    print(f"Mean   : {stats['mean']:.6f}" if stats["mean"] is not None else "Mean   : None")
    print(f"Median : {stats['median']:.6f}" if stats["median"] is not None else "Median : None")
    print(f"Std    : {stats['std']:.6f}" if stats["std"] is not None else "Std    : None")


def print_top_bottom(
    name: str,
    scores: List[Tuple[str, float]],
    k: int,
) -> Tuple[List[str], List[str]]:
    if not scores:
        print(f"\n=== {name}: no valid scores ===")
        return [], []

    sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)
    top_k = sorted_scores[:k]
    bottom_k = sorted_scores[-k:] if len(sorted_scores) >= k else sorted_scores

    print(f"\n=== {name}: top {len(top_k)} images ===")
    for i, (rel, score) in enumerate(top_k, start=1):
        print(f"{i:2d}. {score:8.6f}  {rel}")

    print(f"\n=== {name}: bottom {len(bottom_k)} images ===")
    for i, (rel, score) in enumerate(bottom_k, start=1):
        print(f"{i:2d}. {score:8.6f}  {rel}")

    top_paths = [rel for rel, _ in top_k]
    bottom_paths = [rel for rel, _ in bottom_k]
    return top_paths, bottom_paths


def pearson_correlation(xs: List[float], ys: List[float]) -> Optional[float]:
    if len(xs) < 2 or len(xs) != len(ys):
        return None
    x_arr = np.array(xs, dtype=float)
    y_arr = np.array(ys, dtype=float)
    if np.allclose(x_arr, x_arr[0]) or np.allclose(y_arr, y_arr[0]):
        return None
    corr = np.corrcoef(x_arr, y_arr)[0, 1]
    return float(corr)


def print_model_correlations(joined: List[JoinedRecord]) -> None:
    pairs = {
        ("NIMA", "CLIP-IQA"): ([], []),
        ("NIMA", "MUSIQ"): ([], []),
        ("CLIP-IQA", "MUSIQ"): ([], []),
    }
    for r in joined:
        if r.nima_score is not None and r.clip_iqa_score is not None:
            pairs[("NIMA", "CLIP-IQA")][0].append(r.nima_score)
            pairs[("NIMA", "CLIP-IQA")][1].append(r.clip_iqa_score)
        if r.nima_score is not None and r.musiq_score is not None:
            pairs[("NIMA", "MUSIQ")][0].append(r.nima_score)
            pairs[("NIMA", "MUSIQ")][1].append(r.musiq_score)
        if r.clip_iqa_score is not None and r.musiq_score is not None:
            pairs[("CLIP-IQA", "MUSIQ")][0].append(r.clip_iqa_score)
            pairs[("CLIP-IQA", "MUSIQ")][1].append(r.musiq_score)

    print("\n=== Pearson correlations between models (same images) ===")
    for (name_a, name_b), (xs, ys) in pairs.items():
        corr = pearson_correlation(xs, ys)
        if corr is None:
            print(f"{name_a} vs {name_b}: not enough variance or data")
        else:
            print(f"{name_a} vs {name_b}: r = {corr:.4f} (n={len(xs)})")


def print_top_overlap(
    model_name_a: str,
    top_a: List[str],
    model_name_b: str,
    top_b: List[str],
) -> None:
    set_a = set(top_a)
    set_b = set(top_b)
    overlap = sorted(set_a & set_b)
    print(f"\n=== Overlap between {model_name_a} and {model_name_b} top images ===")
    print(f"Top-{len(top_a)} of {model_name_a}, Top-{len(top_b)} of {model_name_b}")
    print(f"Overlap count: {len(overlap)}")
    if overlap:
        for rel in overlap:
            print(f" - {rel}")


def print_cross_model_scores_for_top(
    label: str,
    top_paths: List[str],
    joined_by_path: Dict[str, JoinedRecord],
) -> None:
    print(f"\n=== Cross-model scores for {label} ===")
    print("Idx  NIMA        CLIP-IQA   MUSIQ      Image")
    print("---- ----------  ---------  ---------  -----")
    for i, rel in enumerate(top_paths, start=1):
        rec = joined_by_path.get(rel)
        if not rec:
            continue
        ns = f"{rec.nima_score:.6f}" if rec.nima_score is not None else "   None "
        cs = f"{rec.clip_iqa_score:.6f}" if rec.clip_iqa_score is not None else "   None "
        ms = f"{rec.musiq_score:.6f}" if rec.musiq_score is not None else "   None "
        print(f"{i:2d}. {ns:10s}  {cs:9s}  {ms:9s}  {rel}")


def run_command(cmd: List[str], cwd: Path) -> None:
    print(f"\nRunning command: {' '.join(cmd)}")
    try:
        completed = subprocess.run(
            cmd,
            cwd=str(cwd),
            check=False,
        )
    except Exception as e:
        print(f"Failed to start command: {e}")
        sys.exit(1)
    if completed.returncode != 0:
        print(f"Command failed with exit code {completed.returncode}")
        sys.exit(completed.returncode)


def ensure_results_file(
    json_path: Path,
    image_root: Path,
    evaluator_script: str,
) -> None:
    """
    Ensure json_path exists. If not, run the given evaluator script:
      python evaluator_script <image_root> --output json_path

    evaluator_script is resolved relative to this script if not absolute.
    """
    if json_path.exists():
        print(f"{json_path.name} already exists; using existing results.")
        return

    script_path = Path(evaluator_script)
    if not script_path.is_absolute():
        here = Path(__file__).resolve().parent
        candidate = here / evaluator_script
        if candidate.exists():
            script_path = candidate

    print(f"{json_path.name} not found. Generating it with {script_path} ...")

    cmd = [sys.executable, str(script_path), str(image_root), "--output", str(json_path)]
    # Run from this project directory (where this script lives)
    project_dir = Path(__file__).resolve().parent
    run_command(cmd, cwd=project_dir)

    if not json_path.exists():
        print(f"Expected results file was not created: {json_path}")
        sys.exit(1)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare NIMA, CLIP-IQA, and MUSIQ results for a directory of images. "
            "If JSON result files are missing, run the evaluator scripts first."
        )
    )
    parser.add_argument(
        "image_directory",
        nargs="?",
        type=Path,
        default=DEFAULT_IMAGE_DIR,
        help=(
            "Directory containing the JPEG images and where results JSON files "
            "will be written/read. Defaults to the China 2024-09-10 directory."
        ),
    )
    args = parser.parse_args()

    # Resolve image directory (either default or user-provided)
    image_root = args.image_directory.resolve()
    if not image_root.exists():
        print(f"Image directory does not exist: {image_root}")
        return 1

    nima_path = (image_root / NIMA_DEFAULT_BASENAME).resolve()
    cm_path = (image_root / CLIP_MUSIQ_DEFAULT_BASENAME).resolve()

    print(f"Image directory : {image_root}")
    print(f"NIMA JSON       : {nima_path}")
    print(f"CLIP/MUSIQ JSON: {cm_path}")

    # Ensure JSONs exist; if not, run evaluators from the project directory.
    ensure_results_file(
        nima_path,
        image_root,
        evaluator_script="image_evaluator_nima.py",
    )
    ensure_results_file(
        cm_path,
        image_root,
        evaluator_script="image_evaluator.py",
    )

    try:
        nima_records = _load_results(nima_path)
        cm_records = _load_results(cm_path)
    except Exception as e:
        print(f"Failed to load results: {e}")
        return 1

    joined = join_results(nima_records, cm_records)
    if not joined:
        print("No overlapping images found between NIMA and CLIP/MUSIQ results (by relative_path).")
        return 1

    print(f"\nTotal images in NIMA results       : {len(nima_records)}")
    print(f"Total images in CLIP/MUSIQ results : {len(cm_records)}")
    print(f"Images present in both (analyzed)  : {len(joined)}")

    # Build per-model score lists
    nima_scores = extract_scores(joined, "nima_score")
    clip_scores = extract_scores(joined, "clip_iqa_score")
    musiq_scores = extract_scores(joined, "musiq_score")

    # Distribution stats
    print_stats("NIMA", nima_scores)
    print_stats("CLIP-IQA", clip_scores)
    print_stats("MUSIQ", musiq_scores)

    # Top and bottom images per model
    top_k = 5
    nima_top, nima_bottom = print_top_bottom("NIMA", nima_scores, top_k)
    clip_top, clip_bottom = print_top_bottom("CLIP-IQA", clip_scores, top_k)
    musiq_top, musiq_bottom = print_top_bottom("MUSIQ", musiq_scores, top_k)

    # Correlations
    print_model_correlations(joined)

    # Overlaps in top images
    print_top_overlap("NIMA", nima_top, "CLIP-IQA", clip_top)
    print_top_overlap("NIMA", nima_top, "MUSIQ", musiq_top)
    print_top_overlap("CLIP-IQA", clip_top, "MUSIQ", musiq_top)

    # Cross-model scores for each model's favorites
    joined_by_path = {r.relative_path: r for r in joined}
    print_cross_model_scores_for_top("NIMA top images", nima_top, joined_by_path)
    print_cross_model_scores_for_top("CLIP-IQA top images", clip_top, joined_by_path)
    print_cross_model_scores_for_top("MUSIQ top images", musiq_top, joined_by_path)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

