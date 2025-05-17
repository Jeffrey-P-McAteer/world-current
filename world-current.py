# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "toml",
#   "diskcache",
#   "platformdirs",
#   "staticmap",
#   "Pillow",
#   "shapely",
# ]
# ///

import os
import sys
import csv

import toml
import diskcache
import platformdirs
import staticmap
import PIL
import shapely
import shapely.geometry
import shapely.wkt

sys.path.append(os.path.dirname(__file__))

import so_funcs

cache = diskcache.Cache(platformdirs.user_cache_dir('world-current'))
CACHE_EXPIRE_S = 60 * 60

def lcache(key, expensive_call, expire=CACHE_EXPIRE_S):
    if key in os.environ.get('IGNORE_CACHES', ''):
        value = expensive_call()
    else:
        value = cache.get(key, None)
    if value is None:
        value = expensive_call()
    cache.set(key, value, expire=expire)
    return value

def create_map(bbox, points, out_file):
    #m = StaticMap(1920, 1080, url_template='http://a.tile.openstreetmap.org/{z}/{x}/{y}.png')
    #m = StaticMap(1920, 1080, url_template='https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}')
    m = StaticMap(1920, 1080, url_template='https://services.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}')
    for p in points:
      marker = CircleMarker((point["lon"], point["lat"]), point["color"], int(point.get('size', 12)) )
      m.add_marker(marker)

    return m

def print_help():
  print(f'''
Usage: uv run world-current.py ./path/to/config.toml

config.toml contains configuration like the following:

```
model_name = "Your Model's Name"

# At exactly one of the region definitions below must be given; if a file or layer of data is specified, ALL contents
# of the file/layer will be used to select regions of the world for processing.

# The bounding box is specified as MinX, MinY, MaxX, MaxY in WGS84 coordinates
region = [-82.9657830472, 7.2205414901, -77.2425664944, 9.61161001224]

# If this is used all polygons in the file will be used to select region; formats supported are
# everything that geopandas supports.
region = "./path/to/layer.geojson"

# region may also contain inline POLYGON() wkt instead of a file-path to a text file.
# In this case whitespace will be removed from the string before parsing.
region = """
POLYGON(-82.9657830472 7.2205414901, -77.2425664944 9.61161001224, -77.1425664944 9.41161001224, -77.0325664944 9.11161001224, -82.9657830472 7.2205414901)
"""

# Download a .zip from https://datasets.wri.org/datasets/global-power-plant-database and set this to point to the .csv
path_to_global_power_plant_database = "./path/to/global_power_plant_database.csv"

# Specify an output file + details


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

  print('=' * 18, ' CONFIG ', '=' * 18)
  print(f'{toml.dumps(config)}')
  print()

  # Step 1: Read region into a list of polygons.
  polygons, bbox = so_funcs.load_geometries(config['region'])
  b_minx, b_miny, b_maxx, b_maxy = bbox
  print(f'polygons = {polygons}')
  print(f'bbox = {bbox}')

  # Step 2: Read path_to_global_power_plant_database and filter to list of generating facilities within region.
  path_to_global_power_plant_database = config['path_to_global_power_plant_database']
  global_power_plants_list = so_funcs.cvs2dicts(path_to_global_power_plant_database)
  region_power_plants = [
    p for p in global_power_plants_list if 'latitude' in p and 'longitude' in p and b_minx <= float(p['longitude']) <= b_maxx and b_miny <= float(p['latitude']) <= b_maxy
  ]
  print(f'Given {len(global_power_plants_list):,} power plants recorded globally, {len(region_power_plants):,} fall within selected region')

  #print(f'region_power_plants = {region_power_plants}')












