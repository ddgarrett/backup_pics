# Image Evaluator

Evaluates JPEG images (e.g. 4080×3071 px, 2–4 MB) using **CLIP-IQA** and **MUSIQ**, and writes detailed results to a JSON file. Re-runs only process images not already in the results file (incremental).

## Features

- **Input**: Directory path (scans main and all subdirectories for JPEGs).
- **Output**: One JSON file (by default `image_evaluation_results.json` in that directory) with:
  - `relative_path`: path to each image relative to the root directory
  - `file_size_bytes`, `file_size_mb`, `width`, `height`
  - `clip_iqa_score`: CLIP-IQA quality score in [0, 1]
  - `musiq_score`: MUSIQ aesthetic score in [1, 10]
  - `evaluated_at`: ISO 8601 timestamp
- **Incremental**: Only images not present in the existing results file are evaluated; results are merged and rewritten.

## Installation

### 1. Python and base dependencies

Use Python 3.9+ and a virtual environment (recommended):

```bash
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install --upgrade pip
```

Optional: install all evaluator dependencies at once:

```bash
pip install -r requirements_image_evaluator.txt
```

### 2. Image loading

```bash
pip install Pillow numpy
```

### 3. CLIP-IQA (PyTorch + PIQ)

CLIP-IQA runs on PyTorch and uses the PIQ library (no TensorFlow):

```bash
pip install torch piq
```

- **CPU**: the above is enough.
- **GPU (CUDA)**: install a CUDA build of PyTorch from [pytorch.org](https://pytorch.org/get-started/locally/), then `pip install piq`.
- **Apple Silicon (MPS)**: PyTorch 1.12+ supports MPS; use `--device mps` if available.

### 4. MUSIQ (TensorFlow or TensorFlow Lite)

**Option A — TensorFlow Hub (default)**

Uses the official MUSIQ model from TensorFlow Hub (no conversion):

```bash
pip install tensorflow tensorflow_hub
```

**Option B — TensorFlow Lite (optional, for smaller runtime / edge)**

Use TFLite only if you have converted the MUSIQ model to `.tflite` (see “Converting MUSIQ to TensorFlow Lite” below). The script can use the full TensorFlow Hub model without TFLite.

Install one of:

- Full TensorFlow (includes TFLite):

  ```bash
  pip install tensorflow
  ```

- Or the smaller TFLite runtime (inference only):

  ```bash
  pip install tflite-runtime
  ```

  See: [TensorFlow Lite Python quickstart](https://www.tensorflow.org/lite/guide/python).

Then run the evaluator with your converted model:

```bash
python image_evaluator.py /path/to/images --musiq-tflite /path/to/musiq.tflite
```

---

## Converting MUSIQ to TensorFlow Lite

MUSIQ is distributed as a TensorFlow Hub model. To use TensorFlow Lite instead of full TensorFlow at inference time, you first export the Hub model to a SavedModel, then convert it to TFLite.

### Step 1: Install TensorFlow and TensorFlow Hub

```bash
pip install tensorflow tensorflow_hub
```

### Step 2: Download the Hub model and save as SavedModel

Use the provided helper script (or run the equivalent code):

```bash
python save_musiq_saved_model.py
# Optional: custom output path
python save_musiq_saved_model.py --output ./my_musiq_saved_model
```

### Step 3: Convert SavedModel to TFLite

Use the provided converter script:

```bash
python convert_musiq_to_tflite.py
# Optional: custom paths
python convert_musiq_to_tflite.py --saved-model ./musiq_saved_model --output ./musiq.tflite
```

If conversion fails (e.g. unsupported ops), the script will error; in that case keep using the TensorFlow Hub model (Option A) without `--musiq-tflite`.

### Step 4: Use the TFLite model in the evaluator

```bash
python image_evaluator.py /path/to/images --musiq-tflite ./musiq.tflite
```

**Note**: The Hub MUSIQ model expects **raw image bytes** (JPEG/PNG). If your converted TFLite model has a different input signature (e.g. fixed-size float image), you may need to adapt the preprocessing in `evaluate_musiq_tflite()` in `image_evaluator.py` (e.g. decode image, resize, normalize) to match the converter’s input shape and type.

---

## Usage

```bash
# Evaluate all JPEGs under a directory (default output: <dir>/image_evaluation_results.json)
python image_evaluator.py /path/to/images

# Custom output file
python image_evaluator.py /path/to/images --output /path/to/my_results.json

# Use MUSIQ via TFLite
python image_evaluator.py /path/to/images --musiq-tflite ./musiq.tflite

# Use GPU for CLIP-IQA (or MPS on Apple Silicon)
python image_evaluator.py /path/to/images --device cuda
python image_evaluator.py /path/to/images --device mps
```

---

## Output JSON shape

Example structure:

```json
{
  "directory": "/absolute/path/to/images",
  "generated_at": "2025-03-08T12:00:00.000000+00:00",
  "total_images": 42,
  "results": [
    {
      "relative_path": "subdir/photo.jpg",
      "file_size_bytes": 3141592,
      "file_size_mb": 2.9962,
      "width": 4080,
      "height": 3071,
      "evaluated_at": "2025-03-08T12:00:01.000000+00:00",
      "clip_iqa_score": 0.723456,
      "clip_iqa_error": null,
      "musiq_score": 5.1234,
      "musiq_error": null
    }
  ]
}
```

If an evaluation step fails for an image, the corresponding `*_score` is `null` and `*_error` contains the error message.

---

## Training data and TFLite

- **CLIP-IQA**: Uses a pre-trained CLIP model and precomputed text tokens (downloaded by PIQ). No training or conversion to TFLite in this project.
- **MUSIQ**: Pre-trained on the AVA dataset; we only run inference. Training code lives in the [Google Research MUSIQ repo](https://github.com/google-research/google-research/tree/master/musiq). To convert a **custom trained** MUSIQ model to TFLite:
  1. Export your model to SavedModel format (as in the Google Research codebase).
  2. Run the same `TFLiteConverter.from_saved_model()` steps as above, and adjust `--musiq-tflite` to point to your `.tflite` file.
