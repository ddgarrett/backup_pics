import tensorflow as tf
import numpy as np

# 1. Load model with full TF to support SELECT_TF_OPS
interpreter = tf.lite.Interpreter(model_path="musiq_ava.tflite")
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

# 2. Read the image as raw bytes 
with open("test.jpg", "rb") as f:
    image_bytes = f.read()

# 3. Pass the string into TFLite
# TFLite Python API expects strings to be wrapped in a numpy object array
input_data = np.array([image_bytes], dtype=object)

interpreter.set_tensor(input_details[0]['index'], input_data)
interpreter.invoke()

# 4. Get Score
score = interpreter.get_tensor(output_details[0]['index'])
print(f"Aesthetic Score: {score}")