import math
from io import BytesIO

import requests
from PIL import Image

import diskcache
import platformdirs

chip_cache = diskcache.Cache(platformdirs.user_cache_dir('world-current'))
CACHE_EXPIRE_S = 24 * 60 * 60

TILE_SIZE = 256
ZOOM = 18  # Updated zoom level

# Example XYZ tile server URL (OpenStreetMap)
#TILE_URL = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
TILE_URL = "https://services.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}"

def latlon_to_tile(lat, lon, zoom):
    lat_rad = math.radians(lat)
    n = 2.0 ** zoom
    xtile = int((lon + 180.0) / 360.0 * n)
    ytile = int((1.0 - math.log(math.tan(lat_rad) + 1 / math.cos(lat_rad)) / math.pi) / 2.0 * n)
    return xtile, ytile

def download_tile(x, y, zoom):
    url = TILE_URL.format(z=zoom, x=x, y=y)
    #print(f'Downloading Image {url}')
    content = chip_cache.get(url, None)
    if content is None:
      response = requests.get(url)
      response.raise_for_status()
      content = response.content
      chip_cache.set(url, content)
    return Image.open(BytesIO(content))

def stitch_tiles(center_x, center_y, zoom, tile_count=11):
    half = tile_count // 2
    tiles = []
    for y in range(center_y - half, center_y + half + 1):
        row = []
        for x in range(center_x - half, center_x + half + 1):
            tile_img = download_tile(x, y, zoom)
            row.append(tile_img)
        tiles.append(row)

    stitched_width = TILE_SIZE * tile_count
    stitched_height = TILE_SIZE * tile_count
    final_img = Image.new('RGB', (stitched_width, stitched_height))

    for row_idx, row in enumerate(tiles):
        for col_idx, tile in enumerate(row):
            final_img.paste(tile, (col_idx * TILE_SIZE, row_idx * TILE_SIZE))

    return final_img

def crop_to_1000m_area(image, lat, zoom, crop_size_m=1000):
    # Calculate meters per pixel at zoom and latitude
    meters_per_pixel = 156543.03392 * math.cos(math.radians(lat)) / (2 ** zoom)
    pixels_1000m = int(crop_size_m / meters_per_pixel)

    center_pixel = image.size[0] // 2
    half = pixels_1000m // 2
    return image.crop((center_pixel - half, center_pixel - half, center_pixel + half, center_pixel + half))


def get_area_chip_image(lonx, laty):
  tile_x, tile_y = latlon_to_tile(laty, lonx, ZOOM)
  stitched_img = stitch_tiles(tile_x, tile_y, ZOOM, tile_count=11)
  #return crop_to_1000m_area(stitched_img, laty, ZOOM)
  return stitched_img



