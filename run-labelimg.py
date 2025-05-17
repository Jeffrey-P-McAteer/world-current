# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "labelImg",
#   "setuptools",
# ]
# ///

import subprocess
import sys
import os
import shutil

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f'Usage: uv run run-labelimg.py ./path/to/images')
        sys.exit(1)
    env = dict(os.environ)
    env['PYTHONPATH'] = os.pathsep.join(sys.path)
    #subprocess.run([sys.executable, "-m", "labelImg", sys.argv[1]], env=env, check=True)
    print(f'Found labelImg at {shutil.which("labelImg")}')
    subprocess.run([shutil.which('labelImg'), sys.argv[1]], env=env, check=True)
