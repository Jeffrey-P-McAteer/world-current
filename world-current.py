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
import json
import math
import threading

import toml
import diskcache
import platformdirs
import staticmap
import PIL
import PIL.ImageFont
import PIL.Image
import shapely
import shapely.geometry
import shapely.wkt

sys.path.append(os.path.dirname(__file__))

import so_funcs
import analytic_tile_server
import location_chipper

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

def get_laty_from_dict(d):
  return float(d.get('latitude', d.get('lat', d.get('y', None))))

def get_lonx_from_dict(d):
  return float(d.get('longitude', d.get('lon', d.get('x', None))))

def color_from_dict(d, default_value='grey'):
  if 'color' in d:
    return d['color']
  return default_value

def size_from_dict(d):
  if 'size' in d:
    return int(d['size'])
  return 12

def energy_source(d):
  if 'primary_fuel' in d and len(d.get('primary_fuel', '')) > 0:
    return d.get('primary_fuel', '').lower()

  for k,v in d.items():
    if 'hydro'.casefold() in v.casefold():
      return 'hydro'


  raise Exception(f'Unknown energy source from {json.dumps(d, indent=2)}')

def color_of_energy_source(s):
  if s == 'hydro':
    return '#add8e6'
  elif s == 'oil':
    return '#b5651d'
  elif s == 'coal':
    return '#654321'
  elif s == 'solar':
    return '#ffea00'
  else:
    return 'grey'


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

  # Step 1: Read region into a list of polygons.
  polygons, bbox = so_funcs.load_geometries(config['region'])
  b_minx, b_miny, b_maxx, b_maxy = bbox
  print(f'polygons = {polygons}')
  print(f'bbox = {bbox}')
  print()

  # Step 2: Read path_to_global_power_plant_database and filter to list of generating facilities within region.
  path_to_global_power_plant_database = config['path_to_global_power_plant_database']
  global_power_plants_list = so_funcs.cvs2dicts(path_to_global_power_plant_database)
  region_power_plants = [
    p for p in global_power_plants_list if 'latitude' in p and 'longitude' in p and b_minx <= float(p['longitude']) <= b_maxx and b_miny <= float(p['latitude']) <= b_maxy
  ]
  print(f'Given {len(global_power_plants_list):,} power plants recorded globally, {len(region_power_plants):,} fall within selected region')
  #print(f'region_power_plants = {json.dumps(region_power_plants, indent=2)}')


  step1_map_png_path = config.get('step1_map', None)
  print()
  if step1_map_png_path is not None and len(step1_map_png_path) > 0 and os.path.exists(os.path.dirname(step1_map_png_path)):
    print(f'Outputting step1 map to {step1_map_png_path}')

    port = random.randint(8000, 8200)
    t = analytic_tile_server.spawn_run_thread(cache, port)
    time.sleep(0.1)

    m = staticmap.StaticMap(MAP_W_PX, MAP_H_PX, url_template=f'http://127.0.0.1:{port}/tile/{{z}}/{{y}}/{{x}}.png')
    for p in region_power_plants:
      marker = staticmap.CircleMarker(
        (get_lonx_from_dict(p), get_laty_from_dict(p) ),
        color_from_dict(p, default_value=color_of_energy_source(energy_source(p))),
        size_from_dict(p)
      )
      m.add_marker(marker)

    m_zoom = so_funcs.calculate_zoom(*bbox, MAP_W_PX, MAP_H_PX);
    image_m = m.render(
      zoom=m_zoom,
      center=so_funcs.center_of_bbox(*bbox)
    )
    # We must _manually_ draw labels ugh
    font = so_funcs.get_default_ttf_font(18)
    drawable_m = PIL.ImageDraw.Draw(image_m)
    taken_xy_coords = list()
    for p in region_power_plants:
      e_source = energy_source(p)
      draw_x = m._x_to_px(staticmap.staticmap._lon_to_x(get_lonx_from_dict(p), m_zoom))
      draw_y = m._y_to_px(staticmap.staticmap._lat_to_y(get_laty_from_dict(p), m_zoom))
      # Offset text slightly to avoid overlapping with the marker
      x_offset = 5
      y_offset = -10
      xy_coord = (draw_x + x_offset, draw_y + y_offset)
      while any(math.sqrt(((xy_coord[0] - other_x)**2.0) + ((xy_coord[1] - other_y)**2.0)) < 26.0 for other_x, other_y in taken_xy_coords):
        y_offset += 5
        xy_coord = (draw_x + x_offset, draw_y + y_offset)
        print(f'Notice: Moved {e_source} label to offset {xy_coord} to avoid label collision')
      taken_xy_coords.append(xy_coord)
      so_funcs.draw_text_with_border(
        drawable_m, xy_coord, e_source, font,
        color_from_dict(p, default_value=color_of_energy_source(energy_source(p)))
      )
      #print(f'{e_source} is being drawn at {draw_x},{draw_y}')

    image_m.save(step1_map_png_path)

    analytic_tile_server.shutdown()

  else:
    print(f'Did not find a key step1_map in config, skipping map preview')
  print()

  font = so_funcs.get_default_ttf_font(18)

  power_plant_images = [None for p in region_power_plants]

  def render_one(i, p):
    image = location_chipper.get_1km_chip_image(
      get_lonx_from_dict(p), get_laty_from_dict(p)
    )
    drawable = PIL.ImageDraw.Draw(image)
    so_funcs.draw_text_with_border(
      drawable, (2, 2),
      f'{json.dumps(p, indent=2)}',
      font,
      '#ffffff',
    )
    power_plant_images[i] = image

  threads = []
  for i, p in enumerate(region_power_plants):
    t = threading.Thread(target=render_one, args=(i, p))
    t.start()
    threads.append(t)
  for t in threads:
    t.join()
  for i, image in enumerate(power_plant_images):
    out_png = f'/tmp/{i}.png'
    image.save(out_png)
    print(f'Output {out_png}')
  print(f'Done chipping!')


















