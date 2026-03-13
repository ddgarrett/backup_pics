#!/usr/bin/env python3
"""
Convert the MUSIQ AVA TensorFlow SavedModel to TFLite.

Reduces console noise during conversion and writes the resulting .tflite file.
Run once on a machine with full TensorFlow, then copy the .tflite file to the Pi.

Usage:
  python convert_musiq_to_tflite.py /path/to/musiq_ava_saved_model
  python convert_musiq_to_tflite.py /path/to/saved_model --output musiq_ava.tflite

To obtain the SavedModel:
  1. Download from TF Hub / Kaggle (google/musiq/ava/1), or
  2. Save it from Python:
       import tensorflow_hub as hub
       model = hub.load("https://tfhub.dev/google/musiq/ava/1")
       model.save("/path/to/musiq_ava_saved_model")
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Convert MUSIQ SavedModel to TFLite.")
    parser.add_argument(
        "saved_model_dir",
        type=Path,
        help="Directory containing the MUSIQ AVA SavedModel (saved_model.pb, variables/).",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=None,
        help="Output .tflite path (default: <saved_model_dir>/../musiq_ava.tflite).",
    )
    parser.add_argument(
        "--no-optimize",
        action="store_true",
        help="Disable TFLite optimizations (larger file, closer to TF numerics).",
    )
    args = parser.parse_args()

    saved_model_dir = args.saved_model_dir.resolve()
    if not saved_model_dir.is_dir():
        print(f"Not a directory: {saved_model_dir}", file=sys.stderr)
        return 1

    # Quiet TensorFlow during conversion
    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    import tensorflow as tf  # noqa: E402

    tf.get_logger().setLevel("ERROR")
    if hasattr(tf, "autograph"):
        tf.autograph.set_verbosity(0)

    out_path = args.output
    if out_path is None:
        out_path = saved_model_dir.parent / "musiq_ava.tflite"
    out_path = out_path.resolve()
    if out_path.suffix.lower() != ".tflite":
        out_path = out_path.with_suffix(".tflite")

    print(f"Converting {saved_model_dir} to TFLite ...")
    converter = tf.lite.TFLiteConverter.from_saved_model(str(saved_model_dir))
    if not args.no_optimize:
        converter.optimizations = [tf.lite.Optimize.DEFAULT]

    tflite_bytes = converter.convert()
    if not tflite_bytes:
        print("Conversion returned no bytes.", file=sys.stderr)
        return 1

    out_path.write_bytes(tflite_bytes)
    print(f"Wrote {len(tflite_bytes)} bytes to {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
