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
from PIL import Image, ImageDraw, ImageFont
from ultralytics import YOLO
import numpy

def get_default_ttf_font(size=16):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "/usr/lib/python3.13/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf",  # Also Linux
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",
        "/Library/Fonts/Arial.ttf",                         # macOS
        "C:/Windows/Fonts/arial.ttf"                        # Windows
    ]
    for path in font_paths:
        if os.path.exists(path):
            return PIL.ImageFont.truetype(path, size)
    print("Warning: No TTF font found. Using default bitmap font.")
    return PIL.ImageFont.load_default()

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

    font = get_default_ttf_font(24)

    for i, result in enumerate(results):
        print(f'Results for image {i} at {image_files[i]}:')

        annotated_img = pil_images[i].copy()
        draw = ImageDraw.Draw(annotated_img)

        for box in result.boxes:
            cls = int(box.cls[0])  # class index
            label = model.names[cls]  # class name
            xyxy = box.xyxy[0].tolist()  # bounding box coordinates
            conf = float(box.conf[0])  # confidence score

            print(f'  Label: {label}')
            print(f'  Bounding box (xyxy): {xyxy}')
            print(f'  Confidence: {conf}')


            xyxy = box.xyxy[0].tolist()
            x1, y1, x2, y2 = map(int, xyxy)
            label = model.names[int(box.cls[0])]
            conf = float(box.conf[0])
            label_text = f"{label} {conf:.2f}"

            # Draw box
            draw.rectangle([x1, y1, x2, y2], outline="red", width=2)
            draw.text((x1, y1 - 10), label_text, fill="red", font=font)

        output_path = f"/tmp/{i}.png"
        annotated_img.save(output_path)
        print(f'Saved an annotated image to {output_path}')

