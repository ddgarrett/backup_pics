import tensorflow as tf
import tensorflow_hub as hub

model = hub.load("https://tfhub.dev/google/musiq/ava/1")

# Create a dummy input tensor based on the model's requirements
dummy_input = tf.zeros((1, 224, 224, 3)) 

# Try calling the model object directly with return_endpoints=True
try:
    outputs = model(dummy_input, training=False, return_endpoints=True)
    print(outputs.keys()) # Look for 'transformer_output', 'pooled_output', or 'enc_out'
except TypeError:
    print("This model does not support return_endpoints via __call__.")