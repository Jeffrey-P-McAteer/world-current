# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "toml",
#   "diskcache",
#   "platformdirs",
#   "staticmap",
#   "Pillow",
#   "shapely",
#   "requests",
# ]
# ///

import os
import sys
import csv
import time
import random

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
import analytic_tile_server

cache = diskcache.Cache(platformdirs.user_cache_dir('world-current'))
CACHE_EXPIRE_S = 60 * 60
MAP_W_PX = 1920
MAP_H_PX = 1080

def lcache(key, expensive_call, expire=CACHE_EXPIRE_S):
    if key in os.environ.get('IGNORE_CACHES', ''):
        value = expensive_call()
    else:
        value = cache.get(key, None)
    if value is None:
        value = expensive_call()
    cache.set(key, value, expire=expire)
    return value

def get_lat_from_dict(d):
  return float(d.get('latitude', d.get('lat', d.get('y', None))))

def get_lon_from_dict(d):
  return float(d.get('longitude', d.get('lon', d.get('x', None))))

def color_from_dict(d):
  if 'color' in d:
    return d['color']
  return 'grey'

def size_from_dict(d):
  if 'size' in d:
    return int(d['size'])
  return 12

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

  port = random.randint(8000, 8200)
  t = analytic_tile_server.spawn_run_thread(cache, port)
  time.sleep(0.1)

  m = staticmap.StaticMap(MAP_W_PX, MAP_H_PX, url_template=f'http://127.0.0.1:{port}/tile/{{z}}/{{y}}/{{x}}.png')
  for p in region_power_plants:
    marker = staticmap.CircleMarker((get_lon_from_dict(p), get_lat_from_dict(p) ), color_from_dict(p), size_from_dict(p) )
    m.add_marker(marker)

  image_m = m.render(
    zoom=so_funcs.calculate_zoom(*bbox, MAP_W_PX, MAP_H_PX),
    center=so_funcs.center_of_bbox(*bbox)
  )
  image_m.save('/tmp/m.png')

  analytic_tile_server.shutdown()










