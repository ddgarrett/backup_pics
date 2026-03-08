#!/usr/bin/env python3
"""
Save the MUSIQ TensorFlow Hub model to a SavedModel directory for TFLite conversion.
Run once: pip install tensorflow tensorflow_hub && python save_musiq_saved_model.py
"""
import argparse
import tensorflow as tf
import tensorflow_hub as hub

MODEL_URL = "https://tfhub.dev/google/musiq/ava/1"


def main():
    p = argparse.ArgumentParser(description="Save MUSIQ Hub model to SavedModel")
    p.add_argument("--output", "-o", default="./musiq_saved_model", help="Output SavedModel directory")
    args = p.parse_args()
    print("Loading MUSIQ from TensorFlow Hub...")
    model = hub.load(MODEL_URL)
    tf.saved_model.save(model, args.output)
    print("Saved to", args.output)


if __name__ == "__main__":
    main()
