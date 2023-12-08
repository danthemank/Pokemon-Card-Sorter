#!/bin/bash

cd /home/ed/GitHub/pokemonCardUi/pokemonCardDocker

cp -r ../DatabaseImageMatchingLibrary ./

sudo docker build -t python-lambda-pokemon:test .

#deploy to aws
sudo docker tag python-lambda-pokemon:test 047627598834.dkr.ecr.us-east-1.amazonaws.com/pokemon-card-repo:latest
sudo docker push 047627598834.dkr.ecr.us-east-1.amazonaws.com/pokemon-card-repo:latest
aws lambda update-function-configuration --region us-east-1 --profile admin --function-name "python-lambda-pokemon" --description "foo"

#this does not work
#aws lambda update-function-code --region us-east-1 --profile admin --function-name python-lambda-pokemon --image-uri 047627598834.dkr.ecr.us-east-1.amazonaws.com/pokemon-card-repo:latest

cd ..
