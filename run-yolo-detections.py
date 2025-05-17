# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "setuptools",
#   "ultralytics",
#   "numpy",
#   "Pillow"
# ]
# ///

import subprocess
import sys
import os
import shutil
import json

import PIL
from ultralytics import YOLO
import numpy

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print(f'Usage: uv run run-yolo-detections.py ./path/to/yolov8n.pt ./path/to/image.png [./path/to/another-image.png ...]')
        sys.exit(1)

    yolo_pt_file = os.path.abspath(sys.argv[1])
    image_files = [os.path.abspath(arg) for arg in sys.argv[2:]]
    print(f'yolo_pt_file = {yolo_pt_file}')
    print(f'image_files = {image_files}')

    model = YOLO(yolo_pt_file)
    pil_images = [PIL.Image.open(file) for file in image_files]

    # Convert PIL images to NumPy format for YOLO
    numpy_array_images = [numpy.array(img) for img in pil_images]

    # Do the analysis!
    results = model(numpy_array_images)

    for i, result in enumerate(results):
        print(f'Results for image {i} at {image_files[i]}:')
        for box in result.boxes:
            cls = int(box.cls[0])  # class index
            label = model.names[cls]  # class name
            xyxy = box.xyxy[0].tolist()  # bounding box coordinates
            conf = float(box.conf[0])  # confidence score

            print(f'  Label: {label}')
            print(f'  Bounding box (xyxy): {xyxy}')
            print(f'  Confidence: {conf}')
