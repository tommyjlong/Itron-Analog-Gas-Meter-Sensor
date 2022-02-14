# Itron Analog Gas Meter Sensor for Home Assistant
This project provides an Itron gas meter sensor that can be used with Home Assistant.  In particular, this is for an Itron meter that looks like the following:

<img alt="Itron Gas Meter" src="./readme_media/Itron_Gasmeter_low.jpg" width="500" height="500"  />

This Project consists of the following software:
* Gasmeter Analyzer - This retrieves an image (picture) taken of the Itron meter, and with configured input from the user on dial coordinates, it deterimines which angle each dial is pointing at, and converts this to a number.  The analyzer repeats this for each dial and then determines the "readout" value of the meter.  Once the value is determined, an MQTT Publish message is sent to an MQTT Broker containing the metered value.
* Pi Camera - Although any camera will do, this project uses a Raspberry Pi ZeroW and a first generation camera module to take images of the meter.  There are two Python codes for this:
  * Raspberry Pi Camera - This Python code is used to take a picture of the meter.  It also turns on the lighting for the camera as well.
  * HTTP Server - This Python code is the http server for the Pi Camera.  It can be used to tell the PiCamera to capture an image, and it can be used to retrieve the image taken.  It can also be used to read the temperature of the Pi's CPU temperature monitor.

# Gasmeter Analyzer
The python3 code for the `gasmeter_analyzer` does the following:
* Retrieves the image from the camera for the configured URL,
* Rotates the image (See Alignment Doc TBD)
* Takes the configured Dial Coordinates and determines the needle angle and thus a value for a given gauge.  A needle angle of 0 corresponds to "0" on the gauge.
* "Reads the Meter" like a human.  A more significant gauge digit has its value determine in part based on the adjacent less significant gauge's digit value. The least significant gauge's dial is taken at face value (within a hundreth).
* As a sanity check, it compares the just read meter value with a previously read meter value to make sure the values are never decreasing as the gas meter values are always increasing.
* Publishes an MQTT message to a broker containing the just read meter value

Before the analyzer can be used, **an alignment process must be performed  and the dial coordinates need to be determined** (Document TBDone).

## Configuring

## Theory of Operation
The `gasmeter_analyzer` takes the configured dial coordinates for an individual gauge (that is the center of rotation for the needle), and takes the configured radius and will draw a circle around the dial's center.  This circle should be nearly the same size as the gauge's circle on the face of the gas meter.  This circle is a single pixel in thickness and there will be several hundred pixels making up the circle.  The `gasmeter_analyzer` will next draw lines from the dial's center to each pixel in the circle and will also compute the angle of the drawn line with 0 degrees at the topmost point of the circle.  From there it will compute an average grayscale for each line drawn.  As the needle is black in color, the `gasmeter_analyser` will look for the line with the darkest grayscale average value and assumes it has found the needle.  Given the selected line as the winner, it's angle is known, and a numeric value for the gauge is next computed to within a couple of fractional decimals (hundreths).  It should be noted too that the configured direction of the gauge's numbering, whether clockwise (CW) or counter-clockwise (CCW) is taken into account when computing the value.

Once all the gauges' dial values are determined, `gasmeter_analyzer` will come up with a meter value similarly to how a human would read the gauges and come up with a value.  One of the main drivers in doing this rather than taking the readings at face value has to do with the fact that the camera's image while 2D, has some 3D distortions regarding the dials and their needle. A needle may look on the image as if it is at or has gone past a digit marker (we'll call the digit boundary) whereas in reality it has not.  A way to determine a more true value of a given gauge's needle position relative to a digit boundary is to look at the previous less significant gauge's dial value.  For example, if a needle looks on the image (and likewise as seen by `gasmeter_analyzer') like it has moved barely past digit '1', we can look at the previous digit, and if the previous digit is approaching '0' but not past '0', then the needle of interest has not yet moved past digit '1'. Each gauge's dial value is determined this way and then rounded down to the nearest integer value (0 to 9). The exception will be the least significant gauge's dial (as it doesn't have a lesser signficant gauge) so the least significant gauge's dial value is taken at face value.  All the gauge's dial values are put together to form the meter's value.

## Restrictions/Limits/Quirks
### Lighting
The most important aspect of the analyzer is the lighting on the gasmeter face.  Sunlight of course is great, but at night, artificial lighting is required. During the development of this project, the following problems were discovered:
1. The clear plastic face of the Itron meter is highly reflective.  Any lighting of course has to be positioned to not reflect off of the dials.
2. The needles on the gauges are also reflective.  They are angled relative to the face of the meter, so lighting that is positioned near a dial can also reflect off of a needle when the needle is at a small range of angles (but not all).
3. The needles can cast shadows.  The needles are essentially a 3D object protruding above the white faceplate of the meter. If there are too few points of lighting shining on the meter, chances are that while most of the dial is nicely illuminated, part of the dial will be darker due to a shadowing effect caused by the needle.
### Visual Perspective and Resolution
The Camera's distance from the meter has a tradeoff.  One would like the perspective (i.e. bird's eye view) to be such that the meter and its needles look nearly 2D, so positioning the camera far from the meter makes this more and more possible.  The `gasmeter_analyzer` will have a more finer grain resolution in computing the dial's angle when more pixels are used around a gauge, so moving the camera too far away will end up with a smaller guage in the image and thus fewer pixels and thus a more coarse dial angle.  This project ended up with around 6.5" distance between the camera lens and the face of the gas meter, and a camera resolution of 2592 x 1944.
# Raspbery Pi Camera
## Camera Image Capture
The guidelines in this section are mainly interested in configuring 

## HTTP Web Server For Camera

# Credits
- Sonya Sawtelle: Wrote a nice and detailed Jupyter-based [blog](https://sdsawtelle.github.io/blog/output/automated-gauge-readout-with-opencv.html) on how to find a needle on an Itron Gas meter and interprete its angle.  The method `def find_needle` described in the blog is made use of in the `gasmeter_analyzer`.

# License
```
- MIT
```
# 3D Enclosure
This project also uses a 3D printed "box".  This box is used to hold the camera in place with the gas meter, and provides consistent illumination of the gas meter during both day and night.  The "box" provides the following:
* Adapts to the front half of the meter on one end of the box.
* A groove to hold the Edison LED filament in place which allows the filament to surround the front edge of the meter.
* Adapts to an enclosure on the other end that contains the Raspberry Pi camera.
The STL files will be provided some time in the future.
