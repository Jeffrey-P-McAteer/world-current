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
import random
import collections
import json

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


lines_similar_filter_output_image = image.copy()
contours_output_image = image.copy()
found_items_output_image = image.copy()

melded_lines = image.copy()
melded_lines[:] = (0, 0, 0) # Zero all pixels

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

            cv2.line(melded_lines, (x1, y1), (x2, y2), (255, 255, 255), 2)  # White lines in melded

# We now re-do the same analysis on melded_lines, which combines tiny fragments which overlap on x,y endpoints.

melded_gray = cv2.cvtColor(melded_lines, cv2.COLOR_BGR2GRAY)

# Apply threshold to segment out the pixels
#_, melded_thresh = cv2.threshold(melded_gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

# Find contours
melded_contours, _ = cv2.findContours(melded_gray, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

potential_hits = []
melded_contours_output_image = melded_lines.copy()
cv2.drawContours(melded_contours_output_image, melded_contours, -1, (0, 255, 0), 1)
for contour in melded_contours:
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
            cv2.drawContours(melded_contours_output_image, [approx], -1, (0, 255, 255), 2)
            cv2.putText(melded_contours_output_image, f"{len(potential_hits)}: {round(length, 1)} l={len(approx)}", (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (128, 128, 128), 1)
            cv2.line(melded_contours_output_image, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Red lines
            potential_hits.append(
                (x1, y1, x2, y2)
            )
            print(f'Melded potential_hit is {(x1, y1, x2, y2)}')


# we now filter by a criteria which gets rid of large results; we draw a circle around the line, and if anything outside of +- 20% of the line length is intersected we omit
# the line being rotated.
line_similarity_threshold = 0.50
hits_with_only_similars_nearby = []
for idx, line in enumerate(potential_hits):
    x1, y1, x2, y2 = line
    xmin, ymin, xmax, ymax = min(x1, x2), min(y1, y2), max(x1, x2), max(y1, y2)
    line_length = math.sqrt(((x1-x2)**2.0 + ((y1-y2)**2.0)))

    intersecting_lines = []
    for maybe_iline in potential_hits:
        m_x1, m_y1, m_x2, m_y2 = maybe_iline
        m_xmin, m_ymin, m_xmax, m_ymax = min(m_x1, m_x2), min(m_y1, m_y2), max(m_x1, m_x2), max(m_y1, m_y2)
        if (xmin < m_xmax and m_xmin < xmax and
            ymin < m_ymax and m_ymin < ymax):
            intersecting_lines.append(maybe_iline)
    shortest_iline_length = None
    longest_iline_length = None
    for maybe_iline in intersecting_lines:
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
        else:
            print(f'{idx} was omitted because it intersected {shortest_iline_length} and {longest_iline_length} length lines! (line itself was {line_length})')
    else:
        # No nearby lines, by definition should remain
        hits_with_only_similars_nearby.append(line)


for idx, line in enumerate(hits_with_only_similars_nearby):
    x1, y1, x2, y2 = line
    print(f"Line {idx+1}: Start({x1}, {y1}) - End({x2}, {y2})")
    cv2.line(lines_similar_filter_output_image, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Red lines

# We now filter hits_with_only_similars_nearby by length +- 20%
# For each list of lines we compute the top 2 most common separation distances.
def calculate_length(line):
    """
    Calculate the length of a line.

    Args:
        line (tuple): Line, represented by two points (x1, y1, x2, y2)

    Returns:
        float: Length of the line
    """
    x1, y1, x2, y2 = line
    length = np.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
    return length

def sort_lines_into_buckets(lines):
    """
    Sort a list of lines into buckets where each bucket contains lines within 20% of the same length.

    Args:
        lines (list): List of lines, where each line is represented by two points (x1, y1, x2, y2)

    Returns:
        dict: Dictionary where each key is a length range and each value is a list of lines within that range
    """
    buckets = {}
    for line in lines:
        length = calculate_length(line)
        # Calculate the length range (i.e., the bucket)
        lower_bound = length * 0.75
        upper_bound = length * 1.25
        # Find the bucket that the line belongs to
        found_bucket = False
        for key in buckets:
            if lower_bound <= key <= upper_bound:
                buckets[key].append(line)
                found_bucket = True
                break
        # If no bucket is found, create a new one
        if not found_bucket:
            buckets[length] = [line]
    return buckets

def extract_frequency(measurements, tolerance=0.1, min_count=2):
    """
    Extract the most common frequency from a list of measurements.

    Args:
        measurements (list): List of measurements
        tolerance (float, optional): Tolerance for differences in frequency. Defaults to 0.1.
        min_count (int, optional): Minimum number of occurrences required for a frequency to be considered. Defaults to 2.

    Returns:
        list: List of most common frequencies
    """
    # Calculate the differences between consecutive measurements
    #differences = np.diff(measurements)
    differences = []
    for i, a in enumerate(measurements):
        min_dist = None
        for j, b in enumerate(measurements):
            if i == j:
                continue
            else:
                if min_dist is None:
                    min_dist = abs(a-b)
                min_dist = min(abs(a-b), min_dist)
        if min_dist is not None and int(min_dist) > 0:
            differences.append(min_dist)

    # Round the differences to the nearest integer
    rounded_differences = np.round(differences)

    # Count the occurrences of each difference
    counts = collections.Counter(rounded_differences)

    # Filter the counts to only include differences that occur at least min_count times
    filtered_counts = {diff: count for diff, count in counts.items() if count >= min_count}

    # Find the most common differences
    most_common_differences = sorted(filtered_counts.items(), key=lambda x: x[1], reverse=True)
    # print(f'most_common_differences = {most_common_differences}')

    # # Check if the most common differences are within the tolerance of each other
    # frequencies = []
    # for diff, count in most_common_differences:
    #     if not frequencies or np.any(np.abs(np.array(frequencies) - diff) / np.array(frequencies) <= tolerance):
    #         frequencies.append(diff)
    # return frequencies

    # val[1] indicates how many lines went into that frequency bucket; we filter all w/ 1 or fewer out
    return sorted(list(set(int(val[0]) for val in most_common_differences if val[1] > 1)))

found_items = []
all_bucketed_hits = sort_lines_into_buckets(hits_with_only_similars_nearby)
bucketed_hits = dict()
for k,v in all_bucketed_hits.items():
    if k > 16.0 and k < 48.0: # Hard-coded "size" for tower objects; TODO better dynamic guess!
        bucketed_hits[k] = v

for size_key, lines in bucketed_hits.items():
    print(f'bucketed_hits[{size_key}] ({len(lines)} items) = {lines}')

for size_key, lines in bucketed_hits.items():
    line_centers = [((x1+x2)/2.0, (y1+y2)/2.0) for x1, y1, x2, y2 in lines]

    group_color = (random.randint(50, 250), random.randint(50, 250), random.randint(50, 250))
    frequencies_to_other_lines = None
    for idx, line in enumerate(lines):
        x1, y1, x2, y2 = line
        cv2.line(found_items_output_image, (x1, y1), (x2, y2), (255,255,255), 5)
        cv2.line(found_items_output_image, (x1, y1), (x2, y2), group_color, 4)
        if frequencies_to_other_lines is None:
            distances_to_other_line_centers = [
                math.sqrt(((line_centers[idx][0] - other_x)**2) + ((line_centers[idx][1] - other_y)**2)) for other_x, other_y in line_centers if int(other_x) != int(line_centers[idx][0]) and int(other_y) != int(line_centers[idx][1])
            ]
            frequencies_to_other_lines = extract_frequency(distances_to_other_line_centers, tolerance=5.0, min_count=2)

    if frequencies_to_other_lines is not None and len(frequencies_to_other_lines) > 0:
        # We know frequencies for one line, b/c distance is communicative that will be the same for all!
        if len(frequencies_to_other_lines) <= 4:
            # We expect only 2 for features we want, therefore add all these lines to found_items!
            print(f'The following frequencies_to_other_lines = {frequencies_to_other_lines} matches expectations, adding to results')
            found_items.extend(lines)
        else:
            print(f'The following frequencies are too divergent! frequencies_to_other_lines = {frequencies_to_other_lines}')
    else:
        print(f'Found no frequencies in {line_centers}')

for line in found_items:
    x1, y1, x2, y2 = line
    cv2.line(found_items_output_image, (x1, y1), (x2, y2), (0, 0, 255), 1) # bgr red indicates a hit

output_image = np.concatenate((
    image,
    cv2.cvtColor(thresh, cv2.COLOR_GRAY2BGR),
    contours_output_image,
    cv2.cvtColor(melded_gray, cv2.COLOR_GRAY2BGR),
    melded_contours_output_image,
    lines_similar_filter_output_image,
    found_items_output_image,
), axis=1)

cv2.imwrite(analysis_output_image, output_image)
print(f'Wrote to {analysis_output_image}')
os.system(analysis_output_image)
