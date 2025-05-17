# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "labelme",
#   "flask",
#   "imgviz", "natsort", "loguru", "PyQt5",
#   "setuptools",
#   "Pillow",
# ]
# ///

import subprocess
import sys
import os
import shutil
import json

from PIL import Image

def read_all_labelme_classes(labelme_dir):
    all_classes = set()
    for fname in os.listdir(labelme_dir):
        if not fname.endswith('.json'):
            continue
        data = json.load(open(os.path.join(labelme_dir, fname)))
        for shape in data['shapes']:
            label = shape['label']
            all_classes.add(label)
    return list(all_classes)

def convert_labelme_to_yolo(labelme_dir, output_dir, class_list):
    os.makedirs(output_dir, exist_ok=True)
    for fname in os.listdir(labelme_dir):
        if not fname.endswith('.json'):
            continue
        data = json.load(open(os.path.join(labelme_dir, fname)))
        image_path = os.path.join(labelme_dir, data['imagePath'])
        image = Image.open(image_path)
        w, h = image.size

        yolo_lines = []
        for shape in data['shapes']:
            label = shape['label']
            if label not in class_list:
                continue
            cls_id = class_list.index(label)
            points = shape['points']
            x1, y1 = points[0]
            x2, y2 = points[1]
            cx = (x1 + x2) / 2 / w
            cy = (y1 + y2) / 2 / h
            bw = abs(x2 - x1) / w
            bh = abs(y2 - y1) / h
            yolo_lines.append(f"{cls_id} {cx} {cy} {bw} {bh}")

        #label_path = os.path.join(output_dir, os.path.splitext(data['imagePath'])[0] + '.txt')
        label_path = os.path.join(output_dir, os.path.basename(os.path.splitext(data['imagePath'])[0]) + '.txt')
        with open(label_path, 'w') as f:
            f.write('\n'.join(yolo_lines))
        # We also copy the image from image_path to
        yolo_image_path = os.path.join(output_dir, os.path.basename(data['imagePath']))
        shutil.copy(image_path, yolo_image_path)
        print(f'Output {image_path} to {label_path} and {yolo_image_path}')


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f'Usage: uv run run-labeler.py ./path/to/images')
        sys.exit(1)

    folder_of_images = sys.argv[1]
    label_sw_git_url = 'https://github.com/wkentaro/labelme'
    label_out_folder = os.path.join(os.path.dirname(folder_of_images), os.path.basename(folder_of_images)+'-label-output')

    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(sys.path)

    os.makedirs(label_out_folder, exist_ok=True)

    print(f'Found labelme at {shutil.which("labelme")}, running with label_out_folder={label_out_folder}')
    subprocess.run([
        shutil.which('labelme'),
        '--output', label_out_folder,
    ], env=env, check=True, cwd=folder_of_images)

    # After labeling is done, we output
    all_classes = read_all_labelme_classes(label_out_folder)
    yolov8_train_folder = os.path.join(os.path.dirname(folder_of_images), os.path.basename(folder_of_images)+'-yolo-training')
    print(f'have {len(all_classes)} labeled classes, converting to YOLOv8 format and placing training data in {yolov8_train_folder}')
    os.makedirs(yolov8_train_folder, exist_ok=True)
    convert_labelme_to_yolo(label_out_folder, yolov8_train_folder, all_classes)


