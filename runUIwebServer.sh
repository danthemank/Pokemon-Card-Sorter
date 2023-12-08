#!/bin/bash
export FLASK_APP=webapp
export FLASK_ENV=development

#export mypath=%~dp0
#export currentDirectory = %mypath:~0,-1%
#echo %currentDirectory%
#cd %currentDirectory%
cd demoUI

# cd C:\Users\cocoa\Documents\GitHub\pokemonCardUi\demoUI
# ..\env\Scripts\activate
# pause
# python -m flask run
#
#../env/bin/python -m demoUI.websocket_server

#start "" "http://127.0.0.1:5000 "
#../env/bin/python -m flask run
#../env/bin/python -m flask run --host=0.0.0.0 --cert=adhoc
#../env/Scripts/python -m flask run --host=0.0.0.0 --cert=adhoc
#../env/Scripts/python -m flask run --host=0.0.0.0 
../env/bin/python -m flask run --host=0.0.0.0
cd ..
#pause
