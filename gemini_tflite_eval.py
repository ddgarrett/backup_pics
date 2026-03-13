import os
import time
import argparse
import tensorflow as tf
import numpy as np

def evaluate_directory(model_path, image_dir):
    print(f"Loading TFLite model from '{model_path}'...")
    
    # Initialize the interpreter using 4 threads for the Pi 5's CPU cores
    interpreter = tf.lite.Interpreter(model_path=model_path, num_threads=4)
    interpreter.allocate_tensors()
    
    input_details = interpreter.get_input_details()
    output_details = interpreter.get_output_details()
    
    # Supported image extensions (MUSIQ natively decodes JPEG, PNG, GIF, BMP)
    valid_extensions = ('.jpg', '.jpeg', '.png', '.bmp', '.gif')
    
    print(f"Scanning directory: '{image_dir}'")
    print("-" * 60)
    
    # Get all valid files and sort them alphabetically
    files = [f for f in os.listdir(image_dir) if f.lower().endswith(valid_extensions)]
    files.sort()
    
    if not files:
        print("No valid image files found in the directory.")
        return

    # Process each image
    for filename in files:
        file_path = os.path.join(image_dir, filename)
        
        # 1. Read the image as raw bytes
        with open(file_path, "rb") as f:
            image_bytes = f.read()
            
        # 2. Prepare the tensor payload
        input_data = np.array([image_bytes], dtype=object)
        
        # 3. Start the timer, run inference, and stop the timer
        start_time = time.time()
        
        interpreter.set_tensor(input_details[0]['index'], input_data)
        interpreter.invoke()
        
        # The score is usually a 1D array, so we grab the first element
        score = interpreter.get_tensor(output_details[0]['index'])[0] 
        
        end_time = time.time()
        
        # Calculate duration
        eval_time = end_time - start_time
        
        # 4. Print the formatted result
        print(f"File: {filename:<20} | Score: {score:5.2f} | Time: {eval_time:5.3f} seconds")

    print("-" * 60)
    print("Evaluation complete.")

if __name__ == "__main__":
    # Set up command line argument parsing
    parser = argparse.ArgumentParser(description="Evaluate a directory of images using the MUSIQ TFLite model.")
    parser.add_argument("image_dir", type=str, help="Path to the directory containing images to evaluate.")
    parser.add_argument("--model", type=str, default="musiq_ava.tflite", help="Path to the .tflite model file (default: musiq_ava.tflite).")
    
    args = parser.parse_args()
    
    # Verify the directory exists before running
    if not os.path.isdir(args.image_dir):
        print(f"Error: The directory '{args.image_dir}' does not exist.")
    else:
        evaluate_directory(args.model, args.image_dir)