#!/usr/bin/env python3
"""
Image Evaluator (MUSIQ only) — evaluate images (e.g. 4080×3071 JPEGs) with MUSIQ.

Takes a directory path, walks main and subdirectories for JPEGs, and saves
CSV results. Supports evaluating at multiple resize max-sizes in a single run;
for each max-size value, separate CSV files are written (depending on backend)
whose names are suffixed with the backend and max-size
e.g. image_evaluation_musiq_results_tf_512.csv.

Usage examples:

  # Default, evaluate with TensorFlow MUSIQ at max-size 512 only
  python image_evaluator_musiq.py /path/to/images

  # Evaluate at multiple sizes (e.g. 256, 512, full-res)
  python image_evaluator_musiq.py /path/to/images --max-size 256 512 0

  # Use TFLite MUSIQ instead of full TensorFlow
  python image_evaluator_musiq.py /path/to/images --backend tflite --tflite-model /path/to/musiq.tflite

  # Run both backends (TF + TFLite) for side-by-side timing comparison
  python image_evaluator_musiq.py /path/to/images --backend both --tflite-model /path/to/musiq.tflite

  # Custom output prefix
  python image_evaluator_musiq.py /path/to/images --output-prefix my_musiq_results

TFLite model notes:
- The official MUSIQ model is published as a TensorFlow SavedModel on TF Hub
  (AVA variant, 1–10 aesthetic scores).
- To use TFLite, first download/clone the SavedModel (from TF Hub or Kaggle
  tfhub-redirect for musiq/ava) and run a small conversion script like:

  ```python
  import tensorflow as tf

  saved_model_dir = "/path/to/downloaded/musiq_ava_saved_model"
  converter = tf.lite.TFLiteConverter.from_saved_model(saved_model_dir)
  # Optional: enable optimizations (may change numeric behavior slightly)
  converter.optimizations = [tf.lite.Optimize.DEFAULT]
  tflite_model = converter.convert()
  with open("musiq_ava.tflite", "wb") as f:
      f.write(tflite_model)
  ```

  Then point --tflite-model at the resulting musiq_ava.tflite file.
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
_MUSIQ_TFLITE = None


def _load_musiq_tf():
    """Lazy-load MUSIQ via TensorFlow Hub."""
    global _MUSIQ_TF
    if _MUSIQ_TF is not None:
        return _MUSIQ_TF
    # Official TF Hub model (AVA-trained, score 1–10)
    model = hub.load("https://tfhub.dev/google/musiq/ava/1")
    _MUSIQ_TF = model.signatures["serving_default"]
    return _MUSIQ_TF


def _load_musiq_tflite(tflite_path: Path):
    """
    Load MUSIQ TFLite model. Returns (interpreter, input_details, output_details).
    Assumes a single input (JPEG bytes as string/uint8) and single scalar output.
    """
    global _MUSIQ_TFLITE
    key = str(tflite_path.resolve())
    if _MUSIQ_TFLITE is not None and _MUSIQ_TFLITE[0] == key:
        return _MUSIQ_TFLITE[1]

    try:
        # Try full TF Lite first
        import tensorflow.lite as tflite  # type: ignore[import]
    except ImportError:
        try:
            import tflite_runtime.interpreter as tflite  # type: ignore[import]
        except ImportError:
            print(
                "Install TensorFlow (pip install tensorflow) or tflite_runtime "
                "for TFLite MUSIQ support.",
                file=sys.stderr,
            )
            raise

    interp = tflite.Interpreter(model_path=str(tflite_path))
    interp.allocate_tensors()
    input_details = interp.get_input_details()
    output_details = interp.get_output_details()
    _MUSIQ_TFLITE = (key, (interp, input_details, output_details))
    return _MUSIQ_TFLITE[1]


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


def evaluate_musiq_tflite(
    image_path: Path,
    tflite_path: Path,
    max_size: Optional[int] = None,
) -> dict:
    """Run MUSIQ via TFLite on one image (raw bytes)."""
    try:
        interp, input_details, output_details = _load_musiq_tflite(tflite_path)
        image_bytes = _image_to_jpeg_bytes(image_path, max_size=max_size)

        inp = input_details[0]
        # Most exported MUSIQ TFLite models accept a string/bytes input.
        if "string" in str(inp["dtype"]).lower():
            data = np.array([image_bytes], dtype=object)
        else:
            # Fallback: pass bytes as uint8 array
            data = np.frombuffer(image_bytes, dtype=np.uint8)[None, :]

        interp.set_tensor(inp["index"], data)
        interp.invoke()
        score = float(interp.get_tensor(output_details[0]["index"]).squeeze())
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
    backend: str,
    tflite_model: Optional[Path],
) -> None:
    """
    Evaluate MUSIQ for each image at each requested max-size, writing one CSV per size
    and backend. max_size == 0 means full resolution (no resize).

    backend:
      - "tf":     use TensorFlow Hub MUSIQ
      - "tflite": use TFLite MUSIQ (requires --tflite-model)
      - "both":   run both and write two CSVs per size (tf + tflite)
    """
    images = list(images)
    if not images:
        print("No JPEG images found; nothing to do.")
        return

    if backend in {"tflite", "both"} and tflite_model is None:
        raise ValueError("TFLite backend requested but --tflite-model was not provided.")

    for max_size in max_sizes:
        size_label = "full" if max_size == 0 else str(max_size)

        def run_for_backend(tag: str) -> None:
            csv_name = f"{output_prefix}_{tag}_{size_label}.csv"
            csv_path = root / csv_name
            print(f"\nEvaluating MUSIQ ({tag}) at max-size={max_size} ({size_label})")
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
                        "backend",
                        "musiq_score",
                        "musiq_error",
                    ]
                )

                for i, img_path in enumerate(images, start=1):
                    info = collect_file_info(img_path, root)
                    print(f"[{i}/{len(images)}] ({tag}) {info.relative_path}")

                    t0 = time.perf_counter()
                    if tag == "tf":
                        musiq_out = evaluate_musiq_tf(
                            img_path,
                            max_size=max_size if max_size > 0 else None,
                        )
                    else:
                        musiq_out = evaluate_musiq_tflite(
                            img_path,
                            tflite_model if tflite_model is not None else Path(""),
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
                            tag,
                            musiq_out["musiq_score"] if musiq_out["musiq_score"] is not None else "",
                            musiq_out["musiq_error"] or "",
                        ]
                    )

            avg_time = total_time / count if count > 0 else 0.0
            print(
                f"Done for backend={tag}, max-size={max_size}. "
                f"{count} images, avg eval time: {avg_time:.4f}s. Results: {csv_path}"
            )

        if backend in {"tf", "both"}:
            run_for_backend("tf")
        if backend in {"tflite", "both"}:
            run_for_backend("tflite")


def parse_args(argv: Optional[List[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate images with MUSIQ only (TensorFlow, TFLite, or both); "
            "save CSV results for one or more resize max-size values "
            "(separate CSV per size and backend)."
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
            "Prefix for output CSV files. For each max-size value and backend, "
            "a CSV named <prefix>_<backend>_<size>.csv will be created in the "
            "directory being evaluated."
        ),
    )
    parser.add_argument(
        "--backend",
        type=str,
        choices=("tf", "tflite", "both"),
        default="tf",
        help=(
            "Which MUSIQ backend to use: 'tf' (TensorFlow Hub), "
            "'tflite' (TFLite), or 'both' for side-by-side comparison. "
            "Default: tf."
        ),
    )
    parser.add_argument(
        "--tflite-model",
        type=Path,
        default=None,
        help=(
            "Path to MUSIQ TFLite model (.tflite). Required when backend is "
            "'tflite' or 'both'."
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
        args.backend,
        args.tflite_model,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

