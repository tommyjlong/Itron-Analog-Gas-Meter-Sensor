#!/bin/bash
echo "Capturing Image (using curl)"
curl --max-time 60 -X GET http://192.168.0.10:8080/api/capture_image
echo ""
sleep 1

#If running in a python virtual environment:
echo "Sourcing venv"
source /opt/homeassistant/venv_3.8/bin/activate

#Run the Analyzer
echo "Running Analyzer"
python /opt/homeassistant/venv_3.8/gasmeter_analyzer.py
