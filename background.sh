#!/bin/bash

# Get the current date and time using the date command
current_date_time=$(date)

# Print the current date and time
echo "Current Date and Time: $current_date_time"

#export mypath=%~dp0
#export currentDirectory = %mypath:~0,-1%
#echo %currentDirectory%
#cd %currentDirectory%

# cd C:\Users\cocoa\Documents\GitHub\pokemonCardUi\demoUI
# ..\env\Scripts\activate
# pause
# python -m flask run
#
echo 'Received parameters:' $1

#if [ -z "$1" ]
#then
#    exit 1
#fi

#systemctl stop pokemon-admin.service

cd /home/goodwill/pokemonCard/pokemonCardUi/
#cd /home/ed/GitHub/pokemonCardUi

echo 'stopping background service'
sudo systemctl stop pokemon-admin.service

echo 'stopping manual sorter interface'
sudo pkill  admin.sh

echo 'starting background service'
sudo systemctl start pokemon-admin.service


#./env/bin/python -m demoUI.admin $1 $2
#pause
