#!/bin/bash

now=$(date +"%T")
echo ">>>>> Current time : $now"

source "/home/ubuntu/VENV/helloworld/bin/activate"

python3 /home/ubuntu/helloworld/helloworld.py

now=$(date +"%T")
echo "<<<<< Finished at : $now"

sleep 5m

deactivate

