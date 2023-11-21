#pip3 install google-cloud-vision

import os,sys
os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r"object_detection.json"

def localize_objects(path):
    from google.cloud import vision_v1 as vision
    client = vision.ImageAnnotatorClient()

    with open(path, 'rb') as image_file:
        content = image_file.read()
    image = vision.types.Image(content=content)

    objects = client.object_localization(image=image).localized_object_annotations

    print('Number of objects found: {}'.format(len(objects)))
    for object_ in objects:
        print('\n{} (confidence: {})'.format(object_.name, object_.score))



#path = sys.argv[1]
test_path = r"/home/abc/Desktop/object_detection/test_img2.jpg"
localize_objects(test_path)
