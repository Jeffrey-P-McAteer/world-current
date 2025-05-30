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
#   "ultralytics",
#   "numpy"
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
import subprocess
import webbrowser
import shutil

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

import numpy
import ultralytics

sys.path.append(os.path.dirname(__file__))

import so_funcs
import analytic_tile_server
import location_chipper
import tower_follower

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

## when specified these cause the progam to output visuals for each step

# step1_map = '/tmp/step1-map.png'
# step2_facility_chips_folder = '/tmp'
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

  config_file = sys.argv[1]
  with open(config_file, 'r') as fd:
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

  m_zoom = so_funcs.calculate_zoom(*bbox, MAP_W_PX, MAP_H_PX) # we use this in several locations, so generate it once

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
        (so_funcs.get_lonx_from_dict(p), so_funcs.get_laty_from_dict(p) ),
        color_from_dict(p, default_value=color_of_energy_source(energy_source(p))),
        size_from_dict(p)
      )
      m.add_marker(marker)

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
      draw_x = m._x_to_px(staticmap.staticmap._lon_to_x(so_funcs.get_lonx_from_dict(p), m_zoom))
      draw_y = m._y_to_px(staticmap.staticmap._lat_to_y(so_funcs.get_laty_from_dict(p), m_zoom))
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

  font = so_funcs.get_default_ttf_font(16)

  power_plant_images = [None for p in region_power_plants]

  def render_one(i, p):
    image = location_chipper.get_area_chip_image(
      so_funcs.get_lonx_from_dict(p), so_funcs.get_laty_from_dict(p)
    )
    power_plant_images[i] = image

  threads = []
  for i, p in enumerate(region_power_plants):
    t = threading.Thread(target=render_one, args=(i, p))
    t.start()
    threads.append(t)
  for t in threads:
    t.join()

  step2_facility_chips_folder = config.get('step2_facility_chips_folder', None)
  if not step2_facility_chips_folder is None and os.path.exists(os.path.dirname(step2_facility_chips_folder)):
    os.makedirs(step2_facility_chips_folder, exist_ok=True)
    for i, image in enumerate(power_plant_images):
      out_png = os.path.join(step2_facility_chips_folder, f'{i}.png')
      labeled_image = image.copy()
      drawable = PIL.ImageDraw.Draw(labeled_image)
      so_funcs.draw_text_with_border(
        drawable, (2, 2),
        f'{json.dumps(region_power_plants[i], indent=2)}',
        font,
        '#ffffff',
      )
      labeled_image.save(out_png)
      print(f'Output {out_png}')
  else:
    print(f'Did not find a key step2_facility_chips_folder in config, skipping chips preview')
  print()

  print(f'We now have {len(power_plant_images):,} images matching to our {len(region_power_plants):,} facilities')

  path_to_tower_model_file = config.get('path_to_tower_model_file', None)
  if path_to_tower_model_file is not None and not os.path.exists(path_to_tower_model_file):
    path_to_tower_model_file = None
  if path_to_tower_model_file is None:
    training_images_folder = os.path.join(os.path.dirname(config_file), 'training-images')
    print(f'Either no path_to_tower_model_file key specified or the file does not exist; we are placing chips')
    print(f'at {training_images_folder} and templating out a training environment.')
    os.makedirs(training_images_folder, exist_ok=True)
    for i, image in enumerate(power_plant_images):
      out_png = os.path.join(training_images_folder, f'{i}.png')
      if os.path.exists(out_png):
        age_s = time.time() - os.path.getmtime(out_png)
        if age_s < 30 * 50:
          print(f'We already have output {out_png} {int(age_s)} seconds ago, skipping')
          continue
      image.save(out_png)
      print(f'Output {out_png}')

    cmd = ['uv', 'run', os.path.join(os.path.dirname(__file__), 'run-labeler.py'), training_images_folder]
    print(f'> {" ".join(cmd)}')
    subprocess.run(cmd, check=True)
    print(f'world-current.py is done asking for labeling + model-generation to occur.')
    path_to_tower_model_file = config.get('path_to_tower_model_file', None)
    if not path_to_tower_model_file is None and os.path.exists(path_to_tower_model_file):
      yn = input('Would you like to continue the analysis directly using {} as the ? (y/n)')
      if not 'y' in yn.lower():
        sys.exit(1)
    else:
      print(f'Please go set path_to_tower_model_file to the .pt file we just created in your {config_file}!')
      sys.exit(1)


  print(f'Loading {path_to_tower_model_file} and using it to find tower positions in imagery...')

  yolo_model = ultralytics.YOLO(path_to_tower_model_file)

  step3_tower_following_folder = config.get('step3_tower_following_folder', None)
  if not step3_tower_following_folder is None:
    font = so_funcs.get_default_ttf_font(18)
    report_html_path = os.path.join(step3_tower_following_folder, 'index.html')
    report_html = '<html><head><title>Following Results</title></head><body>'
    for i, p in enumerate( region_power_plants ):
      i_folder = os.path.join(step3_tower_following_folder, f'{i}')
      if os.path.exists(i_folder):
        shutil.rmtree(i_folder, ignore_errors=True)
      os.makedirs(i_folder, exist_ok=True)
      p = region_power_plants[i]
      p_lonx, p_laty = (so_funcs.get_lonx_from_dict(p), so_funcs.get_laty_from_dict(p))

      tower_follower.follow_towers(
        config, i, 0, i_folder, p_lonx, p_laty, list(), yolo_model, font,
        image.width, image.height, m_zoom
      )


      p_as_json = json.dumps(region_power_plants[i], indent=4, sort_keys=True)
      report_html += f'<details><summary><h2 style="margin-top:0;">Facility {i}<h2></summary><pre>{p_as_json}</pre></details>'
      report_html += '<div style="display:inline;overflow-x:scroll;max-width:98vw;">'
      for image_name in sorted(os.listdir(i_folder)):
        if image_name.casefold().endswith('.png') or image_name.casefold().endswith('.jpg'):
          report_html += f'<img src="{i}/{image_name}" width=512 height=512/>'
      report_html += '</div>'
      report_html += '<hr/>'

    report_html += '</body>'
    
    with open(report_html_path, 'w') as fd:
      fd.write(report_html)
    webbrowser.open(report_html_path)
    print(f'Output {report_html_path}')

  else:
    print(f'TODO use research w/ step3_tower_following_folder output to do the same but w/o intermediate outputs')
    sys.exit(1)


















