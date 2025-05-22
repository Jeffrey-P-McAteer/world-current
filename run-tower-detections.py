# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy",
#   "Pillow",
#   "opencv-python",
#   "diskcache",
#   "platformdirs"
# ]
# ///

import os
import sys
import tempfile
import math

import cv2
import numpy as np
import diskcache
import platformdirs

cache = diskcache.Cache(platformdirs.user_cache_dir('tower-detections'))
cache_expire_s = 24 * 60 * 60

image_to_analyze = sys.argv[1]
analysis_output_image = os.path.join(tempfile.gettempdir(),  'out'+os.path.splitext(image_to_analyze)[1])
print(f'image_to_analyze = {image_to_analyze}')
print(f'analysis_output_image = {analysis_output_image}')

min_length = 5
max_length = 75

image = cv2.imread(image_to_analyze)

gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Apply threshold to segment out the pixels
_, thresh = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# Find contours
contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

def just_numbers(some_array):
    try:
        return str(int(some_array * 10))
    except:
        pass
    return ','.join(just_numbers(item) for item in some_array)


lines_output_image = image.copy()
contours_output_image = image.copy()

potential_hits = [] # List of x1, y1, x2, y2

cv2.drawContours(contours_output_image, contours, -1, (0, 255, 0), 1)
for contour in contours:
    # Approximate the contour with a polygon
    epsilon = 0.03 * cv2.arcLength(contour, True)
    approx = cv2.approxPolyDP(contour, epsilon, True)
    if 2 <= len(approx) <= 5:
        # Calculate the coordinates of the "line" - here we just use the bbox minx/miny maxx/maxy
        x1 = None
        y1 = None
        x2 = None
        y2 = None
        for i in range(0, len(approx)):
            if x1 is None:
                x1 = approx[i][0][0]
            if y1 is None:
                y1 = approx[i][0][1]
            if x2 is None:
                x2 = approx[i][0][0]
            if y2 is None:
                y2 = approx[i][0][1]
            
            x1 = min(x1, approx[i][0][0])
            y1 = min(y1, approx[i][0][1])
            x2 = max(x2, approx[i][0][0])
            y2 = max(y2, approx[i][0][1])

        # if x1, y1 is not near _any_ of the points we flip the y1, y2 values (transpose to align w/ original coordinates)
        closest_dist = 999999.0
        for i in range(0, len(approx)):
            this_pt_dist = math.sqrt(
                ((approx[i][0][0] - x1)**2.0) + ((approx[i][0][1] - y1)**2.0)
            )
            closest_dist = min(this_pt_dist, closest_dist)
        if closest_dist > 3.0:
            old_y1 = y1
            y1 = y2
            y2 = old_y1

        length = cv2.arcLength(contour, True)
        x1_y1_length = math.sqrt(((x1-x2)**2.0 + ((y1-y2)**2.0)))
        if length > min_length and x1_y1_length < 200.0:
            cv2.drawContours(contours_output_image, [approx], -1, (0, 255, 255), 1)
            cv2.putText(contours_output_image, f"{round(length, 1)} l={len(approx)}", (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 1)
            cv2.line(contours_output_image, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Red lines

            potential_hits.append(
                (x1, y1, x2, y2)
            )

# we now filter by a criteria which gets rid of large results; we draw a circle around the line, and if anything outside of +- 20% of the line length is intersected we omit
# the line being rotated.
line_similarity_threshold = 0.20
hits_with_only_similars_nearby = []
for idx, line in enumerate(potential_hits):
    x1, y1, x2, y2 = line
    line_length = math.sqrt(((x1-x2)**2.0 + ((y1-y2)**2.0)))

    intersecting_lines = []
    for maybe_iline in potential_hits:
        m_x1, m_y1, m_x2, m_y2 = maybe_iline
        if (line[0] < maybe_iline[2] and maybe_iline[0] < line[2] and
            line[1] < maybe_iline[3] and maybe_iline[1] < line[3]):
            intersecting_lines.append(maybe_iline)
    shortest_iline_length = None
    longest_iline_length = None
    for iline in intersecting_lines:
        m_x1, m_y1, m_x2, m_y2 = maybe_iline
        iline_length = math.sqrt(((m_x1-m_x2)**2.0 + ((m_y1-m_y2)**2.0)))
        if shortest_iline_length is None:
            shortest_iline_length = iline_length
        if longest_iline_length is None:
            longest_iline_length = iline_length
        shortest_iline_length = min(iline_length, shortest_iline_length)
        longest_iline_length = max(iline_length, longest_iline_length)

    if shortest_iline_length is not None and longest_iline_length is not None:
        shortest_is_within_threshold = shortest_iline_length >= (1.0-line_similarity_threshold) * line_length
        longest_is_within_threshold = longest_iline_length <= (1.0+line_similarity_threshold) * line_length
        if shortest_is_within_threshold and longest_is_within_threshold:
            # line is mostly isolated, save for similarly-sized features
            hits_with_only_similars_nearby.append(line)


for idx, line in enumerate(hits_with_only_similars_nearby):
    x1, y1, x2, y2 = line
    print(f"Line {idx+1}: Start({x1}, {y1}) - End({x2}, {y2})")
    cv2.line(lines_output_image, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Red lines


output_image = np.concatenate((
    image,
    cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR),
    contours_output_image,
    lines_output_image,
), axis=1)

cv2.imwrite(analysis_output_image, output_image)
print(f'Wrote to {analysis_output_image}')
os.system(analysis_output_image)
