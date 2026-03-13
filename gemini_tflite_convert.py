import tensorflow as tf
import tensorflow_hub as hub

print("Loading model...")
# 1. Load the raw SavedModel (bypassing KerasLayer)
model = hub.load("https://tfhub.dev/google/musiq/ava/1")

# 2. Get the specific prediction signature
predict_fn = model.signatures['serving_default']

print("Converting to TFLite...")
# 3. Convert using the concrete function
converter = tf.lite.TFLiteConverter.from_concrete_functions([predict_fn])

# CRITICAL: We must allow Select TF Ops because the model uses internal JPEG decoding
converter.target_spec.supported_ops = [
    tf.lite.OpsSet.TFLITE_BUILTINS, 
    tf.lite.OpsSet.SELECT_TF_OPS  
]
# Optional: Quantize weights for better ARM performance
converter.optimizations = [tf.lite.Optimize.DEFAULT]

tflite_model = converter.convert()

# 4. Save
with open('musiq_ava.tflite', 'wb') as f:
    f.write(tflite_model)
    
print("Success! Saved as musiq_ava.tflite")