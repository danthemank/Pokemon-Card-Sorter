import os, sys, cv2, json
from datetime import datetime
from PIL import Image
import pandas as pd
from demoUI.matchWrapper import matchWrapper
from demoUI.busServoWrapper import busServoWrapper
from demoUI.servoSetup import servoSetup
from random import randint, random
from demoUI.settings import app
from demoUI.settings import settings 
from demoUI.card_data import card_data
from demoUI.websocket_server import websocket_client
from flask import Flask, request
from flask import render_template
import io
import re
import base64
from subprocess import PIPE, Popen
import time 
import threading
import traceback
import numpy as np
import keyboard
import base64
import asyncio
from concurrent.futures.thread import ThreadPoolExecutor
from concurrent.futures import as_completed

try:
    import msvcrt
    is_windows = True
except ImportError:
    import sys, termios    #for linux/unix
    is_windows = False

using_simulator = False

useMultiProccess = settings['use_multi_proccess']
#print(f"use multi process")
#print(useMultiProccess)
process_number = settings['process_number']
cards_number = settings['cards_number']
useRemote = settings['use_remote']
use_gpio = settings["use_gpio"]


if use_gpio:
    try:
        import RPi.GPIO as GPIO
        from rpi_hardware_pwm import HardwarePWM
        import pigpio
    except ImportError:
        print('')
        print('!!! Error importing RPi.GPIO! This is probably because you need superuser privileges. You can achieve this by using "sudo" to run your script')
        print('!!! If you are not using a Raspberry Pi, you can ignore this error')
        print('!!! If you are using a Raspberry Pi and still see this error, make sure you have installed the RPi.GPIO package correctly')
        print('!!! Run this command to install it: sudo pip install RPi.GPIO')
        print('!!! Using SimulRPi.GPIO instead')
        print('')
        import SimulRPi.GPIO as GPIO
        GPIO.setprinting(False)
        using_simulator = True

        key_channel_map = {'ctrl': settings['pin_button']}
        GPIO.setkeymap(key_channel_map)
        #GPIO.setdefaultsymbols("default_ascii")

