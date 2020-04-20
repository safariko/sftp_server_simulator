#!/bin/bash

now=$(date +"%T")
echo ">>>>> Current time : $now"

source "/home/ubuntu/VENV/fdxedi/bin/activate"
python3 /home/ubuntu/dummy/dummydownloader.py

now=$(date +"%T")
echo "<<<<< Finished at : $now"

sleep 5m


deactivate

