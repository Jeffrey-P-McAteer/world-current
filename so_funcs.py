
# Designed to be imported by world-current, does not run stand-alone!

import csv

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
