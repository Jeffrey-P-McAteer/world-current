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
#   "numpy"
# ]
# ///

import math
import os

# import location_chipper

# def pixel_size(zoom, tile_size=256):
#     n = 2 ** zoom
#     lon_size = 360.0 / n / tile_size
#     lat_size = (math.atan(math.sinh(math.pi * (1 - 2 * (tile_size - 1) / n))) - 
#                 math.atan(math.sinh(math.pi * (1 - 2 * tile_size / n)))) / tile_size
#     lat_size = math.degrees(lat_size)
#     return lon_size, lat_size

# #PX_SCALE_FACTOR = 0.0008

# def pixel_to_lonx_laty(x, y, image_width, image_height, zoom, center_laty, center_lonx):
#     px2lon, px2lat = pixel_size(zoom)
#     #px2lon *= PX_SCALE_FACTOR # PX_SCALE_FACTOR is arbitrary scaling to get images closer
#     #px2lat *= PX_SCALE_FACTOR
#     return center_lonx + (px2lon * (x - (image_width/2.0))), center_laty + (-1.0 * px2lat * (y - (image_height/2.0)))

# def latlon_to_pixel(laty, lonx, image_width, image_height, zoom, center_laty, center_lonx):
#     px2lon, px2lat = pixel_size(zoom)
#     delta_laty = center_laty - laty
#     delta_lonx = center_lonx - lonx
#     delta_pixels_y = (delta_laty / px2lat) # * PX_SCALE_FACTOR # PX_SCALE_FACTOR is arbitrary scaling to get images closer
#     delta_pixels_x = (delta_lonx / px2lon) # * PX_SCALE_FACTOR
#     return int(delta_pixels_x + (image_width / 2)), int(delta_pixels_y + (image_height / 2))

def add_pixels_to_coordinates(lat, lon, pixels_north, pixels_east):
    """
    Add pixels to lat, lon coordinates and return the new lat, lon coordinates.

    Parameters:
    lat (float): The latitude in decimal degrees.
    lon (float): The longitude in decimal degrees.
    pixels_north (int): The number of pixels to add in the north direction.
    pixels_east (int): The number of pixels to add in the east direction.

    Returns:
    tuple: A tuple containing the new latitude and longitude in decimal degrees.
    """
    # Define the pixel size in meters
    pixel_size_meters = 0.378320231692

    # Convert the pixel size from meters to degrees
    pixel_size_degrees_lat = pixel_size_meters / 111320.0  # approximately 1 degree of latitude is equal to 111,320 meters
    pixel_size_degrees_lon = pixel_size_meters / (111320.0 * math.cos(math.radians(lat)))  # adjust for latitude

    # Calculate the new latitude and longitude
    new_lat = lat + (pixels_north * pixel_size_degrees_lat)
    new_lon = lon + (pixels_east * pixel_size_degrees_lon)

    return new_lat, new_lon

TILE_SIZE = 256
ZOOM = 18  # Updated zoom level

image_w = TILE_SIZE * 11 # 2816
image_h = TILE_SIZE * 11 # 2816

# This is a marker of known size; we will use this to measure how wide pixels are in meters & assume this remains constant across the globe.
# pil_image = location_chipper.get_area_chip_image(
#     -110.307589, 31.5964
# )
# pil_image.save(r'C:\Temp\marker.png')
# os.system(r'C:\Temp\marker.png')

measured_bar_lengths_px = (401.2 + 398.7 + 408.6) / 3.0
pixel_width_meters = 152.4 / measured_bar_lengths_px
print(f'At zoom {ZOOM} level each pixel is {round(pixel_width_meters, 12)} meters wide')
print(f'This means we can expect our 256x256 pixel move to be {round(pixel_width_meters * math.sqrt((TILE_SIZE**2) + (TILE_SIZE**2)), 1)} meters or {round(pixel_width_meters * TILE_SIZE,1)} meters in either dimension.')

for asserts_on in [False, True]:
    print(f'asserts_on = {asserts_on}')
    for laty in [-60.0, -45.0, -15.0, 0.0, 15.0, 45.0, 60.0]:
        for lonx in [-180.0, -90.0, -45.0, 0.0, 45.0, 90.0, 180.0]:
            # x, y = latlon_to_pixel(laty, lonx, image_w, image_h, ZOOM, laty, lonx)
            # assert x == image_w // 2
            # assert y == image_h // 2
            x = image_w // 2
            y = image_h // 2

            x += TILE_SIZE
            y += TILE_SIZE

            moved_meters = pixel_width_meters * math.sqrt((TILE_SIZE**2) + (TILE_SIZE**2))
            moved_x_meters = pixel_width_meters * TILE_SIZE
            moved_y_meters = pixel_width_meters * TILE_SIZE

            moved_laty, moved_lonx = add_pixels_to_coordinates(laty, lonx, -(y - (image_h // 2)), x - (image_w // 2))
            moved_x_diff = moved_lonx - lonx # we expect moved_lonx to be larger than lonx, so this should be positive
            moved_y_diff = moved_laty - laty # We expect moved_laty to be smaller (pixel++ meand we go south), so this should be negative
            approx_moved_lonx_meters = moved_x_diff * (111320.0 * math.cos(math.radians(laty)))  # adjust for latitude
            approx_moved_laty_meters = moved_y_diff * 111320.0
            
            print(f'{laty:.1f}, {lonx:.1f} test moved {TILE_SIZE},{TILE_SIZE} pixels south-east which translated to {moved_x_diff:.16f} degrees x ({approx_moved_lonx_meters:.1f}m) {moved_y_diff:.16f} degrees y ({approx_moved_laty_meters:.1f}m)')

            if asserts_on:
                assert moved_x_diff > 0.0
                assert moved_y_diff < 0.0

                assert abs(abs(approx_moved_lonx_meters) - abs(moved_x_meters)) < 4.0
                assert abs(abs(approx_moved_laty_meters) - abs(moved_y_meters)) < 4.0



print('Done')

