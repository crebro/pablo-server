import cv2
import zxingcpp
import os
import numpy as np
import cv2

def readCode(image):
    detected_barcodes = zxingcpp.read_barcodes(image)
    
    sortedBarcodes = sorted(detected_barcodes, key=lambda barcode: (barcode.position.top_left.y, barcode.position.top_left.x))
    codes = []
    for barcode in sortedBarcodes:
        code = barcode.text
        codes.append(code)
    return codes

def properOrientedOutput(image):
    n=0
    while True:
        n+=1
        if n==6:
            return {
                "status": "failed",
                "message": "Too many Failed attempts. \nAborting. \nPlease check Image again."
            }
        codes = readCode(image)
        if not(len(codes) > 2):
            print(codes)
            print("letting run once again")
            pass
        elif codes[0].lower() != "start":
            print(f"Barcode not in Correct Orientation. \nRotating image.")
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
            print(f"Image rotated. \nTrying again.")
        else:
            break
    for code in codes:
        if code.lower() == 'Start' or code.lower() == 'end':
            codes.remove(code)
    return {
        "status": "success",
        "commands": codes
    }


def process_image(file):
    file_bytes = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    result = properOrientedOutput(image)

    return result

    