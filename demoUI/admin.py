import os, sys, cv2, json
from . import settings
from datetime import datetime
from PIL import Image
import pandas as pd
from demoUI.matchWrapper import matchWrapper
from demoUI.controller import controller
from demoUI.card_data import card_data
from random import randint, random
from demoUI.webapp import app # import the app from the webapp folder
from demoUI.settings import settings
from flask import Flask, request
from flask import render_template
import io
import re
import base64
from subprocess import PIPE, Popen
import time
import threading
import traceback
import os
from flask import Flask
import asyncio

class admin:
    @staticmethod
    def buid_card_regognition_database():
        print('\nBuilding card recognition database...')
        matchWrapper.generateDatabase()
        return{'result':'ok'}

    @staticmethod
    def start_flask_server():
        ## Set the environment variables
        os.environ['FLASK_APP'] = 'webapp'
        os.environ['FLASK_ENV'] = 'development'

        app.run(host="0.0.0.0")

    @staticmethod
    def identify_image():
        print('running test identify image')
        image_path="/home/ed/GitHub/pokemonCardFiles/referenceImages/base2/base2-31.png"
        image_path="/home/ed/GitHub/pokemonCardFiles/referenceImages/pop2/pop2-9.png"
        #image_path="/home/ed/GitHub/pokemonCardFiles/referenceImages/pokemon_card_backside.png"
        image_path="C:\\Users\\cocoa\\Documents\\GitHub\\pokemonCardFiles\\referenceImages\\base2\\base2-31.png"
        image_path="C:\\Users\\cocoa\\Documents\\GitHub\\pokemonCardFiles\\referenceImagesLarge\\base2\\base2-31.png"
        image_path="C:\\Users\\cocoa\\Documents\\GitHub\\pokemonCardFiles\\referenceImages\\swsh8\\swsh8-191.png"
        #image_path="C:\\Users\\cocoa\\Documents\\GitHub\\pokemonCardFiles\\referenceImagesLarge\\base1\\base1-15.png"
        #image_path="C:\\Users\\cocoa\\Documents\\GitHub\\pokemonCardFiles\\referenceImagesDelete\\base2-31-distoted.jpg"
        #image_path="C:\\Users\\cocoa\\Documents\\GitHub\\pokemonCardFiles\\referenceImagesDelete\\base2-31-distoted2.jpg"
        #image_path="C:\\Users\\cocoa\\Documents\\GitHub\\pokemonCardFiles\\referenceImagesLarge\\base2\\base2-25.png"
        #image_path="C:\\Users\\cocoa\\Documents\\GitHub\\pokemonCardFiles\\referenceImagesLarge\\xy0\\xy0-9.png"
        #image_path="C:\\Users\\cocoa\\Documents\\GitHub\\pokemonCardFiles\\referenceImages\\pokemon_card_backside.png"
        image_path="/home/goodwill/pokemonCard/pokemonCardFiles/referenceImagesLarge/base2/base2-31.png"
        #image_path="C:\\Users\\cocoa\\Documents\\GitHub\\pokemonCardFiles\\referenceImagesDelete\\yugioh-1.png"
        #image_path ="C:\\Users\\cocoa\\Documents\\GitHub\\pokemonCardFiles\\referenceImages\\bw2\\bw2-9.png"
        #image_path ="C:\\Users\\cocoa\\Documents\\GitHub\\pokemonCardFiles\\referenceImages\\xyp\\xyp-XY73.png"
        #image_path="/home/goodwill/pokemonCard/pokemonCardFiles/referenceImages/pokemon_card_backside.png"

        image_path=settings['image_path_sample']

        print('sample image: ',image_path)

        imageFile=Image.open(image_path)
        with controller() as cont:
            results = cont.identifyImage(imageFile)
            #results = cont.identifyImage(imageFile)
            #results = cont.identifyImage(imageFile)
            #results = cont.identifyImage(imageFile)
            #results = cont.identifyImage(imageFile)
            #results = cont.identifyImage(imageFile)
            #results = cont.identifyImage(imageFile)

        #if results['result'] == 'backside':
        #    return

        if results['matchedCardImage'] != None:
            results['matchedCardImage']=results['matchedCardImage'][0:20]
        if results['artworkImage'] != None:
            results['artworkImage']=results['artworkImage'][0:20]
        print(results)

