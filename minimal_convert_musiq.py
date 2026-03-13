#!/usr/bin/env python3
"""
Minimal one-shot converter: MUSIQ AVA SavedModel -> musiq_ava.tflite

Run this on the Raspberry Pi 5 from the backup_pics project directory, where
./musiq_saved_model is the SavedModel directory created via:

  import tensorflow as tf
  import tensorflow_hub as hub
  model = hub.load("https://tfhub.dev/google/musiq/ava/1")
  tf.saved_model.save(model, "./musiq_saved_model")

Then convert with:

  python3 minimal_convert_musiq.py

This script is intentionally simple and prints a single clear success or
error line instead of flooding the terminal.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

# Reduce TensorFlow C++ log spam before importing TF
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

import tensorflow as tf  # noqa: E402

SAVED_DIR = Path("./musiq_saved_model").resolve()
OUT_PATH = Path("./musiq_ava.tflite").resolve()


def main() -> int:
    if not SAVED_DIR.is_dir():
        print(f"SavedModel directory not found: {SAVED_DIR}", file=sys.stderr)
        return 1

    print(f"Converting SavedModel at {SAVED_DIR} to {OUT_PATH} ...")

    try:
        converter = tf.lite.TFLiteConverter.from_saved_model(str(SAVED_DIR))
        # You can comment this line out if optimizations cause issues:
        converter.optimizations = [tf.lite.Optimize.DEFAULT]
        tflite_bytes = converter.convert()
    except Exception as e:
        print(f"ERROR during convert(): {e!r}", file=sys.stderr)
        return 1

    if not tflite_bytes:
        print("ERROR: convert() returned empty bytes", file=sys.stderr)
        return 1

    OUT_PATH.write_bytes(tflite_bytes)
    print(f"OK: wrote {len(tflite_bytes)} bytes to {OUT_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