class controller:
    def __init__(self):
        self.busServo = None
        self.dealer_running = False
        self.rotate_platform = False
        self.button_pressed_b = False
        self.busServoLastPos  = 0
        self.exit_bin_position = 0
        self.use_daemon = False
        self.use_hardware_pwm = False
        self.event_loop = None
        pass

    def __del__(self):
        pass

    def __enter__(self):
        # Initialize any resources here
        if useMultiProccess:
            self.matchWrapper = matchWrapper()
            self.matchWrapper.initialize_workers(process_number, cards_number)

        return self

    def __exit__(self, exc_type, exc_value, traceback):
        # Clean up resources here
        #print('Controller destructor called')
        if useMultiProccess:
            self.matchWrapper.terminate_workers()

        if self.busServo:
            self.busServo.soft_exit()

    async def startVideoFeed(self, showImageFeed=False, activateHardware=True, manualMode=False, onlyVideo=False):
        videoLoopThread = None
        self.last_image_match=None
        self.last_match_source=None
        self.dealer_alarm_time=None
        self.showImageFeed = showImageFeed
        try:
            self.event_loop = asyncio.get_event_loop()

            self.lastFrame=None
            self.img_counter = 0
            self.onlyVideo = onlyVideo
            self.manualMode = manualMode

            if not self.onlyVideo:
                self.activateHardware=activateHardware
                self.setupIO()
            else:
                self.activateHardware = False

            self.analysing_image_event = None
            self.analysing_image_event = threading.Event()
            self.analysing_image_event.set()

            self.runningVideoFeed = True
            self.pauseClassifyLoop = True






            #self.powerOnDealer()

            #self.turn_light_on()

            if not onlyVideo:
                await self.moveCardPlatform('rest')

            self.enter_button_event = threading.Event()
            self.enter_button_event.clear()

            loop = asyncio.get_running_loop()
            executor = ThreadPoolExecutor(max_workers=5)
            funcs = [
                 self.runVideoFeed(None)
                ,self.detectButtonPress(None)
                ,self.process_images_loop(None)
                ,self.readKeyboardEvents(None)
            ]

            # Use executor to submit and await the coroutines
            futures = [loop.run_in_executor(executor,  lambda: asyncio.run(func)) for func in funcs]

            # Wait for all coroutines to complete
            results = await asyncio.gather(*futures)

            #results = await asyncio.gather(*futures)

            if not self.onlyVideo:
                GPIO.cleanup()
            return
        except (KeyboardInterrupt, Exception) as ex:
            print('\nInterrupted')
            traceback.print_exc()
            if not self.onlyVideo:
                GPIO.cleanup()
            try:
                sys.exit(0)
            except SystemExit:
                os._exit(0)
        finally:
            if not self.onlyVideo:
                GPIO.cleanup()
            if videoLoopThread !=None:
                videoLoopThread.join()

    async def readKeyboardEvents(self, parameter):
        print('waiting for keyboard')
        self.enter_button_event = threading.Event()
        self.enter_button_event.clear()

        while self.runningVideoFeed:
            print()
            print('Press ENTER key or hardware button to pause/continue')
            print('Write ESC EXIT or press CTRL-Z to exit')

            controller.flush_input()
            if settings['run_interactive']:
                k=input('waiting for button\n')
            else:
                self.enter_button_event.clear()
                self.enter_button_event.wait()
                k='enter'

            await self.processUserEvents(k)
            await asyncio.sleep(int(settings['wait_for_processing']))

    async def processUserEvents(self, k):
        k=k.lower()
        print(f"key pressed: {k}")
        if k =='esc' or k=='exit':
            self.runningVideoFeed = False
            raise Exception('Exit')
            #break
        elif k=='enter' or k=='':
            await self.onStartPauseButton()
        elif k=='bin':
            self.button_pressed_b = not self.button_pressed_b
            #self.button_callback('B')
            await self.button_callback('D')
        elif k=='pow':
            await self.powerOnDealer()

    def simulateKeyboardEvent(self):
        file_path = "/home/goodwill/pokemonCard/pokemonCardUi/keyboard.txt"
        # Open the file in read mode
        with open(file_path, 'r') as file:
            # Read the contents of the file
            file_contents = file.read()

            # Check if the file is empty
            if not file_contents:
                print("The file is empty.")
                return False
            else:
                print("The file is not empty.")
                return True
    def rotatePlatform(self):
        if self.rotate_platform:
            self.busServoLastPos, speed = self.busServo.read_state()
            if abs( self.busServoLastPos - 4096)<50:
                self.busServo.set_position(0)
            elif abs( self.busServoLastPos )<50:
                self.busServo.set_position(4096)

    async def process_images_loop(self, parameter):
        while self.runningVideoFeed:
            try:
                if self.rotate_platform:
                    self.rotatePlatform()
 
                if self.lastFrame is None or self.pauseClassifyLoop:
                    await asyncio.sleep(1)
                    continue
                elif GPIO.input(self.pin_button_c) and not using_simulator:
                    print('waiting for card...')
                    await asyncio.sleep(1)
                    continue
                elif False:#TODO: test delete
                    print('droping next card')
                    await self.turn_light_on()
                    await asyncio.sleep(1)
                    self.turn_light_off()
                    await asyncio.sleep(1)
                elif not self.onlyVideo:
                    await self.activateCardDealer()

                    value_range = await self.processFrame()
                    if value_range == 'high':
                        await self.activateBlowerHighValue()
                    elif value_range == 'mid':
                        await self.activateBlowerMidValue()
                    else: #value_range == 'low'
                        await self.activateBlowerLowValue()

                if self.manualMode:
                    self.pauseClassifyLoop = True

            except (KeyboardInterrupt, Exception) as ex:
                print('\nError')
                traceback.print_exc()




    async def turn_light_on(self, pin='A'):
        print(f"light {pin} on")
        if self.activateHardware:
            if pin=='A':
                GPIO.output(self.channel_light_A, GPIO.HIGH)
            else:
                GPIO.output(self.channel_light_B, GPIO.HIGH)
        await asyncio.sleep(int(settings['wait_for_lights']))

    def turn_light_off(self, pin='A'):
        print(f"light {pin} off")
        #return #todo delete
        if self.activateHardware:
            if pin=='A':
                GPIO.output(self.channel_light_A, GPIO.LOW)
            else:
                GPIO.output(self.channel_light_B, GPIO.LOW)

    async def processFrame(self):
        #self.last_image_match = None
        print("Capturing image")
        self.img_counter += 1
        if self.lastFrame is None:
            return

        if self.lastFrame is not  None:
            await self.turn_light_on()
            cv2_im = cv2.cvtColor(self.lastFrame, cv2.COLOR_BGR2RGB)
            pil_im = Image.fromarray(cv2_im)
            self.turn_light_off()

        if self.lastFrame_b is not None:
            await self.turn_light_on('B')
            cv2_im_b = cv2.cvtColor(self.lastFrame_b, cv2.COLOR_BGR2RGB)
            pil_im_b = Image.fromarray(cv2_im_b)
            self.turn_light_off('B')


        print('\nanalysing card')

        self.analysing_image_event.clear()

        result = await self.identifyImage(pil_im);

        self.analysing_image_event.set()

        if result['result'] == 'backside':
            if self.lastFrame_b is None:
                return
            result = await self.identifyImage(pil_im_b, use_camera_b=True)

        #print(str(result)[:550])
        result.pop('matchedCardImage')
        result.pop('artworkImage')
        print('\n')
        print(result)

        return self.evaluateCardValue(result)
  

    async def runVideoFeed(self, parameter):
        showImageFeed = self.showImageFeed
        camera_port_a = settings['camera_A_port']
        camera_port_b = settings['camera_B_port']
        #resolution=[320, 240]
        #resolution=[640, 480]
        resolution= [ settings['camera_resolution'][0], settings['camera_resolution'][1] ]
        print(f'camera resolution: {resolution}')

        fourcc = cv2.VideoWriter_fourcc(*'YU12')

        if camera_port_a>=0:
            cam = cv2.VideoCapture(camera_port_a)
            ret = cam.set(cv2.CAP_PROP_FOURCC, fourcc)
            cam.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        else:
            cam=None
            ret = None

        if camera_port_b>=0:
            cam_b = cv2.VideoCapture(camera_port_b)
            ret_b = cam_b.set(cv2.CAP_PROP_FOURCC, fourcc)
            cam_b.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            cam_b.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        else:
            cam_b=None
            ret_b=None
        #cam = cv2.VideoCapture(0, cv2.CAP_DSHOW) # this is the magic!

        #cam.set(cv2.CAP_PROP_FRAME_WIDTH, 4096)
        #cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)

        #cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1640)
        #cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1232)
        
        #resolution=[820, 616]

        #if showImageFeed:
        #    cv2.namedWindow("Card Sorter", cv2.WINDOW_NORMAL)

        self.websocket = websocket_client('ws://localhost:8080')
        #asyncio.set_event_loop(self.event_loop)
        #self.event_loop.run_until_complete (self.websocket.connect())
        #self.event_loop_camera_feed = asyncio.new_event_loop()
        #asyncio.set_event_loop(self.event_loop_camera_feed)
        await self.websocket.connect()

        k=0
        while self.img_counter<settings['max_frame_takes'] or settings['max_frame_takes']==0:
            try:
                if not self.runningVideoFeed:
                    break

                if cam == None:
                    ret = None
                    frame=None
                else:
                    ret, frame = cam.read()
                    if not ret:
                        print("failed to grab frame - camera A")
                        break

                if cam_b == None:
                    ret_b = None
                    frame_b=None
                else:
                    ret_b, frame_b = cam_b.read()
                    if not ret_b:
                        print("failed to grab frame - camera B")
                        break

                square_limits=settings['square_limits'],
                flipHorizontally=settings['flipHorizontally'],
                flipVertically=settings['flipVertically'],

                square_limits_b=settings['square_limits_b'],
                flipHorizontally_b=settings['flipHorizontally_b'],
                flipVertically_b=settings['flipVertically_b'],

                x_square_limits=settings['x_square_limits']
                x_square_limits_b=settings['x_square_limits_b']

                if (flipHorizontally[0]=='true'):
                    frame=cv2.flip(frame, 1);
                if (flipVertically[0]=='true'):
                    frame=cv2.flip(frame, 0);

                if (flipHorizontally_b[0]=='true'):
                    frame_b=cv2.flip(frame_b, 1);
                if (flipVertically_b[0]=='true'):
                    frame_b=cv2.flip(frame_b, 0);

                rotateCameraA=settings['rotate_camera_A']
                rotateCameraB=settings['rotate_camera_B']

                if rotateCameraA != 0:
                    height, width = frame.shape[:2]
                    center = (width // 2, height // 2)
                    angle = rotateCameraA
                    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                    frame = cv2.warpAffine(frame, rotation_matrix, (width, height))
                    #cv2.imshow('Rotated Image', frame)
                    #cv2.waitKey(0)

                if rotateCameraB != 0:
                    height, width = frame_b.shape[:2]
                    center = (width // 2, height // 2)
                    angle = rotateCameraB
                    rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)
                    frame_b = cv2.warpAffine(frame_b, rotation_matrix, (width, height))

                cv2.rectangle(frame, (square_limits[0][0], square_limits[0][1]), (square_limits[0][0]+square_limits[0][2], square_limits[0][1]+square_limits[0][3]), (255, 255, 155), 2)
                cv2.rectangle(frame_b, (square_limits_b[0][0], square_limits_b[0][1]), (square_limits_b[0][0]+square_limits_b[0][2], square_limits_b[0][1]+square_limits_b[0][3]), (255, 255, 255), 2)


                cv2.rectangle(frame, (x_square_limits[0], x_square_limits[1]), (x_square_limits[0]+x_square_limits[2], x_square_limits[1]+x_square_limits[3]), (255, 255, 155), 2)
                cv2.rectangle(frame_b, (x_square_limits_b[0], x_square_limits_b[1]), (x_square_limits_b[0]+x_square_limits_b[2], x_square_limits_b[1]+x_square_limits_b[3]), (255, 255, 255), 2)



                if frame_b is None:
                    max_height = frame.shape[0]
                else:
                    max_height = max(frame.shape[0], frame_b.shape[0])

                image1_resized = cv2.resize(frame, (int(frame.shape[1] * max_height / frame.shape[0]), max_height))
                if frame_b is None:
                    image2_resized = None
                else:
                    image2_resized = cv2.resize(frame_b, (int(frame_b.shape[1] * max_height / frame_b.shape[0]), max_height))

                if self.last_image_match:
                    matched_image= cv2.imread(self.last_image_match)
                    matched_image_resized = cv2.resize(matched_image, (int(matched_image.shape[1] * max_height / matched_image.shape[0]), max_height))

                    matched_image2= cv2.imread(self.last_match_source)
                    matched_source_resized = cv2.resize(matched_image2, (int(matched_image2.shape[1] * max_height / matched_image2.shape[0]), max_height))

                    if frame_b is None:
                        combined_image = cv2.hconcat([matched_source_resized, matched_image_resized, image1_resized ])
                        #combined_image = cv2.hconcat([matched_image_resized, image1_resized ])
                    else:
                        combined_image = cv2.hconcat([matched_source_resized, matched_image_resized, image1_resized, image2_resized])
                        #combined_image = cv2.hconcat([matched_image_resized, image1_resized, image2_resized])
                else:
                    if frame_b is None:
                        combined_image = image1_resized
                    else:
                        combined_image = cv2.hconcat([image1_resized, image2_resized])

                scale_percent = settings['preview_scale_percent']  # Change this value to resize the image to a different percentage
                width = int(combined_image.shape[1] * scale_percent / 100)
                height = int(combined_image.shape[0] * scale_percent / 100)
                dim = (width, height)
                resized_image = cv2.resize(combined_image, dim, interpolation=cv2.INTER_AREA)

                await self.publishImageFeed(combined_image)
                #print('showing frame')
                if showImageFeed:
                    cv2.imshow('Card Sorter - camera A/B', resized_image)
                    desired_frame_rate=0.5#images per second
                    #desired_frame_rate=2#images per second
                    #k = cv2.waitKey(int(1000 / desired_frame_rate))

                    desired_frame_rate = float(settings['wait_for_capture'])
                    k = cv2.waitKey(int(1000 * desired_frame_rate))
                else:
                    await asyncio.sleep(float(settings['wait_for_capture']))

                self.lastFrame = frame
                self.lastFrame_b = frame_b

                if self.analysing_image_event and settings['pause_videofeed']:
                    self.analysing_image_event.wait()
            except Exception as ex:
                print(ex)
                raise(ex)
        
        self.runningVideoFeed = False
        cam.release()
        cv2.destroyAllWindows()

    async def publishImageFeed(self, resized_image=None, message=None, is_result=False, cardValues=None, artwork_data=None):
        try:
            #print('update camera  feed')
            if resized_image is not None:
                _, buffer = cv2.imencode('.jpg', resized_image)
                base64_image = base64.b64encode(buffer).decode('utf-8')
            else:
                base64_image = None
            message  = {
                        #convert image to base 64
                         'running' : self.dealer_running
                        ,'message': message
                        ,'is_result': is_result
                        ,'frame' : base64_image
                        ,'cardValues' : cardValues
                        ,'artwork_data' : artwork_data
                    }

            await self.websocket.send_message(json.dumps(message))
        except Exception as ex:
            pass
            print(ex)


    async def testVideoFeed(self):
        showImageFeed=True
        self.img_counter = 0
        self.runningVideoFeed = True
        camera_port_a = settings['camera_A_port']
        print (f'testing camera dev{camera_port_a}')
        resolution=[320, 240]

        fourcc = cv2.VideoWriter_fourcc(*'YU12')

        if camera_port_a>=0:
            #cam = cv2.VideoCapture(camera_port_a)

            cam = cv2.VideoCapture('/dev/video2', cv2.CAP_DSHOW) # this is the magic!
            #cam = cv2.VideoCapture('/dev/video2')
            #ret = cam.set(cv2.CAP_PROP_FOURCC, fourcc)
            cam.set(cv2.CAP_PROP_FRAME_WIDTH, resolution[0])
            cam.set(cv2.CAP_PROP_FRAME_HEIGHT, resolution[1])
        else:
            cam = None

        #cam.set(cv2.CAP_PROP_FRAME_WIDTH, 4096)
        #cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 2160)

        #cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1640)
        #cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1232)
        
        #resolution=[820, 616]

        #if showImageFeed:
        #    cv2.namedWindow("Card Sorter", cv2.WINDOW_NORMAL)

        k=0
        while self.img_counter<settings['max_frame_takes'] or settings['max_frame_takes']==0:
            try:
                if cam == None:
                    ret = None
                    frame=None
                else:
                    ret, frame = cam.read()
                    if not ret:
                        print("failed to grab frame - camera A")
                        break

                square_limits=settings['square_limits'],
                flipHorizontally=settings['flipHorizontally'],
                flipVertically=settings['flipVertically'],

                x_square_limits=settings['x_square_limits']

                #print(square_limits[0])
                #dir(flipHorizontally[0])
                #dir(flipHorizontally[0])

                if (flipHorizontally[0]=='true'):
                    frame=cv2.flip(frame, 1);
                if (flipVertically[0]=='true'):
                    frame=cv2.flip(frame, 0);


                cv2.rectangle(frame, (square_limits[0][0], square_limits[0][1]), (square_limits[0][0]+square_limits[0][2], square_limits[0][1]+square_limits[0][3]), (255, 255, 255), 2)

                cv2.rectangle(frame, (x_square_limits[0], x_square_limits[1]), (x_square_limits[0]+x_square_limits[2], x_square_limits[1]+x_square_limits[3]), (255, 255, 255), 2)


                if showImageFeed:
                    #frame_small = cv2.resize(frame, (960, 540))                # Resize image
                    #frame=frame_small

                    #cv2.imshow("Card Sorter - camera A", frame)
                    #cv2.imshow("Card Sorter - camera B", frame_b)

                    max_height = max(frame.shape[0], 0)

                    image1_resized = cv2.resize(frame, (int(frame.shape[1] * max_height / frame.shape[0]), max_height))

                    combined_image = image1_resized

                    scale_percent = 200  # Change this value to resize the image to a different percentage
                    width = int(combined_image.shape[1] * scale_percent / 100)
                    height = int(combined_image.shape[0] * scale_percent / 100)
                    dim = (width, height)
                    resized_image = cv2.resize(combined_image, dim, interpolation=cv2.INTER_AREA)

                    cv2.imshow('Card Sorter - camera A/B', resized_image)

                    k = cv2.waitKey(1)
                    k=-1
                else:
                    await asyncio.sleep(float(settings['wait_for_capture']))
                    #k=32

                self.lastFrame = frame
                #self.lastFrame_b = frame_b

                if k%256 == 27 or not self.runningVideoFeed:
                    # ESC pressed
                    print("Escape hit, closing...")
                    break
                elif k%256 == 32:
                    # SPACE pressed
                    #self.processFrame()
                    pass

            except Exception as ex:
                print(ex)
                raise(ex)
        
        self.runningVideoFeed = False
        cam.release()
        cv2.destroyAllWindows()




    async def identifyImage(self, imageFile: Image, use_camera_b=False, image_range=None):
        start_time=datetime.now()
        print(f"Identify Image - Start time is {start_time}")

        imagePath="{saved_image_path}{date}.{format}".format(saved_image_path=settings['saved_image_path'], date=str(datetime.now().strftime("%Y%m%d%H%M%S")), format=settings['saved_image_format'])

        #cv2.imwrite(imagePath, frame)
        image_folder= settings['saved_image_path']
        if not os.path.exists(image_folder):
            os.makedirs(image_folder)

        imageFile.save(imagePath,settings['saved_image_format'])

        print("\n\nImage saved to {}".format(imagePath))

        #database_csv_path=os.path.join(settings['database_base_path'],settings['database_cvs_file'])

        #dfPokemon=pd.read_csv(database_csv_path)
        resultScript=''

        #imageName=matchWrapper.matchImageScript(imagePath) 
        #imagePath='C:/Users/cocoa/Documents/GitHub/pokemonCardFiles/savedImages/{0}.jpg'.format( randint(1,3))
        #imagePath='C:/Users/cocoa/Documents/GitHub/pokemonCardFiles/savedImages/a1.jpg'

        only_high_price=settings['only_high_price']
        message = ''

        if useRemote:
            imageName, confidence, message = await matchWrapper.matchImageRemote(imagePath, use_camera_b, self.event_loop)
        elif useMultiProccess:
            imageName, confidence, message = self.matchWrapper.matchImageQueue(imagePath, use_camera_b) 
            print(imageName, confidence, message)
        else:
            subset=None
            if only_high_price:
                subset = card_data.get_cards_sorted_by_price(price=settings['high_price_threshold'])
            imageName, confidence, message = matchWrapper.matchImage(imagePath, use_camera_b, subset)# , settings['confidence_threshold']) 

        cardValues={}
        image_data=''
        cardValues = None
        image_data = None
        artwork_data = None

        if message is None or message == '':
            result='ok' 
        else:
            result='error'

        if imageName is not None:
            #get the filename without the directory path
            file_name=os.path.basename(imageName)
            #get the file name without the extension
            card_code=file_name.split('.')[0]
            if card_code == "pokemon_card_backside":
                #return {'result':'backside'}
                result = 'backside'
                message = 'card is backside'
            else:
                print("card_code: {0}".format(card_code))
                #cardValues is row id from database for the match
                cardValues = card_data.get_card(card_code)
                if cardValues is not None:
                    image_file = os.path.join(cardValues['set_code'],cardValues['code']+".png")
                    image_data, message_file = self.readImageFileAsBase64(settings['reference_image_path'],imageName)
                    artwork_data, message_file =  self.readImageFileAsBase64(settings['artwork_image_path'],image_file)
                    self.last_image_match = os.path.join(settings['artwork_image_path'],image_file)
                    self.last_match_source = imagePath

                    if self.last_image_match and False:
                        matched_image= cv2.imread(self.last_image_match)
                        source_image = imageFile
                        
                        max_height = max(source_image.shape[0], 0)
                        
                        matched_image_resized = cv2.resize(matched_image, (int(matched_image.shape[1] * max_height / matched_image.shape[0]), max_height))
                        combined_image = cv2.hconcat([source_image, matched_image_resized])
                        
                        await self.publishImageFeed(combined_image, image_file, True, cardValues, artwork_data)


                    if message is None:
                        message  = ''
                    message = message + message_file
                else:
                    result='error'
                    message='card not found in database'
                    #self.last_image_match = None
        else:
            result='error'
            message='no match found'
            #self.last_image_match = None

        print(result, message)

        end_time=datetime.now()
        print(f"Identify Image - End time is {end_time}")
        print(f"Elapsed time is {end_time-start_time}\n\n")
 
        return {'result':result,'message':message,'script':resultScript,'matched':imageName ,'matchedCard':cardValues, 'matchedCardImage':image_data,'artworkImage':artwork_data}


    def readImageFileAsBase64(self, imageFolder, imageFileName, ):
        imageFilePath=os.path.join(imageFolder, imageFileName)
        image_data=''
        message=''
        print(imageFilePath)
        if os.path.exists(imageFilePath):
            with open(imageFilePath, "rb") as image_file:
                image_data ='data:image/jpg;base64,'+ base64.b64encode(image_file.read()).decode()
        else:
            message='image file not found'+imageFileName
        return image_data, message


    def evaluateCardValue(self, result):
        print('\nevaluating card value')

        if 'matchedCard' in result and result['matchedCard'] is not None:
            averageSellPrice_str = result['matchedCard']['cardmarket.prices.averageSellPrice']
            averageSellPrice=float(averageSellPrice_str)

            print('\nSale Price: {}'.format(averageSellPrice));

        card_value = 'low'
        if result['result'] == 'error':
            card_value = 'low'
            print(f"Error: {result['message']}")
        elif averageSellPrice >= settings['price_treshold_mid']:
            card_value = 'high'
        elif averageSellPrice >= settings['price_treshold_low']:
            card_value = 'mid'
        else:
            card_value = 'low'
        print ('card value: {}'.format(card_value))
        return card_value
        #return self.img_counter %3 ==1

    async def activateCardDealer(self):
        print('\n\n______________________________________________\nturn ON card dealer');
        if self.activateHardware:
            GPIO.output(self.channel_dealer, GPIO.LOW)
        await asyncio.sleep(int(settings['wait_for_card_dealer']))

        print('\nturn OFF card dealer');
        if self.activateHardware:
            GPIO.output(self.channel_dealer, GPIO.HIGH)
        await asyncio.sleep(int(settings['wait_between_actions']))

    async def activateBlowerHighValue(self):
        await self.moveDestinationBin('high')
        await self.activateServoDropCard()

    async def activateBlowerLowValue(self):
        await self.moveDestinationBin('low')
        await self.activateServoDropCard()

    async def activateBlowerMidValue(self):
        await self.moveDestinationBin('middle')
        await self.activateServoDropCard()

    async def moveDestinationBin(self, value=None, duty_cycle=None):
        print(f"Moving bin to position: {value}")
        if not self.activateHardware:
            return

        if value is not None:
            angle = settings['servo_B_pwm_angle_'+value]
            #self.servo_B_pwm_duty_cycle = self.angle_to_duty_cycle(angle, self.servo_B_pwm_frecuency_hz)
            self.servo_B_pwm_duty_cycle = angle
        elif duty_cycle is not None:
            self.servo_B_pwm_duty_cycle = duty_cycle
        else:
            print('no value provided for bin position')
            return
        #print(f"Servo B value: angle: {angle} duty cycle: {self.servo_B_pwm_duty_cycle}")
        print(f"Servo B value: duty cycle: {self.servo_B_pwm_duty_cycle}")
        if using_simulator:
            GPIO.output(self.channel_servo_B, GPIO.HIGH)
        else:
            if settings['servo_B_use_bus_serial']:
                self.servo_B_pwm_duty_cycle = self.servo_B_pwm_duty_cycle % 4096
                self.busServo.set_position(self.servo_B_pwm_duty_cycle)
                self.busServo.read_state()
            elif self.use_daemon:
                self.daemon.hardware_PWM(self.channel_servo_B, self.servo_B_pwm_frecuency_hz, int(self.servo_B_pwm_duty_cycle)*10000)#25*10000 == 25% dutycycle
            elif self.use_hardware_pwm:
                self.servo_B_pwm.start(self.servo_B_pwm_duty_cycle)
                self.servo_B_pwm.change_duty_cycle(self.servo_B_pwm_duty_cycle)
            else:
                self.servo_B_pwm.start(self.servo_B_pwm_duty_cycle)


        await asyncio.sleep(int(settings['wait_for_servo_bin']))

    async def activateServoDropCard(self):
        print(f"Dropping card")
        if not self.activateHardware:
            return

        await self.moveCardPlatform('dump')
        await self.moveCardPlatform('rest')
            
    async def moveCardPlatform(self, position, duty_cycle=None):
        print(f"moving platform to position {position}")
        if position == 'rest':
            servo_A_pwm_angle = settings['servo_A_pwm_angle_rest']
        elif position == 'dump':
            servo_A_pwm_angle = settings['servo_A_pwm_angle_dump']
        else:
            servo_A_pwm_angle = settings['servo_A_pwm_angle_rest']

        #self.servo_A_pwm_duty_cycle = self.angle_to_duty_cycle(servo_A_pwm_angle, self.servo_A_pwm_frecuency_hz)
        #print(f"Servo A value: angle: {servo_A_pwm_angle} duty cycle: {self.servo_A_pwm_duty_cycle}")
        if duty_cycle is None:
            self.servo_A_pwm_duty_cycle = servo_A_pwm_angle
        else:
            self.servo_A_pwm_duty_cycle = duty_cycle
        print(f"Servo A value: duty cycle: {self.servo_A_pwm_duty_cycle}")
        if using_simulator:
            GPIO.output(self.channel_servo_A, GPIO.HIGH)
        else:
            if self.use_daemon:
                self.daemon.hardware_PWM(self.channel_servo_A, self.servo_A_pwm_frecuency_hz, int(self.servo_A_pwm_duty_cycle)*10000)#25*10000 == 25% dutycycle
            elif self.use_hardware_pwm:
                self.servo_A_pwm.start(self.servo_A_pwm_duty_cycle)
                self.servo_A_pwm.change_duty_cycle(self.servo_A_pwm_duty_cycle)
                self.servo_A_pwm.stop()
            else:
                self.servo_A_pwm.start(self.servo_A_pwm_duty_cycle)

        await asyncio.sleep(int(settings['wait_for_card_dump']))

    def angle_to_duty_cycle(self, angle, frecuency_hz):
        duty_cycle = ((angle/180.0) + 1.0) * 5.0
        return duty_cycle

    def setupIO(self):
        print('\nsetup IO');

        self.channel_dealer = settings['pin_dealer']
        self.channel_dealer_B = settings['pin_dealer_B']

        self.channel_light_A = settings['pin_light_A']
        self.channel_light_B = settings['pin_light_B']

        self.channel_servo_A = settings['pin_servo_A']
        self.channel_servo_B = settings['pin_servo_B']

        self.led_channels = [
                self.channel_dealer,
                self.channel_dealer_B,
                self.channel_light_A,
                self.channel_light_B,
                #self.channel_servo_A, #interference with pigpio libray
                #self.channel_servo_B  #interference with pigpio libray
                ]

        self.pin_button = settings['pin_button']
        self.pin_button_b = settings['pin_button_b']
        self.pin_button_c = settings['pin_button_c']

        print(f'dealer    GPIO_{self.channel_dealer}  \tpin_{self.BCMtoBOARD(self.channel_dealer)}')
        print(f'dealer    GPIO_{self.channel_dealer_B}  \tpin_{self.BCMtoBOARD(self.channel_dealer_B)}')

        print(f'light A   GPIO_{self.channel_light_A} \tpin_{self.BCMtoBOARD(self.channel_light_A)}')
        print(f'light B   GPIO_{self.channel_light_B} \tpin_{self.BCMtoBOARD(self.channel_light_B)}')

        print(f'servo A   GPIO_{self.channel_servo_A} \tpin_{self.BCMtoBOARD(self.channel_servo_A)}')
        print(f'servo B   GPIO_{self.channel_servo_B} \tpin_{self.BCMtoBOARD(self.channel_servo_B)}')

        print(f'button    GPIO_{self.pin_button} \tpin_{self.BCMtoBOARD(self.pin_button)}')
        print(f'button B  GPIO_{self.pin_button_b} \tpin_{self.BCMtoBOARD(self.pin_button_b)}')
        print(f'button C  GPIO_{self.pin_button_c} \tpin_{self.BCMtoBOARD(self.pin_button_c)}')

        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.led_channels, GPIO.OUT)
        GPIO.setup([self.pin_button, self.pin_button_b, self.pin_button_c], GPIO.IN, pull_up_down=GPIO.PUD_UP)
        #GPIO.add_event_detect(self.pin_button, GPIO.RISING, callback=self.button_callback, bouncetime=200)

        GPIO.output(self.channel_dealer, GPIO.HIGH)
        GPIO.output(self.channel_dealer_B, GPIO.HIGH)

        self.servo_A_pwm_frecuency_hz = settings['servo_A_pwm_frecuency_hz']
        self.servo_B_pwm_frecuency_hz = settings['servo_B_pwm_frecuency_hz']
        servo_A_pwm_angle_wait = settings['servo_A_pwm_angle_rest']
        servo_B_pwm_angle_rest = settings['servo_B_pwm_angle_low']

        print(f"servo A PWM frecuency: {self.servo_A_pwm_frecuency_hz}")
        print(f"servo B PWM frecuency: {self.servo_B_pwm_frecuency_hz}")


        self.use_hardware_pwm = settings['use_hardware_pwm']
        self.use_daemon = settings['use_daemon']
        channel_servo_A_hdw = settings['channel_servo_A_hdw']
        channel_servo_B_hdw = settings['channel_servo_B_hdw']
        #channel_servo_A_hdw = settings['pin_servo_A']
        #channel_servo_B_hdw = settings['pin_servo_B']

        if using_simulator:
            pass
        else:
            if self.use_daemon:
                self.daemon = pigpio.pi()
                #self.daemon.write(22, 1)
            elif self.use_hardware_pwm:
                self.servo_A_pwm = HardwarePWM(channel_servo_A_hdw, hz= self.servo_A_pwm_frecuency_hz)
                if not settings['servo_B_use_bus_serial']:
                    self.servo_B_pwm = HardwarePWM(channel_servo_B_hdw, hz =self.servo_B_pwm_frecuency_hz)
            else:
                self.servo_A_pwm = GPIO.PWM(self.channel_servo_A, self.servo_A_pwm_frecuency_hz)
                if not settings['servo_B_use_bus_serial']:
                    self.servo_B_pwm = GPIO.PWM(self.channel_servo_B, self.servo_B_pwm_frecuency_hz)
                #self.servo_B_pwm.start(servo_B_pwm_angle_rest) # full duty cycle
                #self.servo_B_pwm.change_duty_cycle(servo_B_pwm_angle_rest)
                #self.servo_B_pwm.change_frequency(25_000)
                #self.servo_B_pwm.stop()

            if settings['servo_B_use_bus_serial']:
                servoSetup.execute_command_servo_driver('start_serial_forwarding')
                self.busServo = busServoWrapper()
                self.busServo.initialize()
                self.busServo.read_state()

    async def detectButtonPress(self, parameter):
        try:
            if not self.activateHardware:
                return
            while self.runningVideoFeed:
                #print('checking  buttons')
                ##event = keyboard.read_event()
                #if self.simulateKeyboardEvent():
                #    self.button_pressed_a = True
                #    self.button_callback('A')
                #else:
                #    self.button_pressed_a = False
                #if not GPIO.input(self.pin_button) or (event.event_type == keyboard.KEY_DOWN and event.name == 'x'):

                if not GPIO.input(self.pin_button):
                    self.button_pressed_a = True
                    await self.button_callback('A')
                else:
                    self.button_pressed_a = False

                if True:#move platform one bit at a time
                    if not GPIO.input(self.pin_button_b):
                        self.button_pressed_b = True
                        await self.button_callback('D')
                    else:
                        self.button_pressed_b = False
                else:
                    if not GPIO.input(self.pin_button_b):
                        self.button_pressed_b = True
                        await self.button_callback('B')
                    else:
                        self.button_pressed_b = False
                        await self.button_callback('B')


                if self.dealer_running and GPIO.input(self.pin_button_c) and not using_simulator:
                    self.button_pressed_c = True
                    if self.dealer_alarm_time:
                        if abs(time.time() - self.dealer_alarm_time) > 7:
                            await self.button_callback('C')
                    else:
                        self.dealer_alarm_time = time.time()
                else:
                    self.dealer_alarm_time = None
                    self.button_pressed_c = False


                await asyncio.sleep(0.500)#50ms
                #if self.analysing_image_event:
                #    self.analysing_image_event.wait()
        except (KeyboardInterrupt, Exception) as ex:
            print('\nInterrupted')
            traceback.print_exc()


    async def button_callback(self, button = 'A'):
        if button == 'A':
            print(f"hardware button pressed: {button}")
            await self.onStartPauseButton()
            #if settings['run_interactive']:
            #    keyboard.press_and_release('enter')
            #else:
            #    self.enter_button_event.set()
        elif button == 'B':
            if self.button_pressed_b:
                print(f"hardware button pressed: {button}")
                if not self.rotate_platform:
                    self.busServo.set_speed(500)
                    self.busServo.set_position(4096)
                    self.rotate_platform = True
            elif not self.button_pressed_b :
                if  self.rotate_platform:
                    print('hard button B released')
                    self.busServo.set_position(self.busServoLastPos)
                    self.busServo.set_speed(0)
                    self.rotate_platform = False
        elif button == 'D':
            print(f"hardware button pressed: {button}")
            self.exit_bin_position = (self.exit_bin_position + 1) % 3
            if self.exit_bin_position == 1:
                await self.moveDestinationBin('exit_low')
            elif self.exit_bin_position == 2:
                await self.moveDestinationBin('exit_middle')
            else:
                await self.moveDestinationBin('exit_high')
        elif button == 'C':
            print(f"hardware button pressed: {button}")
            if GPIO.input(self.pin_button_c):
                await self.powerOffDealer()


    async def powerOnDealer(self):
        await self.publishImageFeed(None, 'turning dealer on')
        self.dealer_running = False
        self.pauseClassifyLoop = True
        print('\nturn ON DEALER SSR');
        self.dealer_time_check = time.time()
        GPIO.output(self.channel_dealer_B, GPIO.LOW)
        i = 0
        while i<=7:
            await asyncio.sleep(1)#wait for first card to be set
            i=i+1
            if using_simulator or not GPIO.input(self.pin_button_c):
            #if not GPIO.input(self.pin_button_c):# or using_simulator:
                print(f"DEALER: running")
                self.dealer_running = True
                self.pauseClassifyLoop = False
                await self.publishImageFeed(None, 'Dealer: running')
                break
        if not self.dealer_running:
            print("DEaler stopped: no cards available")
            GPIO.output(self.channel_dealer_B, GPIO.HIGH)
            await self.publishImageFeed(None, 'Dealer stopped: no cards available')
        await self.publishImageFeed(None, 'turning dealer on')

    async def onStartPauseButton(self):
        if self.manualMode:
            await self.powerOnDealer()
        elif self.dealer_running:
            await self.powerOffDealer()
        else:
            await self.powerOnDealer()


    async def powerOffDealer(self):
        if self.dealer_running:
            print(f"DEALER: stoped")
            GPIO.output(self.channel_dealer_B, GPIO.HIGH)
            self.dealer_running = False
            self.pauseClassifyLoop = True
            await self.publishImageFeed(None, 'turning dealer off')


    async def test_digital_outputs3(self):
        # Set up GPIO mode
        GPIO.setmode(GPIO.BCM)

        self.channel_dealer = settings['pin_dealer']
        self.channel_low_blower = settings['pin_low_blower']
        self.channel_high_blower = settings['pin_high_blower']
        self.channel_mid_blower = settings['pin_mid_blower']
        self.led_channels = [self.channel_dealer, self.channel_low_blower, self.channel_high_blower, self.channel_mid_blower]

        GPIO.setup(self.led_channels, GPIO.OUT)

        pins = self.led_channels

        try:
            while True:
                # Turn on each pin one at a time
                for pin in pins:
                    GPIO.output(pin, GPIO.HIGH)
                    board_pin = self.BCMtoBOARD(pin)  # Convert BCM to board pin number
                    print(f"BCM Pin: GPIO {pin} | Board Pin: {board_pin} | Status: ON")
                    await asyncio.sleep(5)  # Delay for 1 second
                    GPIO.output(pin, GPIO.LOW)
                    print(f"BCM Pin: GPIO {pin} | Board Pin: {board_pin} | Status: OFF")
        finally:
            # Clean up GPIO settings
            GPIO.cleanup()

    async def calibrate_servo_a(self):
        try:
            self.activateHardware=True
            self.setupIO()
            await self.turn_light_on()
    
            while True:
                k=input('u/d/esc/duty cycle(0-100)\n')
                k=k.lower()
                print(f"key pressed: {k}")
                if k =='esc' or k=='exit':
                    break;
                else:
                    duty_cycle=float(k)%100
                    await self.moveCardPlatform(None, duty_cycle)
        except Exception as e:
            raise e
        finally:
            GPIO.cleanup()


    async def calibrate_servo_b(self):
        try:
            self.activateHardware=True
            self.setupIO()
    
            while True:
                k=input('u/d/esc/duty cycle(0-100)\n')
                k=k.lower()
                print(f"key pressed: {k}")
                if k =='esc' or k=='exit':
                    break;
                else:
                    duty_cycle=int(k)
                    await self.moveDestinationBin(None,duty_cycle)
        except Exception as e:
            raise e
        finally:
            GPIO.cleanup()

    async def test_hardware(self):
        try:
            self.activateHardware=True
            self.setupIO()

            while False:

                controller.flush_input()
                k=input('Press a key a b c d\n')
                k=k.lower()
                print(f"key pressed: {k}")
                if k =='a':
                    await self.activateCardDealer()
                elif k=='b':
                    print('\nturn ON DEALER SSR');
                    GPIO.output(self.channel_dealer_B, GPIO.LOW)
                elif k=='c':
                    print('\nturn OFF DEALER SSR');
                    GPIO.output(self.channel_dealer_B, GPIO.HIGH)






            while False:
                await self.activateCardDealer()
                await asyncio.sleep(2)
                await self.moveCardPlatform('dump')
                await asyncio.sleep(2)
                await self.moveCardPlatform('rest')
                await asyncio.sleep(2)
    
            #self.activateCardDealer()
            #await asyncio.sleep(3)

            #self.turn_light_on()
            #await asyncio.sleep(5)
            #self.turn_light_off()
            #await asyncio.sleep(2)

            #self.turn_light_on('B')
            #await asyncio.sleep(5)
            #self.turn_light_off('B')
            #await asyncio.sleep(2)

            #self.turn_light_on()
            #self.turn_light_on('B')

            #self.moveCardPlatform('dump')
            #await asyncio.sleep(5)
            #self.moveCardPlatform('rest')
            #await asyncio.sleep(5)
             
            await self.moveDestinationBin('high')
            time.sleep(5)
            await self.moveDestinationBin('middle')
            time.sleep(5)
            await self.moveDestinationBin('low')
            time.sleep(5)

            while False:
                k=input('u/d/esc\n')
                k=k.lower()
                print(f"key pressed: {k}")
                if k =='esc' or k=='exit':
                    break;
                else:
                    duty_cycle=float(k)%100
                    await self.moveDestinationBin('high',duty_cycle)
 
                #self.moveDestinationBin('high')
                #print('\r\r\r',end='')
                #self.moveDestinationBin('middle')
                #print('\r\r\r',end='')
                #self.moveDestinationBin('low')
                #print('\r\r\r',end='')
                #self.moveDestinationBin('rest')
                #print('\r\r\r',end='')
        except Exception as e:
            raise e
        finally:
            GPIO.cleanup()

    async def test_digital_outputs2(self):
        # Set up GPIO mode
        GPIO.setmode(GPIO.BCM)

        pins = [i for i in range(0,28)]#GPIO0 to GPIO27
        # Set up each pin as an output
        for pin in pins:
            GPIO.setup(pin, GPIO.OUT)

        try:
            while True:
                # Turn on each pin one at a time
                for pin in pins:
                    GPIO.output(pin, GPIO.HIGH)
                    board_pin = self.BCMtoBOARD(pin)  # Convert BCM to board pin number
                print(f"All IO pins | Status: ON")
                await asyncio.sleep(5)  # Delay for 5 second

                for pin in pins:
                    GPIO.output(pin, GPIO.LOW)
                print(f"All IO pins  | Status: OFF")
                await asyncio.sleep(5)  # Delay for 5 second
        finally:
            # Clean up GPIO settings
            GPIO.cleanup()

    async def test_digital_outputs(self):
        # Set up GPIO mode
        GPIO.setmode(GPIO.BCM)

        pins = [i for i in range(0,28)]#GPIO0 to GPIO27
        # Set up each pin as an output
        for pin in pins:
            GPIO.setup(pin, GPIO.OUT)

        try:
            while True:
                # Turn on each pin one at a time
                for pin in pins:
                    GPIO.output(pin, GPIO.HIGH)
                    board_pin = self.BCMtoBOARD(pin)  # Convert BCM to board pin number
                    print(f"BCM Pin: GPIO {pin} | Board Pin: {board_pin} | Status: ON")
                    await asyncio.sleep(1)  # Delay for 1 second
                    GPIO.output(pin, GPIO.LOW)
                    print(f"BCM Pin: GPIO {pin} | Board Pin: {board_pin} | Status: OFF")
        finally:
            # Clean up GPIO settings
            GPIO.cleanup()

    # Define the mapping from BCM to board pin numbers
    pin_mapping = {
        2: 3, 3: 5, 4: 7, 14: 8, 15: 10, 17: 11, 18: 12, 27: 13,
        22: 15, 23: 16, 24: 18, 10: 19, 9: 21, 25: 22, 11: 23, 8: 24, 7: 26,
        0: 27, 1: 28, 5: 29, 6: 31, 12: 32, 13: 33, 19: 35, 16: 36, 26: 37, 20: 38, 21: 40
    }

    async def test_light(self):
        self.activateHardware=True
        print('light pin: ' + str(settings['pin_light']))
        print('light pin2: ' + str(settings['pin_light2']))

        self.channel_light = settings['pin_light']
        self.channel_light2 = settings['pin_light2']

        self.led_channels = [self.channel_light, self.channel_light2]
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.led_channels, GPIO.OUT)
        self.light_pwm_frecuency = settings['light_pwm_frecuency_hz']
        self.light_duty_cycle = settings['light_pwm_duty_cycle']
        print(f"light PWM frecuency: {self.light_pwm_frecuency}")
        print(f"light PWM duty cycle: {self.light_duty_cycle}")

        pin = self.channel_light
        pin2 = self.channel_light2
        board_pin = self.BCMtoBOARD(pin)  # Convert BCM to board pin number
        board_pin2 = self.BCMtoBOARD(pin2)  # Convert BCM to board pin number

        if using_simulator:
            pass
        else:
            self.light_pwm = GPIO.PWM(self.channel_light, self.light_pwm_frecuency)
            self.light_pwm2 = GPIO.PWM(self.channel_light2, self.light_pwm_frecuency)

        try:
            while True:

                print(f"BCM Pin: GPIO {pin} | Board Pin: {board_pin} | Status: PWM ON")
                self.turn_light_on()
                await asyncio.sleep(5)  # Delay for 1 second
                self.turn_light_off()
                print(f"BCM Pin: GPIO {pin} | Board Pin: {board_pin} | Status: PWM OFF")

                print(f"BCM Pin: GPIO {pin2} | Board Pin: {board_pin2} | Status: PWM ON")
                self.turn_light_on('B')
                await asyncio.sleep(5)  # Delay for 1 second
                self.turn_light_off('B')
                print(f"BCM Pin: GPIO {pin2} | Board Pin: {board_pin2} | Status: PWM OFF")


                print()
                print('Press any key to continue')
                print('Press ESC to exit')
                print('Press Up arrow key to increase the light')
                print('Press Down arrow key to decrease the light')
 
                #k = keyboard.read_key()
                k=input('write up/down/esc and press enter\n')
                k=k.lower()
                print(f"key pressed: {k}")
                if k =='esc' or k=='exit':
                    break
                elif k=='up':
                    print ("increasing light dimmer")
                    duty_cycle = self.light_duty_cycle + 10
                    self.light_duty_cycle = duty_cycle if duty_cycle <= 100 else 100
                    print(f"light duty cycle: {self.light_duty_cycle} %")
                    continue
                elif k=='down':
                    print ("decreasing light dimmer")
                    duty_cycle = self.light_duty_cycle - 10
                    self.light_duty_cycle = duty_cycle if duty_cycle >= 0 else 0
                    print(f"light duty cycle: {self.light_duty_cycle} %")
                    continue
        finally:
            # Clean up GPIO settings
            GPIO.cleanup()

    
    def BCMtoBOARD(self, bcm_pin):
        return self.pin_mapping.get(bcm_pin, None)

    def pick_rectangle_by_height(self, image, target_height_percentage, target_width_percentage):
        height, width, _ = image.shape
        target_height = height * target_height_percentage
        target_width = width * target_width_percentage
    
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 50, 150)
        contours, _ = cv2.findContours(edges.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
        selected_rectangle = None
        min_height_diff = float('inf')
        min_width_diff = float('inf')
    
        rectangles = []
        for contour in contours:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(approx)

                height_diff = abs(h - target_height)
                if target_height_percentage > 0:
                    if height_diff < min_height_diff:
                        min_height_diff = height_diff
                        selected_rectangle = (x, y, w, h)
                else:
                    width_diff = abs(w - target_width)
                    if width_diff < min_width_diff:
                        min_width_diff = width_diff
                        selected_rectangle = (x, y, w, h)
                rectangles.append((x, y, w, h))
        return selected_rectangle, rectangles

    
    def split_npz_file():
        matchWrapper.split_database()

    def flush_input():
        if settings['run_interactive']:
            if is_windows:
                while msvcrt.kbhit():
                    msvcrt.getch()
            else:
                termios.tcflush(sys.stdin, termios.TCIOFLUSH)


if __name__ == "__main__":
    #controller().startVideoFeed(True, True)
    controller().testVideoFeed()
