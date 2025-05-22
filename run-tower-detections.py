# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "numpy",
#   "Pillow",
#   "opencv-python",
# ]
# ///

import os
import sys
import tempfile

import cv2
import numpy as np

image_to_analyze = sys.argv[1]
analysis_output_image = os.path.join(tempfile.gettempdir(),  'out'+os.path.splitext(image_to_analyze)[1])
print(f'image_to_analyze = {image_to_analyze}')
print(f'analysis_output_image = {analysis_output_image}')

image = cv2.imread(image_to_analyze)


# Convert to grayscale
gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

# Edge detection
edges = cv2.Canny(gray, 50, 150, apertureSize=3)

# Hough Line Transform
lines = cv2.HoughLinesP(edges, rho=1, theta=np.pi / 180, threshold=150,
                        minLineLength=5, maxLineGap=4)

lines_output_image = image.copy()

if lines is not None:
    for idx, line in enumerate(lines):
        x1, y1, x2, y2 = line[0]
        print(f"Line {idx+1}: Start({x1}, {y1}) - End({x2}, {y2})")
        cv2.line(lines_output_image, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Red lines

else:
    print("No lines were detected.")

output_image = np.concatenate((
    image,
    cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR),
    cv2.cvtColor(edges, cv2.COLOR_GRAY2BGR),
    lines_output_image,
), axis=1)

cv2.imwrite(analysis_output_image, output_image)
print(f'Wrote to {analysis_output_image}')
os.system(analysis_output_image)
