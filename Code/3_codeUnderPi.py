from pubnub.pubnub import PubNub, SubscribeListener, SubscribeCallback, PNStatusCategory
from pubnub.pnconfiguration import PNConfiguration
import time
import sys
import RPi.GPIO as GPIO
from picamera2 import Picamera2
import sqlite3
import os
import cv2  # Assuming OpenCV is installed for YOLO
from ultralytics import YOLO # Import YOLO
from gpiozero import DistanceSensor

# YOLO setup (adjust as needed)
model = YOLO(r"/home/pi/Desktop/best.pt")

# Database setup
'''
conn = sqlite3.connect('image_store.db')
c = conn.cursor()
#c.executeCREATE TABLE IF NOT EXISTS images (id INTEGER PRIMARY KEY, path TEXT))
conn.commit()
'''
# Initialize PiCamera
picam2 = Picamera2()
camera_config = picam2.create_preview_configuration()
picam2.configure(camera_config)

# Initialize GPIO pins
GPIO.setmode(GPIO.BCM)
#GPIO.setwarnings(False)
# Rest of your GPIO setup...
TRIG = 4
ECHO = 17
RED_LED_PIN = 18
GPIO.setup(TRIG, GPIO.OUT) 
GPIO.setup(ECHO, GPIO.IN)
ultrasonic = DistanceSensor(echo=ECHO, trigger=TRIG, threshold_distance=0.2)

sendMsg = True



# PubNub Configuration
pnconf = PNConfiguration()
pnconf.publish_key = 'pub-c-3335be66-434a-496a-bead-f63156d13ccc'
pnconf.subscribe_key = 'sub-c-0a899813-96ce-4536-abe1-84bb4a033180'
pnconf.uuid = 'Uuid'
pubnub = PubNub(pnconf)
channel = 'Group2'

# Function to handle motion detection and capture image
def handle_motion():
    global sendMsg
    try:
        while True:
            if ultrasonic.wait_for_in_range():
                print("In range")
                if sendMsg:
                    pubnub.publish().channel(channel).message({'Motion Detected':True}).sync()
                    sendMsg = False
                    time.sleep(1)
                    return True

            else :
                print("Out of range")
                sendMsg = True
                time.sleep(1)
                
    except KeyboardInterrupt:
        GPIO.cleanup()  # Cleanup GPIO on keyboard interrupt
        return False
    
    finally:
        print("Exiting handle_motion")


# Function to capture image and save to SQLite
def capture_image():
    print("strat camera")
    image_path = 'images/image.jpg'
    #picam2.start_preview(Preview.QTGL)
    picam2.start()
    print("sleep")
    time.sleep(1)
    picam2.capture_file(image_path)
    picam2.stop()
    #picam2.stop_preview()
    print("camera end")
    #c.execute("INSERT INTO images (path) VALUES (?)", (image_path,))
    #conn.commit()
    #identify_object(image_path)


# Function to identify object using YOLO
def live_stream_detection():
    
    print("in to live ")
# Initialize counter and parameter
    video_path = r"/home/pi/Desktop/SEP 728 Project/images/image.jpg"
    cap = cv2.VideoCapture(video_path)

# Initialize counter and parameter
    host_counter = 0
    person_identity = ""

# Loop through the video frames
    while cap.isOpened():
        success, frame = cap.read()
        if success:
        # Run YOLOv8 inference on the frame
            results = model(frame)

        # Check for host confidence score, only when detection runs a confidence score of over 0.95, we consider this as a validation for the host
            for detection in results:
                if detection.probs.data[1] > 0.90:
                    host_counter += 1
                    break

        # Check if host has been detected with high confidence 30 times
        if host_counter >= 1:
            person_identity = "Host"
            break
        else:
        # Break the loop if the end of the video is reached
            break

# Set parameter based on counter
    if person_identity == "":
        person_identity = "unknown guest"

# Release the video capture object and close the display window
    cap.release()

# Output the final decision
    print(person_identity)
    check_host_via_video_result(person_identity)


# Liam Edit: Function to check if the person is the host or not
def check_host_via_video_result(person_identity):
    global sendMsg 
    # Implement your host checking logic here
    GPIO.setmode(GPIO.BCM)
    if not person_identity == "Host":
        pubnub.publish().channel(channel).message('Guest').sync()
        GPIO.setup(RED_LED_PIN, GPIO.OUT)
        GPIO.output(RED_LED_PIN, True)
        time.sleep(5)
        GPIO.output(RED_LED_PIN, False)
        sendMsg = True
    else:
        print("host")
        time.sleep(5)
        pubnub.publish().channel(channel).message('Welcome Home').sync()
        sendMsg = True
        
        
# Main loop
try:
    while True:
        motion_detected = handle_motion()
    
        if motion_detected:
            
            capture_image()
            
            live_stream_detection()
            
except KeyboardInterrupt:
    print("Main loop KeyboardInterrupt")
    GPIO.cleanup()  # Cleanup GPIO on keyboard interrupt
    
