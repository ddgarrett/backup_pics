#!/usr/bin/env python3
"""
Image Evaluator — evaluate images (e.g. 4080×3071 JPEGs, 2–4 MB) with CLIP-IQA and MUSIQ.

Takes a directory path, walks main and subdirectories for JPEGs, and saves detailed
evaluation results. Re-runs only process images not previously evaluated (incremental).

Usage:
  python image_evaluator.py /path/to/images
  python image_evaluator.py /path/to/images --output results.json
  python image_evaluator.py /path/to/images --musiq-tflite path/to/musiq.tflite
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime, timezone

import numpy as np

# Image discovery and loading
try:
    from PIL import Image
except ImportError:
    print("Install Pillow: pip install Pillow", file=sys.stderr)
    sys.exit(1)

# CLIP-IQA (PyTorch + PIQ)
try:
    import torch
    import piq
except ImportError as e:
    print("Install PyTorch and PIQ for CLIP-IQA: pip install torch piq", file=sys.stderr)
    sys.exit(1)

# MUSIQ: TensorFlow Hub or TensorFlow Lite
_MUSIQ_TF = None
_MUSIQ_TFLITE = None


def _load_musiq_tf():
    """Lazy-load MUSIQ via TensorFlow Hub."""
    global _MUSIQ_TF
    if _MUSIQ_TF is not None:
        return _MUSIQ_TF
    try:
        import tensorflow as tf
        import tensorflow_hub as hub
    except ImportError:
        raise ImportError("Install TensorFlow and TensorFlow Hub for MUSIQ: pip install tensorflow tensorflow_hub")
    # Official TF Hub model (AVA-trained, score 1–10)
    model = hub.load("https://tfhub.dev/google/musiq/ava/1")
    _MUSIQ_TF = model.signatures["serving_default"]
    return _MUSIQ_TF


def _load_musiq_tflite(tflite_path: str):
    """Load MUSIQ from a .tflite file. Returns (interpreter, input_details, output_details)."""
    global _MUSIQ_TFLITE
    key = str(tflite_path)
    if _MUSIQ_TFLITE is not None and _MUSIQ_TFLITE[0] == key:
        return _MUSIQ_TFLITE[1]
    try:
        import tensorflow.lite as tflite
    except ImportError:
        try:
            import tflite_runtime.interpreter as tflite
        except ImportError:
            raise ImportError(
                "Install TensorFlow (pip install tensorflow) or tflite_runtime for TFLite MUSIQ"
            )
    interp = tflite.Interpreter(model_path=tflite_path)
    interp.allocate_tensors()
    input_details = interp.get_input_details()
    output_details = interp.get_output_details()
    _MUSIQ_TFLITE = (key, (interp, input_details, output_details))
    return _MUSIQ_TFLITE[1]


# Result file name (stored in the evaluated directory)
DEFAULT_RESULTS_BASENAME = "image_evaluation_results.json"
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


def load_image_as_tensor(path: Path, device: torch.device) -> torch.Tensor:
    """Load JPEG as tensor (1, 3, H, W), range [0, 1], RGB."""
    img = Image.open(path).convert("RGB")
    arr = torch.from_numpy(np.array(img)).float() / 255.0
    # (H, W, C) -> (1, C, H, W)
    tensor = arr.permute(2, 0, 1).unsqueeze(0).to(device)
    return tensor


def evaluate_clip_iqa(image_path: Path, device: torch.device) -> dict:
    """Run CLIP-IQA on one image. Returns dict with score and optional error."""
    try:
        x = load_image_as_tensor(image_path, device)
        metric = piq.CLIPIQA(data_range=1.0).to(device)
        with torch.no_grad():
            score = metric(x)
        value = float(score.squeeze().cpu().numpy())
        return {"clip_iqa_score": round(value, 6), "clip_iqa_error": None}
    except Exception as e:
        return {"clip_iqa_score": None, "clip_iqa_error": str(e)}


def evaluate_musiq_tf(image_path: Path) -> dict:
    """Run MUSIQ via TensorFlow Hub on one image (raw bytes). Returns dict with score 1–10."""
    import tensorflow as tf
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        predict_fn = _load_musiq_tf()
        # Model expects image bytes (batch of scalars or single tensor)
        inp = tf.constant([image_bytes])
        out = predict_fn(inp)
        # Output may be dict with key like 'output_0' or 'predictions'
        if isinstance(out, dict):
            v = next(iter(out.values()))
        else:
            v = out
        score = float(tf.squeeze(v).numpy())
        return {"musiq_score": round(score, 4), "musiq_error": None}
    except Exception as e:
        return {"musiq_score": None, "musiq_error": str(e)}


def evaluate_musiq_tflite(image_path: Path, tflite_path: str) -> dict:
    """Run MUSIQ via TFLite. Expects input shape compatible with image bytes or decoded image."""
    try:
        interp, input_details, output_details = _load_musiq_tflite(tflite_path)
        with open(image_path, "rb") as f:
            image_bytes = f.read()
        # Typical Hub->TFLite: input is string (bytes). Shape often (1,) or () for one image.
        inp = input_details[0]
        if inp["dtype"] == np.uint8 or "string" in str(inp["dtype"]).lower():
            # Pass raw bytes; interpreter may expect numpy array of bytes/object
            data = np.array([image_bytes], dtype=object) if inp["shape"] != [] else np.array(image_bytes, dtype=object)
        else:
            # Decode image and resize to model input size if needed
            img = Image.open(image_path).convert("RGB")
            arr = np.array(img, dtype=np.float32)
            if len(inp["shape"]) == 4:
                # NCHW or NHWC
                if arr.shape[-1] != inp["shape"][-1] and len(inp["shape"]) == 4 and inp["shape"][-1] == 3:
                    pass  # NHWC
                else:
                    arr = np.expand_dims(arr, 0)
            data = arr
        interp.set_tensor(inp["index"], data)
        interp.invoke()
        score = float(interp.get_tensor(output_details[0]["index"]).squeeze())
        return {"musiq_score": round(score, 4), "musiq_error": None}
    except Exception as e:
        return {"musiq_score": None, "musiq_error": str(e)}


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


def load_existing_results(results_path: Path) -> dict[str, dict]:
    """Load existing results JSON: map relative_path -> record."""
    if not results_path.exists():
        return {}
    try:
        with open(results_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}
    # Support both {"results": [...]} and [...] formats
    if isinstance(data, dict) and "results" in data:
        list_results = data["results"]
    elif isinstance(data, list):
        list_results = data
    else:
        return {}
    return {r["relative_path"]: r for r in list_results if "relative_path" in r}


def save_results(results_path: Path, records: list[dict], root: Path) -> None:
    """Write results JSON with metadata."""
    payload = {
        "directory": str(root.resolve()),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_images": len(records),
        "results": records,
    }
    with open(results_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, ensure_ascii=False)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate images with CLIP-IQA and MUSIQ; save detailed results (incremental by path)."
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
        "--musiq-tflite",
        type=str,
        default=None,
        help="Path to MUSIQ TFLite model (.tflite). If not set, use TensorFlow Hub.",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
        choices=("cpu", "cuda", "mps"),
        help="Device for CLIP-IQA (PyTorch)",
    )
    args = parser.parse_args()

    root = args.directory.resolve()
    if not root.is_dir():
        print(f"Not a directory: {root}", file=sys.stderr)
        return 1

    results_path = (args.output or root / DEFAULT_RESULTS_BASENAME).resolve()
    existing = load_existing_results(results_path)
    device = torch.device(args.device)

    all_jpegs = find_jpeg_files(root)
    to_process = [p for p in all_jpegs if relative_path(p, root) not in existing]
    print(f"Found {len(all_jpegs)} JPEG(s); {len(to_process)} new to process.")

    # Start from existing results, then add/update
    results_by_path = dict(existing)

    for i, image_path in enumerate(to_process):
        rel = relative_path(image_path, root)
        print(f"[{i+1}/{len(to_process)}] {rel}")
        rec = collect_file_info(image_path, root)
        rec["evaluated_at"] = datetime.now(timezone.utc).isoformat()

        clip_out = evaluate_clip_iqa(image_path, device)
        rec.update(clip_out)

        if args.musiq_tflite:
            musiq_out = evaluate_musiq_tflite(image_path, args.musiq_tflite)
        else:
            musiq_out = evaluate_musiq_tf(image_path)
        rec.update(musiq_out)

        results_by_path[rel] = rec

    # Persist full list (order: existing keys order + new in scan order)
    order = [relative_path(p, root) for p in all_jpegs]
    ordered_records = [results_by_path[r] for r in order if r in results_by_path]
    save_results(results_path, ordered_records, root)
    print(f"Wrote {results_path} ({len(ordered_records)} images).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
