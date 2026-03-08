#!/usr/bin/env python3
"""
Convert MUSIQ SavedModel to TensorFlow Lite.
Run after save_musiq_saved_model.py:
  python convert_musiq_to_tflite.py --saved-model ./musiq_saved_model --output musiq.tflite
"""
import argparse
import tensorflow as tf


def main():
    p = argparse.ArgumentParser(description="Convert MUSIQ SavedModel to TFLite")
    p.add_argument("--saved-model", "-s", default="./musiq_saved_model", help="SavedModel directory")
    p.add_argument("--output", "-o", default="./musiq.tflite", help="Output .tflite path")
    args = p.parse_args()

    converter = tf.lite.TFLiteConverter.from_saved_model(args.saved_model)
    converter.target_spec.supported_ops = [
        tf.lite.OpsSet.TFLITE_BUILTINS,
        tf.lite.OpsSet.SELECT_TF_OPS,
    ]
    tflite_model = converter.convert()
    with open(args.output, "wb") as f:
        f.write(tflite_model)
    print("Wrote", args.output)


if __name__ == "__main__":
    main()
