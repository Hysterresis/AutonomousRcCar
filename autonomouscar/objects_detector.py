import cv2
import logging
import datetime
import time
from edgetpu.detection.engine import DetectionEngine
from edgetpu.utils import dataset_utils, image_processing
from PIL import Image
from traffic_objects import *
from threading import Thread

_SHOW_IMAGE = False


class ObjectsDetector:
    """
    """
    def __init__(self, conf, camera, car_state):
        self.camera = camera
        self.car_state = car_state
        self.conf = conf
        
        # Initialize engine.
        self.engine = DetectionEngine(conf['OBJECT_DETECTION']['model_fname'])


        # Init a dictonary with obj_id and obj_label as key, and the corresponding traffic object class as value
        self.traffic_objects = dict.fromkeys([0, 'Battery'], Battery(conf)) 
        self.traffic_objects.update(dict.fromkeys([1, 'SpeedLimit25'], SpeedLimit(conf, 25)))
        self.traffic_objects.update(dict.fromkeys([2, 'SpeedLimit50'], SpeedLimit(conf, 50)))
        self.traffic_objects.update(dict.fromkeys([3, 'StopSign'], StopSign(conf)))
        self.traffic_objects.update(dict.fromkeys([4, 'TrafficLightGreen'], TrafficLight(conf, 'green')))
        self.traffic_objects.update(dict.fromkeys([5, 'TrafficLightOff'], TrafficLight(conf, 'off')))
        self.traffic_objects.update(dict.fromkeys([6, 'TrafficLightRed'], TrafficLight(conf, 'red')))

        # Var to stop the thread
        self.stopped = False

    def __enter__(self):
        """ Entering a with statement """
        self.startThread()
        return self
    
    def __exit__(self, exception_type, exception_value, traceback):
        self.stopThread()
        """ Exit a with statement"""

    def startThread(self):
        # start the thread to follow the road
        t = Thread(target=self._run, name="ObjectDetector", args=())
        t.start()
        return self

    def stopThread(self):
        # indicate that the thread should be stopped
        self.stopped = True

    def _run(self):
        while not self.stopped:
            img = self.camera.current_frame
            # Run inference.
            objs = self.engine.detect_with_image(
                Image.fromarray(img), 
                keep_aspect_ratio =False, 
                relative_coord=False,
                threshold=self.conf['OBJECT_DETECTION']['match_threshold'],
                top_k=self.conf['OBJECT_DETECTION']['max_obj'])
            
            for obj in objs:
                traffic_obj = self.traffic_objects[obj.label_id]
                if traffic_obj.is_nearby(obj):
                    traffic_obj.present = True

                # Print and draw detected objects.
                if self.conf["DISPLAY"]["show_plots"]:
                    cv2.rectangle(img,tuple(obj.bounding_box[0].astype(int)),tuple(obj.bounding_box[1].astype(int)), color=(255,0,0) if traffic_obj.is_nearby(obj) else (0,255,0))
                    cv2.putText(img, f"{traffic_obj.label} ({obj.score*100:.0f}%)",tuple(obj.bounding_box[0].astype(int)-(70,0)),cv2.FONT_HERSHEY_SIMPLEX, 0.5, self.conf["DISPLAY"]["textColor"], 1)

            # The 25 speed limit sign has priority.
            if self.traffic_objects['SpeedLimit25'].present:
                self.traffic_objects['SpeedLimit50'].present = False

            # The red light has priority.
            if self.traffic_objects['TrafficLightRed'].present:
                self.traffic_objects['TrafficLightOff'].present = False
                self.traffic_objects['TrafficLightGreen'].present = False

            # Each TrafficSignProcessor change the car state
            map(lambda x: x.set_car_state(self.car_state), self.traffic_objects)  