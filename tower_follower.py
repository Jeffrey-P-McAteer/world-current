
# Designed to be imported by world-current.py
import os
import sys
import math
import traceback

import numpy
import PIL

import so_funcs
import location_chipper

def have_processed(list_of_xy, lonx, laty):
    equality_epsilon = 0.000001
    for x,y in list_of_xy:
        if abs(x - lonx) < equality_epsilon and abs(y - laty) < equality_epsilon:
            return True
    return False

def next_nonexisting(directory, file_name_creator):
    n = 0
    while os.path.exists( os.path.join(directory, file_name_creator(n)) ):
        n += 1
    return os.path.join(directory, file_name_creator(n))

# i == number from gen fac, j == number in recursive sequence, primarially used for debugging
def follow_towers(config, i, j, i_folder, lonx, laty, already_processed_xys, yolo_model, font, MAP_W_PX, MAP_H_PX, m_zoom):
    if have_processed(already_processed_xys, lonx, laty) or j > 50 or len(already_processed_xys) > 50:
        return 0
    
    #tower_following_out_png = os.path.join(i_folder, f'{j}.png')
    tower_following_out_png = next_nonexisting(i_folder, lambda n:  f'{n}.png')
    print(f'Writing tower-following results to {tower_following_out_png}')
    print(f'Calling get_1km_chip_image({lonx}, {laty})')
    try:
        pil_image = location_chipper.get_1km_chip_image(
            lonx, laty
        )
    except:
        traceback.print_exc()
        return 0
    
    labeled_image = pil_image.copy()
    drawable = PIL.ImageDraw.Draw(labeled_image)

    so_funcs.draw_text_with_border(
        drawable, (4.0, 4.0),
        f'Image x,y center = {lonx}, {laty}\n',
        font,
        '#ffffff',
    )
    
    numpy_image = numpy.array(pil_image)
    numpy_images = [numpy_image]
    image_results = list(yolo_model( numpy_images ))
    if len(image_results) < 1:
        print(f'At {i}/{j} model found no boxes!')
        return 0
    
    image_result = image_results[0]
    for tower_j, box in enumerate(image_result.boxes):
        cls = int(box.cls[0])  # class index
        label = yolo_model.names[cls]  # class name
        xyxy = box.xyxy[0].tolist()  # bounding box coordinates
        conf = float(box.conf[0])  # confidence score

        box_pixels_center = so_funcs.center_of_bbox(*xyxy)

        box_gis_center = so_funcs.pixel_to_lonx_laty(
          box_pixels_center[0], box_pixels_center[1],
          MAP_W_PX, MAP_H_PX, m_zoom, laty, lonx
        )
        so_funcs.draw_text_with_border(
            drawable, box_pixels_center,
            f'< {box_pixels_center} is a {label} ({round(conf, 2)}) at GIS location lonx,laty= {box_gis_center}',
            font,
            '#ffffff',
        )

    labeled_image.save(tower_following_out_png)
    print(f'Output {tower_following_out_png}')

    already_processed_xys.append( (lonx, laty) )
    num_towers_processed = len(image_result.boxes)

    # And recurse through each tower until we run out of towers!
    for tower_j, box in enumerate(image_result.boxes):
        cls = int(box.cls[0])  # class index
        label = yolo_model.names[cls]  # class name
        xyxy = box.xyxy[0].tolist()  # bounding box coordinates
        conf = float(box.conf[0])  # confidence score
        
        box_pixels_center = so_funcs.center_of_bbox(*xyxy)
        box_gis_center = so_funcs.pixel_to_lonx_laty(
          box_pixels_center[0], box_pixels_center[1],
          MAP_W_PX, MAP_H_PX, m_zoom, laty, lonx
        )

        num_towers_processed += follow_towers(
            config, i, j+num_towers_processed+1, i_folder, box_gis_center[0], box_gis_center[1], already_processed_xys,
            yolo_model, font, MAP_W_PX, MAP_H_PX, m_zoom
        )

    return num_towers_processed
