import os, sys, cv2, json
from datetime import datetime
from PIL import Image
from random import randint, random
import io
import re
import base64
import time
import traceback
import os, cv2, json
import numpy as np
import json
import traceback
from DatabaseImageMatching.Database import Database
from DatabaseImageMatching.Input import Input
from DatabaseImageMatching.Matcher import Matcher

def lambda_handler(event, context):
    try:
        printEvent=False
        print('this is the last version, reading files from s3')
        if printEvent:
            print("Received event: " + json.dumps(event, indent=2))
        else:
            print("Received new event")
	
        original_event = event

        if 'isBase64Encoded' in event and event['isBase64Encoded']:
            print("\n")
            print('it is base64 encoded')
            if printEvent:
                print(event['body'])
            decoded_bytes = base64.b64decode(event['body'])
            decoded_string = decoded_bytes.decode('utf-8')
            if printEvent:
                print(decoded_string)
            event = json.loads(decoded_bytes)
            if printEvent:
                print(event)
        elif 'body' in event:
            print("\n")
            print('it is not base64 encoded but it has a body')
            event = json.loads(event['body'])
            #check if is string
            if isinstance(event, str):
                event = json.loads(event)
            if printEvent:
                print(event)
            print(type(event))
            if printEvent:
                print(event['data'])
        else:
            print("\n")
            print("it is not base64 encoded and it does not have a body")
            event = json.loads(event)
            if isinstance(event, str):
                event = json.loads(event)
            if printEvent:
                print(event)
            print(type(event))
            if printEvent:
                print(event['data'])

            if False:
                return {
                    'statusCode': 500,
                    'body': "it is not base64 encoded and it does not have a body"
                    }
        
        print('running test identify image')

        image_path = event['data']['image_path']
        image_b64 = event['data']['image_b64']
        initial_crop = event['data']['initial_crop']
        initial_scale = event['data']['initial_scale']
        image_range = event['data']['image_range']
        split = event['data']['split']
        print(image_range)
        
        print('sample image: ',image_path)

        matcher = WrapperMatcher()
        if split:
            matcher.load_database(image_range)
        else:
            matcher.load_database()
        
        results = matcher.matchImageRange(None, initial_crop, initial_scale, image_range, image_b64)
        print('this is the result:')
        print(results)
        return {
                'statusCode': 200,
                'body': {
                    'match': results
                    }
                }

        #raise an errror including the current path
        #raise Exception(f'error in path: {os.getcwd()}')

    except Exception as e:
        error_message = str(e)
        print(f"Error occurred: {error_message}")

        # Get the stack trace as a string
        stack_trace = traceback.format_exc()
        print(stack_trace)

        # Return an error response with the error message and stack trace
        return {
            'statusCode': 500,  # Use an appropriate status code for server errors
            'body': json.dumps({'error': error_message, 'stack_trace': stack_trace})
        }


class WrapperMatcher:
    def __init__(self):
        if hasattr(sys, '_MEIPASS'):
           # Running as a standalone executable, get the executable's directory path
           print('Running as a standalone executable')
           SITE_ROOT = os.path.abspath(os.path.dirname(sys.executable))
        else:
            SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
        json_url = os.path.join(SITE_ROOT,  "settings.json")
        settingsFile=open(json_url,'r')
        self.settings=json.load(settingsFile) 


    def load_database(self, image_range=None):
        # Paths to Database Variables
        settings = self.settings
        DESCRIPTOR_NPZ_FILE=os.path.join(settings['database_base_path'],settings['image_descriptor_file_npz'])
    
        use_s3=settings['use_s3']
        self.database = Database(DESCRIPTOR_NPZ_FILE, use_s3, image_range)
    
    def matchImageRange(self, image_path, initial_crop, initial_scale, image_range, image_b64):
        query = Input(image_path, initial_crop, initial_scale, image_b64)

        query.create_image_crop('FullCard',0.0,1.0,1.0) # Feed all of card into image matcher
        query.set_active_image('FullCard')
        query.image_range = image_range

        # Match query image to database
        matcher = Matcher('bf')
        match = matcher.match_input_to_database(query, self.database)

        print(f'Match = {match}')
        return match

