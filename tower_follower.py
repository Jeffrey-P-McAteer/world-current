
# Designed to be imported by world-current.py
import os
import sys
import math

import numpy
import PIL

import so_funcs
import location_chipper

def have_processed(list_of_xy, lonx, laty):
    equality_epsilon = 0.000001
    for x,y in list_of_xy:
        if abs(x - lonx) < equality_epsilon and abs(y - laty):
            return True
    return False

# i == number from gen fac, j == number in recursive sequence, primarially used for debugging
def follow_towers(config, i, j, i_folder, lonx, laty, already_processed_xys, yolo_model, font, MAP_W_PX, MAP_H_PX, m_zoom):
    if have_processed(already_processed_xys, lonx, laty):
        return 0
    
    tower_following_out_png = os.path.join(i_folder, f'{j}.png')
    print(f'Writing tower-following results to {tower_following_out_png}')
    pil_image = location_chipper.get_1km_chip_image(
      lonx, laty
    )
    
    labeled_image = pil_image.copy()
    drawable = PIL.ImageDraw.Draw(labeled_image)
    
    numpy_image = numpy.array(pil_image)
    numpy_images = [numpy_image]
    image_result = next( list(yolo_model( numpy_images )) )
    for tower_j, box in enumerate(image_result.boxes):
        cls = int(box.cls[0])  # class index
        label = yolo_model.names[cls]  # class name
        xyxy = box.xyxy[0].tolist()  # bounding box coordinates
        conf = float(box.conf[0])  # confidence score

        box_pixels_center = so_funcs.center_of_bbox(*xyxy)
        box_gis_center = so_funcs.pixel_to_latlon(
          box_pixels_center[0], box_pixels_center[1],
          MAP_W_PX, MAP_H_PX, m_zoom, lonx, laty
        )

        so_funcs.draw_text_with_border(
            drawable, box_pixels_center,
            f'< {box_pixels_center} is a {label} ({round(conf, 2)})',
            font,
            '#ffffff',
        )

    labeled_image.save(tower_following_out_png)

    already_processed_xys.append( (lonx, laty) )

    # And recurse through each tower until we run out of towers!
    num_towers_processed = 1
    for tower_j, box in enumerate(image_result.boxes):
        cls = int(box.cls[0])  # class index
        label = yolo_model.names[cls]  # class name
        xyxy = box.xyxy[0].tolist()  # bounding box coordinates
        conf = float(box.conf[0])  # confidence score
        
        box_pixels_center = so_funcs.center_of_bbox(*xyxy)

        num_towers_processed += follow_towers(
            config, i, j+num_towers_processed+tower_j, i_folder, box_pixels_center[0], box_pixels_center[1], already_processed_xys,
            yolo_model, font, MAP_W_PX, MAP_H_PX, m_zoom
        )

    return num_towers_processed
