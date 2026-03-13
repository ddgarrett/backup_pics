import tensorflow as tf
import tensorflow_hub as hub

# 1. Load the MUSIQ AVA model from TF Hub
model_url = "https://tfhub.dev/google/musiq/ava/1"
musiq_model = hub.KerasLayer(model_url)

# 2. Create a concrete function that handles raw tensors
# Note: MUSIQ expects specific multi-scale inputs. 
# For a standard TFLite conversion, we define a wrapper:
class MusiqWrapper(tf.Module):
    def __init__(self, model):
        super(MusiqWrapper, self).__init__()
        self.model = model

    @tf.function(input_signature=[tf.TensorSpec(shape=[1, None, None, 3], dtype=tf.float32)])
    def __call__(self, x):
        # The original model might expect normalized data or specific resizing
        # We pass the tensor directly to the hub layer
        return self.model(x)

wrapper = MusiqWrapper(musiq_model)

# 3. Convert to TFLite
converter = tf.lite.TFLiteConverter.from_concrete_functions(
    [wrapper.__call__.get_concrete_function()],
    wrapper
)

# Optimizations for ARM (Raspberry Pi 5)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
# If you want to use the Pi's 16GB RAM for speed, Float16 is a good balance
converter.target_spec.supported_types = [tf.float16]

tflite_model = converter.convert()

# 4. Save the model
with open('musiq_ava.tflite', 'wb') as f:
    f.write(tflite_model)