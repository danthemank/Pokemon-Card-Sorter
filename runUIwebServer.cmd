set FLASK_APP=webapp
set FLASK_ENV=development

SET mypath=%~dp0
set currentDirectory = %mypath:~0,-1%
echo %currentDirectory%
cd %currentDirectory%
cd demoUI

start "" "http://127.0.0.1:5000 "
..\env\Scripts\python -m flask run
cd ..
pause
