
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

def pt_dist(p1, p2):
    return math.sqrt(
        ((p1[0] - p2[0])**2.0) + ((p1[1] - p2[1])**2.0)
    )

def pixel_to_latlon(x, y, image_width, image_height, zoom, center_lat, center_lon):
    TILE_SIZE = 256

    # Convert center lat/lon to pixel coordinates at this zoom level
    def latlon_to_pixels(lat, lon, zoom):
        scale = TILE_SIZE * 2**zoom
        x_pixel = (lon + 180.0) / 360.0 * scale
        sin_lat = math.sin(math.radians(lat))
        y_pixel = (
            0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)
        ) * scale
        return x_pixel, y_pixel

    # Convert pixel coordinates to lat/lon at this zoom level
    def pixels_to_latlon(px, py, zoom):
        scale = TILE_SIZE * 2**zoom
        lon = px / scale * 360.0 - 180.0
        n = math.pi - 2.0 * math.pi * py / scale
        lat = math.degrees(math.atan(math.sinh(n)))
        return lat, lon

    # Center pixel position in global coordinates
    center_px, center_py = latlon_to_pixels(center_lat, center_lon, zoom)

    # Offset from image center to this pixel
    dx = x - image_width / 2
    dy = y - image_height / 2

    # Global pixel coordinates of the input pixel
    target_px = center_px + dx
    target_py = center_py + dy

    # Convert back to lat/lon
    return pixels_to_latlon(target_px, target_py, zoom)

def latlon_to_pixel(lat, lon, image_width, image_height, zoom, center_lat, center_lon):
    TILE_SIZE = 256

    # Convert lat/lon to global pixel coordinates at a given zoom level
    def latlon_to_global_px(lat, lon, zoom):
        scale = TILE_SIZE * 2**zoom
        x = (lon + 180.0) / 360.0 * scale
        sin_lat = math.sin(math.radians(lat))
        y = (0.5 - math.log((1 + sin_lat) / (1 - sin_lat)) / (4 * math.pi)) * scale
        return x, y

    # Get global pixel coordinates of center and target lat/lon
    center_px, center_py = latlon_to_global_px(center_lat, center_lon, zoom)
    target_px, target_py = latlon_to_global_px(lat, lon, zoom)

    # Calculate pixel position relative to image center
    dx = target_px - center_px
    dy = target_py - center_py

    pixel_x = image_width / 2 + dx
    pixel_y = image_height / 2 + dy

    return pixel_x, pixel_y

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



