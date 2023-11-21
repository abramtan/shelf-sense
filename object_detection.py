#pip3 install google-cloud-vision

import os,sys
from camera_object_detector import take_photo
from rgb_led import *
from collections import Counter
import time
from PIL import Image

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r"object_detection.json"

def localize_objects(path):
    from google.cloud import vision_v1 as vision
    client = vision.ImageAnnotatorClient()

    with open(path, 'rb') as image_file:
        content = image_file.read()
    image = vision.types.Image(content=content)

    objects = client.object_localization(image=image).localized_object_annotations

    #print('Number of objects found: {}'.format(len(objects)))
    
    objects_list = []
    
    for object_ in objects:
        #print('\n{} (confidence: {})'.format(object_.name, object_.score))
        objects_list.append(object_.name)
        
    object_dict_count = Counter(objects_list)
    
    return object_dict_count

#path = sys.argv[1]

# # for testing
#test_path = r"/home/abc/Desktop/shelfsense/test_img2.jpg"
#object_count = localize_objects(test_path)
#print(object_count)
#print(type(object_count))
#print(object_count["Apple"])

def identify_photo_objects():
    leds_on()
    time.sleep(2)
    photo_path = take_photo()
    object_count = localize_objects(photo_path)
    time.sleep(1)
    leds_off()
    return photo_path, object_count

if __name__ == "__main__":
    object_count = identify_photo_objects()
    print(object_count)

    
