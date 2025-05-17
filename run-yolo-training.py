# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "setuptools",
#   "ultralytics",
# ]
# ///

import subprocess
import sys
import os
import shutil
import json

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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f'Usage: uv run run-yolo-training.py ./path/to/yolo-training')
        sys.exit(1)

    yolo_directory = os.path.abspath(sys.argv[1])
    label_out_folder = None
    for dirent in os.listdir(os.path.dirname(yolo_directory)):
      if dirent.lower().endswith('label-output'):
        label_out_folder = os.path.join(os.path.dirname(yolo_directory), dirent)
        break

    yolov8_model_file = os.path.join(yolo_directory, 'yolov8n.pt')
    yolov8_data_yaml_file = os.path.join(yolo_directory, 'data.yaml')

    print(f'label_out_folder = {label_out_folder}')
    all_classes  = read_all_labelme_classes(label_out_folder)
    print(f'all_classes = {all_classes}')

    with open(yolov8_data_yaml_file, 'w') as fd:
      fd.write(f'''
train: {os.path.join("images", "train")}
val: {os.path.join("images", "val")}

nc: {len(all_classes)}
names: {json.dumps(all_classes)}
''')
    print(f'Wrote {yolov8_data_yaml_file}')

    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(sys.path)
    print(f'Found yolo at {shutil.which("yolo")}')
    subprocess.run([
      shutil.which("yolo"),
      'detect', 'train',
      f'model={yolov8_model_file}',
      f'data={yolov8_data_yaml_file}',
      'epochs=1000',
      'imgsz=1694',
      'patience=500',
    ], check=True, env=env)

    print(f'Done!')
    print(f'See output model file {yolov8_model_file}')

