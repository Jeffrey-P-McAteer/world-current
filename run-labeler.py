# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "labelme",
#   "flask",
#   "imgviz", "natsort", "loguru", "PyQt5",
#   "setuptools",
# ]
# ///

import subprocess
import sys
import os
import shutil

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

    print(f'Found labelme at {shutil.which("labelme")}')
    subprocess.run([
        shutil.which('labelme'),
        '--output', label_out_folder,
    ], env=env, check=True, cwd=folder_of_images)

