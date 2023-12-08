from os import path
from os import listdir, remove
import re
import string
from subprocess import PIPE, Popen
import multiprocessing
import threading
import sys
import importlib.machinery
import cv2
import base64
import requests
import json
import asyncio
import aiohttp
import time
import boto3
import io
import numpy as np
from DatabaseImageMatching.Database import Database
from DatabaseImageMatching.Input import Input
from DatabaseImageMatching.Matcher import Matcher
import pandas as pd
from demoUI.settings import settings 
from demoUI.settings import app
from queue import Empty
from pprint  import pprint
from demoUI.card_data import card_data


class matchWrapper:
    def generateDatabase():
        initial_scale=settings['initial_scale']
        app.logger.info('starting database generation')
        Database.generate_database_descriptor_files(settings['reference_image_path'], path.join(settings['database_base_path'],settings['image_descriptor_file_npz']), path.join(settings['database_base_path'],settings['length_descriptor_file_npy']) , path.join(settings['database_base_path'],settings['database_dict_file']), initial_scale)
        app.logger.info('finished database generation')

    def matchImageScript( image_full_path:string):
        shell_command=['python', settings['match_script_path'], image_full_path]

        resultScript=''
        try:
            session = Popen(shell_command, stdout=PIPE, stderr=PIPE)
            stdout, stderr = session.communicate()
            resultScript+="STDOUT:"+stdout.decode('utf-8')
            if stderr:
                resultScript+="STDERR:"+stderr.decode('utf-8')
        except Exception as ex:
            resultScript+=str(ex)

        p=re.compile('.*(ScriptResults\:)(.*)',re.DOTALL)
        match=p.match(resultScript)
        if match is not None:
            imageName=match[2]
            return imageName
        return None
 
    def matchImage(input_image_file:string, use_camera_b=False, subset=None):
        # Paths to Database Variables
        DESCRIPTOR_NPZ_FILE=path.join(settings['database_base_path'],settings['image_descriptor_file_npz'])

        # Construct database from pre-stored files
        #print ("Constructing database...")
        database = Database(DESCRIPTOR_NPZ_FILE, False, [0, -1], subset)
        #print ("Database constructed.")

        # Generate query input from image file
        input_file = input_image_file#image got from camera feed

        # Crop input image to card - (crop_height, crop_width, start_width, start_height)
        square=settings['square_limits']
        if use_camera_b:
            square=settings['square_limits_b']

        #remove part of the image that are not part of the card
        initial_crop = (square[3], square[2], square[0], square[1])

        # Scale cropped input image to reduce run-time
        initial_scale=settings['initial_scale']
        query = Input(input_file, initial_crop, initial_scale)
        # Feed all of card into image matcher# change here to make it work with a smaller part of the card
        query.create_image_crop('FullCard',0.0,1.0,1.0)
        query.set_active_image('FullCard')
        query.image_range = [0, -1]

        # Match query image to database
        matcher = Matcher('bf')
        match = matcher.match_input_to_database(query, database)
        #match_attributes = matcher.get_match_attributes(match, database)
        #print(f'Match = {match}, Attributes = {match_attributes}')
        print(f'Match = {match}')
        card_name = match[0]
        confidence = match[1]
        message = None

        confidence_threshold = settings['confidence_threshold']
        if confidence_threshold > 0 and match[1] is not None and match[1] > confidence_threshold:
            message = "Found match is below confidence threshold: ignoring card"

        return card_name, confidence, message

    @staticmethod
    def processQueueMatchImage(queue_in, queue_out, stop_workers):
        matcher = matchWrapper()
        matcher.load_database()
        while not stop_workers.is_set():
            try:
                message = queue_in.get(timeout=5)# Wait for a message from the main process
            except Empty:
                continue
            if message['message'] == "exit":
                break
            elif message['message'] == "call_function":
                #print("Function called in process:", multiprocessing.current_process().name)
                match = matcher.matchImageRange(message['input_file'], message['initial_crop'], message['initial_scale'], message['image_range'])
                queue_out.put({
                    'match': match,
                    'input_file': message['input_file'],
                    'image_range': message['image_range']
                })  # Send the result to the main process
            # Add more message handling as needed

    def load_database(self):
        # Paths to Database Variables
        DESCRIPTOR_NPZ_FILE=path.join(settings['database_base_path'],settings['image_descriptor_file_npz'])

        only_high_price = settings['only_high_price']
        subset = None
        if only_high_price:
            subset = card_data.get_cards_sorted_by_price(price=settings['high_price_threshold'])

        self.database = Database(DESCRIPTOR_NPZ_FILE, use_s3=False, image_range=None, subset=subset)

    def matchImageRange(self, input_file, initial_crop, initial_scale, image_range):
        # Generate query input from image file

        query = Input(input_file, initial_crop, initial_scale)

        query.create_image_crop('FullCard',0.0,1.0,1.0) # Feed all of card into image matcher
        query.set_active_image('FullCard')
        query.image_range = image_range

        matcher = Matcher('bf')
        match = matcher.match_input_to_database(query, self.database)
        #match_attributes = matcher.get_match_attributes(match, database)

        print(f'Match = {match}')
        card_name = match[0]
        confidence = match[1]
        message = None

        confidence_threshold = settings['confidence_threshold']
        if confidence_threshold > 0 and match[1] is not None and match[1] > confidence_threshold:
            message = "Found match is below confidence threshold: ignoring card"

        return card_name, confidence, message

    def initialize_workers(self, processes_number, cards_number):
        self.processes_number = processes_number
        self.cards_per_process =int(cards_number / processes_number)
        print(f'cards_per_process = {self.cards_per_process}')

        print(f'available cpu {multiprocessing.cpu_count()}')
        self.stop_workers = multiprocessing.Event()

        self.requests = {}
        self.queue_in = multiprocessing.Queue()
        self.queue_out = multiprocessing.Queue()

        processes = []
        for _ in range(self.processes_number):
            process = multiprocessing.Process(target=matchWrapper.processQueueMatchImage, args=(self.queue_in, self.queue_out, self.stop_workers))
            processes.append(process)
            process.start()

        self.processes = processes

        self.monitor_workers_thread  = threading.Thread(target=self.monitor_workers, args=(self.queue_out,))
        self.monitor_workers_thread.start()


    def monitor_workers(self, queue_out):
        while not self.stop_workers.is_set():
            try:
                message = queue_out.get(timeout=5)  # Wait for a message from the worker
            except Empty:
                continue
            if message['input_file']:
                request = self.requests[message["input_file"]]
                request['matches'][message['image_range'][0]]=message['match']
                event = request['events'][message['image_range'][0]]
                event.set()

    async def callMatchImageRemoteAsync(payload, image_range):
        init_time = time.time()
        async with aiohttp.ClientSession() as session:
            url = settings['lambda_url']
            payload['data']['image_range'] = image_range

            #print(payload)

            # Rest of your payload and request code ...
            payload_json = json.dumps(payload)

            async with session.post(url, json=payload_json) as response:
                print("partial match")
                json_response = await response.json()
                print(json_response)
                print("elapsed time: ", time.time() - init_time)
                return json_response

    async def matchImageRemoteAsync(input_image_file:string, use_camera_b=False):
        square=settings['square_limits']
        if use_camera_b:
            square=settings['square_limits_b']
        initial_crop = (square[3], square[2], square[0], square[1])
        initial_scale=settings['initial_scale']

        image = cv2.imread(input_image_file)
        result, buffer = cv2.imencode(".png", image)
        base64_string = base64.b64encode(buffer).decode("utf-8")
        #base64_string = "empty"

        split= settings['split_database']
        payload = {
                "data": {
                    "image_path":       input_image_file,
                    "image_b64":        base64_string,
                    "initial_crop":     initial_crop,
                    "initial_scale":    initial_scale,
                    "image_range":[0,100],
                    "split":            split
                    }
                }
        #payload=""

        img = cv2.imread(input_image_file)

        img_crop = Input.crop_and_scale(img, initial_crop, initial_scale)

        cv2.imwrite(input_image_file+'crop.jpg',img_crop)



        # List of image ranges for 5 calls (example values)
        lower_bound = 0
        image_ranges=[]
        if split:
            processes_number = settings['process_number']
        else:
            processes_number = 1

        cards_number = settings['cards_number']
        cards_per_process =int(cards_number / processes_number)

        for i in range(processes_number):
            image_range= [lower_bound, lower_bound + cards_per_process]
            lower_bound += cards_per_process
            image_ranges.append(image_range)

        print("Image ranges: ", image_ranges)
        tasks = []
        for image_range in image_ranges:
            task = matchWrapper.callMatchImageRemoteAsync(payload, image_range)
            tasks.append(task)

        results = await asyncio.gather(*tasks)
        #print("Partial matches: ", results)

        max_distance = float('inf')
        max_match = None
        for result in results:
            if 'match' in result:
                match = result['match']
                if match[1] !=None and match[1] < max_distance:
                    max_distance = match[1]
                    max_match = match
            else:
                print("Error: ", result)

        print("Best match: ", max_match)

        #max_match.append("match not found")
        if max_match is None:
            return None
        else:
            return max_match[0], max_match[1], max_match[2] if len(max_match) > 2 else None

    async def matchImageRemote(input_image_file:string, use_camera_b=False, event_loop=None):
        if event_loop is None:
            event_loop = asyncio.get_event_loop()
        #result = event_loop.run_until_complete(matchWrapper.matchImageRemoteAsync(input_image_file, use_camera_b))
        result = await matchWrapper.matchImageRemoteAsync(input_image_file, use_camera_b)
        if result is None:
            return None, 0, "Error no match"
        else:
            card, confidence, message = result
            return card, confidence, message

    def matchImageQueue(self, input_image_file:string, use_camera_b=False):
        square=settings['square_limits']
        if use_camera_b:
            square=settings['square_limits_b']
        initial_crop = (square[3], square[2], square[0], square[1])
        initial_scale=settings['initial_scale']

        events = {}
        matches = {}
        request = {
                "events": events,
                "matches": matches
                }
        self.requests[input_image_file] = request

        # Send a message to each process to call the function
        lower_bound = 0
        for _ in range(self.processes_number):
            event = threading.Event()
            events[lower_bound]=event
            image_range= [lower_bound, lower_bound + self.cards_per_process]
            lower_bound += self.cards_per_process
            self.queue_in.put({
                "message": "call_function",
                "input_file":input_image_file,
                "initial_crop":initial_crop,
                "initial_scale":initial_scale,
                "image_range":image_range
                    })

        for event in events.values():
            event.wait()  # Wait for the event to be set by the worker

        max_distance = float('inf')
        max_match = None
        print(matches)
        for match in matches.values():
            if match[1] !=None and match[1] < max_distance:
                max_distance = match[1]
                max_match = match

        print("Best match: ", max_match)
        return max_match

    def terminate_workers(self):
        #print("Terminating workers")
        self.stop_workers.set()

        ## Send an "exit" message to each process to terminate them
        #for _ in range(self.processes_number):
        #    self.queue_in.put({
        #        "message":"exit"
        #        })

        for process in self.processes:
            process.join(timeout=10)
            if process.is_alive():
                process.terminate()

        #print("All processes have finished.")
        self.processes = []
        #print("waiting for monitor thread to finish")
        self.monitor_workers_thread.join(timeout=5)
        if self.monitor_workers_thread.is_alive():
            print("monitor thread is still alive")
            #self.monitor_workers_thread.terminate()

    def split_database():
        print("splitting database")
        descriptor_npz_file=path.join(settings['database_base_path'],settings['image_descriptor_file_npz'])
        descriptors_file=descriptor_npz_file

        use_s3 = False
        if use_s3:
            if True:
                # set the aws credentials
                aws_access_key_id = 'akiaqwfwtppzj7wavqxy'
                aws_secret_access_key = 'pyz+ubr4jf1iijsm0covwcb7p0zw0dd6s7sbqgp9'
                
                # set the aws credentials for boto3
                session = boto3.session(
                        aws_access_key_id=aws_access_key_id,
                        aws_secret_access_key=aws_secret_access_key
                        )
                s3_client = session.client('s3')
            else:    
                s3_client = boto3.client('s3')

        if use_s3:
            bucket=descriptors_file.split('/')
            response = s3_client.get_object(bucket=bucket[0], key=bucket[1])
            s3_object_data = response['body'].read()
            in_memory_buffer = io.bytesio(s3_object_data)

            descriptors = np.load(in_memory_buffer)
        else:
            descriptors = np.load(descriptors_file)
            #delete all files in the folder of descriptors_file with SIFT_ and end in .npz
            for file in listdir(path.dirname(descriptors_file)):
                if file.startswith("SIFT_") and file.endswith(".npz"):
                    remove(path.join(path.dirname(descriptors_file), file))

        size_f = len(descriptors)
        num_parts =20
        part_size = int(size_f/num_parts)
        print(descriptors)
        print(type(descriptors))
        print(len(descriptors))

        npz_file_path = descriptors_file
        
        # load the .npz file
        data = np.load(npz_file_path)
        
        # get the list of array names in the .npz file (in the same order as stored)
        array_names = list(data.files)
        
        # calculate the number of keys in each part and the remaining keys
        total_keys = len(array_names)
        print(f"total keys: {total_keys}")
        part_size = total_keys // num_parts
        remaining_keys = total_keys % num_parts
        
        # split the keys into parts
        parts = []
        remaining_part = {}
        start_idx = 0
        for i in range(num_parts):
        	keys_in_part = part_size + (1 if i < remaining_keys else 0)
        	end_idx = start_idx + keys_in_part
        	part_keys = array_names[start_idx:end_idx]
        	part = {name: data[name] for name in part_keys}
        	parts.append(part)
        
        	# save the part to a separate .npz file with the order information in the filename
        	part_filename = f"SIFT_{start_idx}_{end_idx - 1}.npz"
        	np.savez(path.join(settings['database_base_path'], part_filename), **part)
        
        	start_idx = end_idx
        
        # store the remaining keys in a separate dictionary
        if start_idx < total_keys-1:
            remaining_keys = array_names[start_idx:]
            for name in remaining_keys:
            	remaining_part[name] = data[name]
        
        # save the remaining keys to a separate .npz file
        remaining_filename = f"part_{start_idx}_{total_keys - 1}.npz"
        np.savez(remaining_filename, **remaining_part)

        parts.append(remaining_part)
        # print the parts
        for i, part in enumerate(parts, 1):
            print(f"part {i}:")
            print(f"total keys: {len(part)}")

        
        #return parts, remaining_part
        return





