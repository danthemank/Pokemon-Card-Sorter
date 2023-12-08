#!/bin/bash

./env/bin/python -m demoUI.websocket_server &

./admin.sh 0 n &

./runUIwebServer.sh


