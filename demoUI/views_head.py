from random import randint, random
from demoUI.matchWrapper import matchWrapper
import  os
from . import app
from . import settings 
from flask import Flask, request
from flask import render_template
from datetime import datetime
import io
import re
import base64
from PIL import Image
import pandas as pd
from subprocess import PIPE, Popen

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/")
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
        imagePath="{saved_image_path}{date}.{format}".format(saved_image_path=settings['saved_image_path'], date=str(datetime.now().strftime("%Y%m%d%H%M%S")), format=settings['saved_image_format'])

        imageFile.save(imagePath,settings['saved_image_format'])

        database_csv_path=os.path.join(settings['database_base_path'],settings['database_cvs_file'])

        dfPokemon=pd.read_csv(database_csv_path)
        resultScript=''

        #imageName=matchWrapper.matchImageScript(imagePath) 
        #imagePath='C:/Users/cocoa/Documents/GitHub/pokemonCardScript/savedImages/{0}.jpg'.format( randint(1,3))
        imageName=matchWrapper.matchImage(imagePath) 

        cardValues={}
        image_data=''
        message=''
    
        if imageName is not None:
            matchedRow=dfPokemon[dfPokemon['imgname']==imageName]
            if len(matchedRow)>0:
                cardValues=matchedRow.iloc[0].to_dict()
                image_data, message = readImageFileAsBase64(settings['reference_image_path'],imageName)
                artwork_data, message =  readImageFileAsBase64(settings['artwork_image_path'],cardValues['database'])
            else:
                result='error'
                message='no match found'
        else:
            result='error'
            message='error running matching script'
 
        return {'result':result,'message':message,'script':resultScript,'matched':imageName ,'matchedCard':cardValues, 'matchedCardImage':image_data,'artworkImage':artwork_data}

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
 