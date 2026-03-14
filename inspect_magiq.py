import tensorflow_hub as hub

'''
result:

<class 'tensorflow.python.saved_model.load.Loader._recreate_base_user_object.<locals>._UserObject'>
False
['f', 'graph_debug_info', 'signatures', 'tensorflow_git_version', 'tensorflow_version']
Signatures: ['serving_default']

'''

model = hub.load("https://tfhub.dev/google/musiq/ava/1")

# What type is it?
print(type(model))

# Does it have .layers (Keras-style)?
print(hasattr(model, "layers"))

# What attributes does it have?
print([x for x in dir(model) if not x.startswith("_")])

# Signatures (what you're already using)
print("Signatures:", list(model.signatures.keys()))