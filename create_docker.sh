#!/bin/bash

cd /home/ed/GitHub/pokemonCardUi/pokemonCardDocker

cp -r ../DatabaseImageMatchingLibrary ./

sudo docker build -t python-lambda-pokemon:initial . -f Dockerfile_initial

cd ..
