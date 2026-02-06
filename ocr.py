import keras_ocr
import cv2
import numpy as np

# ===================================
# Load image
# ===================================
image_path = "rokok.jpg"
img = cv2.imread(image_path)

# ===================================
# Preprocess (embossed text boost)
# ===================================
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
gray = clahe.apply(gray)
gray = cv2.bilateralFilter(gray, 11, 17, 17)

thresh = cv2.adaptiveThreshold(
    gray, 255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY_INV,
    31, 7
)

cv2.imwrite("processed.png", thresh)

# ===================================
# OCR (keras-ocr)
# ===================================
pipeline = keras_ocr.pipeline.Pipeline()  # loads local models
prediction_groups = pipeline.recognize([thresh])

# ===================================
# Extract digits ONLY
# ===================================
all_digits = []

for text, box in prediction_groups[0]:
    digits = ''.join(c for c in text if c.isdigit())
    if digits:
        all_digits.append(digits)

print("Detected digits:", all_digits)

# Pick longest number
if all_digits:
    best = max(all_digits, key=len)
    print("Most likely:", best)
else:
    print("No digits detected.")



# cara run program scrapping
# source venv/bin/activate  
# python ocr.py  
