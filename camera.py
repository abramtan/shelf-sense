import libcamera
from picamera2 import Picamera2
from datetime import datetime
import os

def take_photo():
    # get current date and time
    current_dateTime = datetime.now()
    current_dateTime_str = current_dateTime.strftime("%Y-%H-%M-%S")

    # create camera object
    picam = Picamera2()

    # configure camera settings
    config = picam.create_still_configuration(main={"size": (3280,2464)})
    # picam.start_preview(Preview.QTGL)
    config["transform"] = libcamera.Transform(hflip=1, vflip=1)
    picam.configure(config)

    # check if /photos folder is created
    photos_path = os.path.join(os.getcwd(), 'photos')
    if os.path.isdir(photos_path):
        photo_filename = f"photos/{current_dateTime_str}.jpg"
    else:
        os.mkdir(photos_path)
        photo_filename = f"photos/{current_dateTime_str}.jpg"

    # take a photo
    picam.start()
    # time.sleep(2)
    picam.capture_file(photo_filename)
    picam.close()

    return os.path.abspath(photo_filename)