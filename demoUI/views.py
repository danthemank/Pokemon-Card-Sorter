from random import randint, random
from demoUI.matchWrapper import matchWrapper
import  os
from demoUI.settings import app
from demoUI.settings import settings 
from demoUI.controller import controller
from flask import Flask, request
from flask import render_template
from datetime import datetime
import io
import re
import base64
from PIL import Image
import pandas as pd
from subprocess import PIPE, Popen
#import pokemonCardDocker.lambda_function as docker
from pokemonCardDocker import lambda_function as docker
import json



@app.route("/lambda", methods = ['GET', 'POST'])
def lambda_handler():
    result = docker.lambda_handler(json.dumps(request.json), None)
    return result['body']

@app.route("/about")
def about():
    return render_template("about.html")

#@app.route("/")
@app.route("/capture")
@app.route("/capture/<mode>")
def capture(mode = None):
    settings['debug']=True if mode=='debug' else False
    mode='debug' if settings['debug'] else ''
    return render_template(
        "capture.html",
        mode=mode,
        square_limits=settings['square_limits'],
	    flipHorizontally=settings['flipHorizontally'],
        flipVertically=settings['flipVertically'],
        date=datetime.now()
    )

@app.route("/")
@app.route("/monitor")
@app.route("/monitor/<mode>")
def monitor(mode = None):
    settings['debug']=True if mode=='debug' else False
    mode='debug' if settings['debug'] else ''
    return render_template(
        "monitor.html",
        mode=mode,
        square_limits=settings['square_limits'],
	    flipHorizontally=settings['flipHorizontally'],
        flipVertically=settings['flipVertically'],
        date=datetime.now()
    )


@app.route("/data")
def get_data():
    return app.send_static_file("data.json")

@app.route("/identifyImage", methods = ['POST'])
def identifyImage():
    result='ok' 
    parametros=request.json
    match=None
    if 'image' in parametros:
        image_data=parametros['image']
        p=re.compile('(data:image/)(.*)(base64,)(.*)')
        match=p.match(image_data)
    if match is None:
        return {'result':'error','message':'image not available'}
    else:
        format=match[2]#'image/webp;'
        image_content=match[4]

        imageBytes=base64.b64decode(image_content)
        imageFile=Image.open(io.BytesIO(imageBytes))


        results = controller().identifyImage(imageFile)
 
        return results

def readImageFileAsBase64(imageFolder, imageFileName, ):
    imageFilePath=os.path.join(imageFolder, imageFileName)
    image_data=''
    message=''
    if os.path.exists(imageFilePath):
        with open(imageFilePath, "rb") as image_file:
            image_data ='data:image/jpg;base64,'+ base64.b64encode(image_file.read()).decode()
    else:
        message='image file not found'+imageFileName
    return image_data, message

@app.route("/analyse", methods = ['POST'])
def analyseDatabase():
    matchWrapper.generateDatabase()
    return{'result':'ok'}
 
