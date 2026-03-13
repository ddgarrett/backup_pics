#!/usr/bin/env python3
"""
Convert the MUSIQ AVA TensorFlow SavedModel to TFLite.

Intended for use on Raspberry Pi 5 (16GB RAM is sufficient for conversion).
Reduces console noise during conversion and writes the resulting .tflite file.
Run from the backup_pics project directory.

Usage (on the Pi):
  python convert_musiq_to_tflite.py ./musiq_saved_model --output musiq_ava.tflite

To obtain the SavedModel on the Pi (use tf.saved_model.save, not model.save):
  import tensorflow as tf
  import tensorflow_hub as hub
  model = hub.load("https://tfhub.dev/google/musiq/ava/1")
  tf.saved_model.save(model, "./musiq_saved_model")
"""

from __future__ import annotations

# Must be set before TensorFlow is imported (reduces C++ / oneDNN log spam)
import os
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
os.environ["TF_LOGGING_VERBOSITY"] = "ERROR"

import argparse
import contextlib
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

    print(f"Converting {saved_model_dir} ...")
    converter = tf.lite.TFLiteConverter.from_saved_model(str(saved_model_dir))
    if not args.no_optimize:
        converter.optimizations = [tf.lite.Optimize.DEFAULT]

    @contextlib.contextmanager
    def suppress_stderr():
        """Redirect stderr to devnull during conversion to silence TF C++/oneDNN output."""
        try:
            stderr_fd = sys.stderr.fileno()
            with open(os.devnull, "w") as devnull:
                save_fd = os.dup(stderr_fd)
                try:
                    os.dup2(devnull.fileno(), stderr_fd)
                    yield
                finally:
                    os.dup2(save_fd, stderr_fd)
                    os.close(save_fd)
        except (OSError, AttributeError):
            # Windows or non-fd stderr: run without suppressing
            yield

    try:
        with suppress_stderr():
            tflite_bytes = converter.convert()
    except Exception as e:
        print(f"Conversion failed: {e}", file=sys.stderr)
        return 1

    if not tflite_bytes:
        print("Conversion returned no bytes.", file=sys.stderr)
        return 1

    out_path.write_bytes(tflite_bytes)
    print(f"Wrote {len(tflite_bytes)} bytes to {out_path.absolute()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
