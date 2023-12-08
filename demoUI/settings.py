import flask 
import json
import sys, os


if hasattr(sys, '_MEIPASS'):
   # Running as a standalone executable, get the executable's directory path
   SITE_ROOT = sys._MEIPASS
   SITE_ROOT = os.path.abspath(os.path.dirname(sys.executable))
   print('Running as a standalone executable')
else:
   print('Running as a script settings')
   # Running as a script, use the script's directory path
   SITE_ROOT = os.path.dirname(os.path.abspath(__file__))
   #SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
print(SITE_ROOT)

#if getattr(sys, 'frozen', False):
#    # If the application is run as a bundle, the PyInstaller bootloader
#    # extends the sys module by a flag frozen=True and sets the app 
#    # path into variable _MEIPASS'.
#    SITE_ROOT = sys._MEIPASS
#else:
#    SITE_ROOT = os.path.dirname(os.path.abspath(__file__))
#    #SITE_ROOT = os.path.realpath(os.path.dirname(__file__))

json_url = os.path.join(SITE_ROOT,  "settings.json")
print(json_url)
settingsFile=open(json_url,'r')
settings=json.load(settingsFile) 


app = flask.Flask(__name__)
