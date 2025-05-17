
# Designed to be imported by world-current, does not run stand-alone!

import csv
import math


import shapely
import shapely.geometry
import shapely.wkt

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



