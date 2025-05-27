
# Designed to be imported by world-current, does not run stand-alone!

import csv
import math
import os
import sys

import PIL
import PIL.ImageFont
import PIL.ImageColor
import shapely
import shapely.geometry
import shapely.wkt


def get_laty_from_dict(d):
  return float(d.get('latitude', d.get('lat', d.get('y', None))))

def get_lonx_from_dict(d):
  return float(d.get('longitude', d.get('lon', d.get('x', None))))


def pt_dist(p1, p2):
    return math.sqrt(
        ((p1[0] - p2[0])**2.0) + ((p1[1] - p2[1])**2.0)
    )

def pixel_size(zoom, tile_size=256):
    n = 2 ** zoom
    lon_size = 360.0 / n / tile_size
    lat_size = (math.atan(math.sinh(math.pi * (1 - 2 * (tile_size - 1) / n))) - 
                math.atan(math.sinh(math.pi * (1 - 2 * tile_size / n)))) / tile_size
    lat_size = math.degrees(lat_size)
    return lon_size, lat_size

def pixel_to_lonx_laty(x, y, image_width, image_height, zoom, center_laty, center_lonx):
    px2lon, px2lat = pixel_size(zoom)

    return center_lonx + (px2lon * (x - (image_width/2.0))), center_laty + (-1.0 * px2lat * (y - (image_height/2.0)))

def latlon_to_pixel(laty, lonx, image_width, image_height, zoom, center_laty, center_lonx):
    px2lon, px2lat = pixel_size(zoom)
    delta_laty = center_laty - laty
    delta_lonx = center_lonx - lonx
    delta_pixels_y = delta_laty / px2lat
    delta_pixels_x = delta_lonx / px2lon
    return int(delta_pixels_x + (image_width / 2)), int(delta_pixels_y + (image_height / 2))

def brightness(color):
    # Convert color name or hex to RGB tuple
    rgb = PIL.ImageColor.getrgb(color)
    r, g, b = rgb

    # Calculate brightness using luminance formula (0-255 scale)
    # Formula from WCAG: Y = 0.2126*R + 0.7152*G + 0.0722*B
    return 0.2126 * r + 0.7152 * g + 0.0722 * b

def brightness_difference(color1, color2):
    b1 = brightness(color1)
    b2 = brightness(color2)

    diff = abs(b1 - b2)

    # Normalize to range 0..1 (max difference is between 0 and 255)
    return diff / 255.0

def draw_text_with_border(draw, position, text, font, text_color):
    x, y = position
    border_color = '#ffffff'
    border_width = 1

    if brightness_difference(text_color, border_color) > 0.50: # if we are FAR from white (ie big diff), add white border
        border_color = '#ffffff'
    else:
        border_color = '#000000'

    # Draw border by drawing the text shifted in 8 directions around the center
    for dx in range(-border_width, border_width + 1):
        for dy in range(-border_width, border_width + 1):
            if dx == 0 and dy == 0:
                continue  # Skip the center (main text)
            draw.text((x + dx, y + dy), text, font=font, fill=border_color)

    # Draw the main text
    draw.text(position, text, font=font, fill=text_color)


def get_default_ttf_font(size=16):
    font_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
        "/usr/lib/python3.13/site-packages/matplotlib/mpl-data/fonts/ttf/DejaVuSans.ttf",  # Also Linux
        "/usr/share/fonts/noto/NotoSans-Regular.ttf",
        "/Library/Fonts/Arial.ttf",                         # macOS
        "C:/Windows/Fonts/arial.ttf"                        # Windows
    ]
    for path in font_paths:
        if os.path.exists(path):
            return PIL.ImageFont.truetype(path, size)
    print("Warning: No TTF font found. Using default bitmap font.")
    return PIL.ImageFont.load_default()


def cvs2dicts(csv_path):
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        data = [row for row in reader]
    return data

def load_geometries(input_data):
    polygons = []

    if isinstance(input_data, list) and len(input_data) == 4:
        # Handle bounding box list
        minx, miny, maxx, maxy = input_data
        polygons.append(shapely.geometry.box(minx, miny, maxx, maxy))

    elif isinstance(input_data, str):
        if input_data.strip().lower().endswith('.geojson') and os.path.isfile(input_data):
            # Handle .geojson file
            with open(input_data, 'r') as f:
                geojson = json.load(f)

            features = geojson.get('features', [])
            for feature in features:
                geom = shapely.geometry.shape(feature['geometry'])
                if isinstance(geom, shapely.geometry.Polygon):
                    polygons.append(geom)
                else:
                    # Convert multi-geometry to individual polygons if needed
                    polygons.extend(geom.geoms if hasattr(geom, 'geoms') else [geom])
        else:
            try:
                # Assume it's a WKT string
                geom = shapely.wkt.load_wkt(input_data)
                if isinstance(geom, shapely.geometry.Polygon):
                    polygons.append(geom)
                else:
                    polygons.extend(geom.geoms if hasattr(geom, 'geoms') else [geom])
            except Exception as e:
                raise ValueError(f"Invalid WKT or file path: {e}")
    else:
        raise TypeError("Input must be a [minx, miny, maxx, maxy] list, WKT string, or .geojson file path.")

    # Compute overall bounding box
    if polygons:
        combined = shapely.geometry.box(*polygons[0].bounds)
        for poly in polygons[1:]:
            combined = combined.union(shapely.geometry.box(*poly.bounds))
        bounding_box = combined.bounds
    else:
        bounding_box = None

    return polygons, bounding_box

def calculate_zoom(min_lon, min_lat, max_lon, max_lat, width_px, height_px):
    """Estimate zoom level that fits the bounding box in the given pixel dimensions."""
    WORLD_DIM = {'height': 256, 'width': 256}
    ZOOM_MAX = 19

    def lat_rad(lat):
        sin = math.sin(lat * math.pi / 180)
        rad_x2 = math.log((1 + sin) / (1 - sin)) / 2
        return max(min(rad_x2, math.pi), -math.pi) / 2

    def zoom(map_px, world_px, fraction):
        return math.floor(math.log(map_px / world_px / fraction) / math.log(2))

    lat_fraction = (lat_rad(max_lat) - lat_rad(min_lat)) / math.pi
    lon_diff = max_lon - min_lon
    lon_fraction = ((lon_diff + 360) if lon_diff < 0 else lon_diff) / 360

    lat_zoom = zoom(height_px, WORLD_DIM['height'], lat_fraction)
    lon_zoom = zoom(width_px, WORLD_DIM['width'], lon_fraction)

    return min(lat_zoom, lon_zoom, ZOOM_MAX)

def center_of_bbox(minx, miny, maxx, maxy):
    return float(minx + maxx) / 2.0, float(miny + maxy) / 2.0



