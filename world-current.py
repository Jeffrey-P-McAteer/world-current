# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "toml",
#
# ]
# ///

import os
import sys


import toml

def print_help():
  print(f'''
Usage: uv run world-current.py ./path/to/config.toml

config.toml contains configuration like the following:

```
model_name = "Your Model's Name"

# At least one region_* definition must be given; if a file or layer of data is specified, ALL contents
# of the file/layer will be used to select regions of the world for processing.

# The bounding box is specified as MinX, MinY, MaxX, MaxY in WGS84 coordinates
region_bbox = [-82.9657830472, 7.2205414901, -77.2425664944, 9.61161001224]

# If this is used all polygons in the file will be used to select region
region_geojson = "./path/to/layer.geojson"

# region_wkt may also contain inline POLYGON() wkt instead of a file-path to a text file.
# In this case whitespace will be removed from the string before parsing.
region_wkt = "./path/to/wkt.txt"

```

'''.strip())

def die(msg='', code=1):
  print(msg)
  print()
  print_help()
  sys.exit(code)

if __name__ == '__main__':
  if len(sys.argv) < 2:
    die('No config.toml passed as an argument! Write a configuration file and try again.')

  if not os.path.exists(sys.argv[1]):
    die(f'The file {sys.argv[1]} does not exist! Please select a configuration file which exists and try again.')

  with open(sys.argv[1], 'r') as fd:
    config = toml.loads(fd.read())

  print(f'config = {config}')









