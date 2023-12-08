import flask 
import json
import sys
import os

if hasattr(sys, '_MEIPASS'):
   # Running as a standalone executable, get the executable's directory path
   SITE_ROOT = sys._MEIPASS
   SITE_ROOT = os.path.abspath(os.path.dirname(sys.executable))
   print('Running as a standalone executable')
else:
   print('Running as a script init')
   # Running as a script, use the script's directory path
   SITE_ROOT = os.path.dirname(os.path.abspath(__file__))
   #SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
print(SITE_ROOT)

json_url = os.path.join(SITE_ROOT,  "settings.json")
settingsFile=open(json_url,'r')
settings=json.load(settingsFile) 

