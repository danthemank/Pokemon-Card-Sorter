@echo off

echo Received parameters: %1

rem if "%~1"=="" (
rem     exit /b 3
rem )

cd C:\Users\cocoa\Documents\GitHub\pokemonCardUi
.\env\Scripts\python.exe -m demoUI.admin %1
pause
