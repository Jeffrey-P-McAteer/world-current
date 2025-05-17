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

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f'Usage: uv run run-yolo-training.py ./path/to/yolo-training')
        sys.exit(1)

    yolo_directory = sys.argv[1]
    yolov8_model_file = os.path.join(yolo_directory, 'yolov8n.pt')
    yolov8_data_yaml_file = os.path.join(yolo_directory, 'data.yaml')

    with open(yolov8_data_yaml_file, 'w') as fd:
      fd.write(f'''
train: /absolute/path/to/yolo_dataset/images/train TODO
val: /absolute/path/to/yolo_dataset/images/val

nc: 1
names: ['power_pole']
''')

    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(sys.path)
    print(f'Found yolo at {shutil.which("yolo")}')
    subprocess.run([
      shutil.which("yolo"),
      'detect', 'train',
      f'model={yolov8_model_file}',
      f'data={yolov8_data_yaml_file}',
      'epochs=100',
      'imgsz=1694',
    ], check=True, env=env)