async def runAdmin():
    choice = -1
    if len(sys.argv) > 1:
        print('Running admin command: ',sys.argv[1])
        choice = sys.argv[1]
    print('parameters')
    print(sys.argv)
    run_interactive = True
    if len(sys.argv) > 2:
        print('Running mode: ',sys.argv[2])
        if sys.argv[2] == 'n':
            run_interactive = False
    settings["run_interactive"]=run_interactive
    settings["show_image_feed"]=run_interactive
    print('run_interactive')
    print(settings["run_interactive"])
    print(settings["show_image_feed"])
    print('0 - Run automatic sorter')
    print('1 - Update Card Database')
    print('2 - Download Card Images')

    print('3 - Update Card Database (debug)')
    print('4 - Download Card Images (debug)')
    print('5 - Test Identify Image')
    print('6 - Print Card Database brief')
    #print('7 - Activate all pins in sequence')
    #print('8 - Activate all pins at once')
    #print('9 - Activate settings file pins in sequence')
    print('10 - Run Manual Sorter (press button to activate)')
    #print('11 - Test light')
    print('12 - show cameras')
    print('13 - split npz file')
    print('14 - start web server')
    print('15 - Test hardware')
    print('16 - Calibrate Servo A')
    print('17 - Calibrate Servo B')
    print('18 - Download Missing Cards')


    print('101 - Clear Card Database')

    if choice == -1:
        if settings["run_interactive"]:
            choice=input('Enter choice: ')
        else:
            choice='0'

    print(f"choice {choice}")
    if choice=='0':
        with controller() as cont:
            await cont.startVideoFeed(settings["show_image_feed"], True)
    elif choice=='1':
        card_data.build_database(debug=False, full_size_images=False, retrieve_images=False, update_database=True)
        #card_data.get_all_cards_for_each_set(debug=False, sets=['swsh8'])
    elif choice=='2':
        card_data.build_database(debug=False, full_size_images=False, retrieve_images=True, update_database=False)
        admin.buid_card_regognition_database()
    elif choice=='3':
        card_data.build_database(debug=True, full_size_images=False, retrieve_images=False, update_database=True)
    elif choice=='4':
        card_data.build_database(debug=True, full_size_images=True, retrieve_images=True, update_database=False)
        admin.buid_card_regognition_database()
    elif choice=='5':
        await admin.identify_image()
    elif choice=='6':
        card_data.print_database_brief()
    #elif choice=='7':
    #    controller().test_digital_outputs()
    #elif choice=='8':
    #    controller().test_digital_outputs2()
    #elif choice=='9':
    #    controller().test_digital_outputs3()
    elif choice=='10':
        with controller() as cont:
            await cont.startVideoFeed(True, True, manualMode=True)
    #elif choice =='11':
    #    controller().test_light()
    elif choice == '12':
        await controller().startVideoFeed(True, True, onlyVideo=True)
    elif choice == '13':
        controller.split_npz_file()
    elif choice == '14':
        admin.start_flask_server()
    elif choice == '15':
        await controller().test_hardware()
    elif choice == '16':
        await controller().calibrate_servo_a()
    elif choice == '17':
        await controller().calibrate_servo_b()
    elif choice=='18':
        card_data.build_database(debug=False, full_size_images=False, retrieve_images=False, update_database=False, add_missing_cards=True)
    elif choice=='101':
        card_data.clean_database()

if __name__ == "__main__":
    asyncio.run(runAdmin())
#    start_flask_server()
