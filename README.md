# Itron Analog Gas Meter Sensor for Home Assistant
This project provides a gas meter sensor that can be used with Home Assistant.  It is for an Itron meter that looks like the following:

<img alt="Itron Gas Meter" src="./readme_media/Itron_Gasmeter.jpg" width="500" height="500"  />

This Project consists of the following:
* Gasmeter Analyzer - This retrieves an image (picture) taken of the Itron meter, and with configured input from the user on dial coordinates, it deterimines which angle each dial is pointing at, and converts this to a number.  The analyzer repeats this for each dial and then determines the "readout" value of the meter.  Once the value is determined, an MQTT Publish message is sent to an MQTT Broker containing the metered value.
* Pi Camera - Although any camera will do, this project uses a Raspberry Pi ZeroW and a first generation camera module to take images of the meter.  There are two Python codes for this:
  * PiCamera - This Python code takes the picture of the meter.  It also turns on the lighting for the camera as well.
  * HTTP Server - This Python code is the http server for the Pi Camera.  It can be used to tell the PiCamera to capture an image, and it can be used to retrieve the image taken.  It can also be used to read the temperature of the Pi's CPU temperature monitor.


# Gasmeter Analyzer
## Configuring
## Theory of Operation
## Restrictions/Limits/Quirks
The most important aspect of the analyzer is the lighting on the gasmeter face.  Sunlight of course is great, but at night, artificial lighting is required. During the development of this project, the following problems were discovered:
1. The clear plastic face of the Itron meter is highly reflective.  Any lighting of course has to be positioned to not reflect off of the dials.
2. The needles on the gauges are also reflective.  They are angled relative to the face of the meter, so lighting that is positioned near a dial can also reflect off of a needle when the needle is at a small range of angles (but not all).
3. The needles can cast shadows.  The needles are essentially a 3D object protruding above the white faceplate of the meter. If there are too few points of lighting shining on the meter, chances are that while most of the dial is nicely illuminated, part of the dial will be darker due to a shadowing effect caused by the needle.
# Pi Camera
## Camera Image Capture
The guidelines in this section are mainly interested in configuring 

## HTTP Web Server For Camera

# Credits
- Sonya Sawtelle: Wrote a nice and detailed Jupyter-based [blog](https://sdsawtelle.github.io/blog/output/automated-gauge-readout-with-opencv.html) on how to find a needle on an Itron Gas meter and interprete its angle.  The method `def find_needle` described in the blog is made use of in the `gasmeter_analyzer`.

# License
```
- MIT
```

