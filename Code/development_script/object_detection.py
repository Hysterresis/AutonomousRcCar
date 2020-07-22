# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
r"""An example using `DetectionEngine` to perform object/face detection
with an image.

The following command runs this example for object detection using a
MobileNet model trained with the COCO dataset (it can detect 90 types
of objects). It saves a copy of the given image at the location specified by
`output`, with bounding boxes drawn around each detected object.

python3 object_detection.py \
--model models/mobilenet_ssd_v2_coco_quant_postprocess_edgetpu.tflite \
--label models/coco_labels.txt \
--input images/grace_hopper.bmp \
--output ${HOME}/object_detection_results.jpg

If you pass a model trained to detect faces, you can exclude the `label`
argument:

python3 object_detection.py \
--model models/mobilenet_ssd_v2_face_quant_postprocess_edgetpu.tflite \
--input images/grace_hopper.bmp \
--output ${HOME}/face_detection_results.jpg

Note: Currently this only supports SSD model with postprocessing operator.
Other models such as YOLO won't work.
"""

import argparse

import sys, getopt, os,inspect
currentdir = os.path.dirname(os.path.abspath(inspect.getfile(inspect.currentframe())))
parentdir = os.path.dirname(currentdir)
sys.path.insert(0,parentdir)

from edgetpu.detection.engine import DetectionEngine
from edgetpu.utils import dataset_utils, image_processing
import yaml
import cv2
import time
from PIL import Image
from my_camera import PicameraController
import numpy as np

def main():
    with open('conf.yaml') as fd:
        conf = yaml.load(fd, Loader=yaml.FullLoader)

    camera = PicameraController(
            cam_param_dict = [(arg, value) for (arg, value) in conf['CAMERA']['parameters'].items() if value != None]
        )

    # Initialize engine.
    engine = DetectionEngine("/home/pi/Documents/AutonomousRcCar/autonomouscar/resources/model_quantized_edgetpu.tflite")
    labels = dataset_utils.read_label_file("/home/pi/Documents/AutonomousRcCar/autonomouscar/resources/sign_label.txt")

    with camera:
        while True:
            
            img = camera.current_frame
            # Run inference.
            objs = engine.detect_with_image(Image.fromarray(img), keep_aspect_ratio =False, relative_coord=False,threshold=0.2,top_k=10)

            # Print and draw detected objects.
            for obj in objs:
                obj_height_pix = obj.bounding_box[1][1]  - obj.bounding_box[0][1]
                cv2.rectangle(img,tuple(obj.bounding_box[0].astype(int)),tuple(obj.bounding_box[1].astype(int)),color=(255,0,0))
                cv2.putText(img, f"{labels[obj.label_id]} ({obj.score*100:.0f}%) pix: {obj_height_pix:.0f} d: {(1.8*80*480)/(10*obj_height_pix*2.738):.1f}",tuple(obj.bounding_box[0].astype(int)-(70,0)),cv2.FONT_HERSHEY_SIMPLEX, 0.5, conf["DISPLAY"]["textColor"], 1)

            if not objs:
                print('No objects detected.')

            cv2.namedWindow("Objects", cv2.WINDOW_NORMAL)
            cv2.imshow("Objects", cv2.cvtColor(img, cv2.COLOR_RGB2BGR))

            # Quit
            key = cv2.waitKey(1)
            if key == ord("q"):
                break

if __name__ == '__main__':
  main()