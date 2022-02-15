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
* Rotates the image in order to align the gauges along the horizontal plane.
* Takes the configured "Dial Center Coordinates", searches for and locates the needle, and with it, its angle and thus a value for each gauge.  
* "Reads the Meter" like a human.  A more significant gauge digit has its value determine in part based on the adjacent less significant gauge's digit value. The least significant gauge's dial is taken at face value (within a hundreth).
* As a sanity check, it compares the just read meter value with a previously read meter value to make sure the values are never decreasing as the gas meter values are always increasing.
* Publishes an MQTT message to a broker containing the just read meter value

Before the analyzer can be used, **an alignment process must be performed  and the dial coordinates need to be determined.** See the [Alignment and Coordinates Doc](./readme_media/Align_Coordinates.pdf).

Note: The code's image processing is rather CPU intensive and so one should take caution when deploying it on a system needing to do other important/critical things as well. _I actually wanted to try this out on a PiZeroW, but opencv2 (which gasmeter_analyser uses extensively) doesn't install so easily, and I didn't spend anymore time trying to get it to run._
 
## Theory of Operation
The `gasmeter_analyzer` takes the configured dial coordinates for an individual gauge (that is the center of rotation for the needle), and takes the configured radius and will draw a circle around the dial's center.  This circle should be nearly the same size as the gauge's circle on the face of the gas meter.  This circle is a single pixel in thickness and there will be several hundred pixels making up the circle.  The `gasmeter_analyzer` will next draw lines from the dial's center to each pixel in the circle and will also compute the angle of the drawn line with 0 degrees at the topmost point of the circle.  From there it will compute an average grayscale for each line drawn.  As the needle is black in color, the `gasmeter_analyser` will look for the line with the darkest grayscale average value and assumes it has found the needle.  Given the selected line as the winner, it's angle is known, and a numeric value for the gauge is next computed to within a couple of fractional decimals (hundreths).  It should be noted too that the configured direction of the gauge's numbering, whether clockwise (CW) or counter-clockwise (CCW) is taken into account when computing the value.

Once all the gauges' dial values are determined, `gasmeter_analyzer` will come up with a meter value similarly to how a human would read the gauges and come up with a value.  One of the main drivers in doing this rather than taking the readings at face value has to do with the fact that the camera's image while 2D, has some 3D distortions regarding the dials and their needle. A needle may look on the image as if it is at or has gone past a digit marker (we'll call the digit boundary) whereas in reality it has not.  A way to determine a more true value of a given gauge's needle position relative to a digit boundary is to look at the previous less significant gauge's dial value.  For example, if a needle looks on the image (and likewise as seen by `gasmeter_analyzer') like it has moved barely past digit '1', we can look at the previous digit, and if the previous digit is approaching '0' but not past '0', then the needle of interest has not yet moved past digit '1'. Each gauge's dial value is determined this way and then rounded down to the nearest integer value (0 to 9). The exception will be the least significant gauge's dial (as it doesn't have a lesser signficant gauge) so the least significant gauge's dial value is taken at face value.  All the gauge's dial values are put together to form the meter's value.

## Configuring
**Configuration of For reaching the Gas Meter Camera**
* `gasmeter_camera_ip` - IP address and Port to reach the gasmeter camera. HTTP GET requests are used with this. <br/>
  Example: `gasmeter_camera_ip = '192.168.0.14:8080'`
* `image_url_postfix` - The latter portion of the URL that is used retrieve the gasmeter image.  It is generally the filename with extension.  `gasmeter_analyzer` will accept `.jpg`, `.png`, and `.npy` (Numpy 3D array of the image).  _I actually use a numpy file type. JPEG compression can be lossy, and although PNG is a lossless compression, gasmeter_analyzer uses opencv which operates on numpy arrays, so by using a numpy file of the image there is no extra step in conversion._ <br/>
  Example: `image_url_postfix = '/gasmeter_last.npy' #include forward slash`. <br/>
  With these examples, the final URL will be `http://192.168.0.14:8080/gasmeter_last.npy` <br/>

**Configuration of Local Operations**<br/>
_See the [Alignment and Coordinates Doc](./readme_media/Align_Coordinates.pdf) for help in determining some of the configured values below._
* `data_path` - The directory where gasmeter_analyzer will read/write files to.  
  For example, I use an old HA Python venv directory: `data_path = "/opt/homeassistant/venv_3.8/"` <br/>
* `ROTATE_IMAGE` - Number of degress to rotate the image around its center. Positive values of degrees will rotate the image counterclockwise. <br/>
  Example: `ROTATE_IMAGE = +0.5`
* `CIRCLE_RADIUS` - The distance, in number of pixels, from the center of the needle's axis of rotation to the tip of the needle. <br/>
  Example:  `CIRCLE_RADIUS = 107`
* `gauge_centers` - The (x,y) coordinates, in number of pixels, for the center of the needle's axis of rotation.  (x=0,y=0) is located at the uppermost leftmost corner of the image.  The (x,y) values are always positive.  The coordinates are configured using a Python list structure with the first item representing the least signficant gauge digit (the gauge at the upper right from the Itron picture above), and the last item representing the most significant gauge digit (the gauge at the upper left from the Itron picture above). <br/>
  Example: 
  ```
  gauge_centers = [
    (1615, 897),   #Least Significant gauge digit
    (1384, 899),
    (1148, 899),
    (915, 903)     #Most Signficant gauge digit
    ]
  ```
* `readout_conventions` - The rotational direction of each gauge either `CW` for clockwise, or `CCW` for counter-clockwise. These conventions are configured using a Python list structure with the first item representing the least signficant gauge digit (the gauge at the upper right from the Itron picture above), and the last item representing the most significant gauge digit (the gauge at the upper left from the Itron picture above). <br/>
  Example of the Itron gasmeter picture above:
  ```
  readout_conventions = [
    "CW",    #Least Significant gauge digit
    "CCW",
    "CW",
    "CCW"    #Most Signficant gauge digit
    ]
  ```
**Configuration of MQTT Client**
`gasmeter_analyzer` provides an MQTT Client which uses a simple single shot publisher for each message sent to the broker.
* `client_name` - A name used by the broker to identify the gasmeter_analyzer as an MQTT client. <br/>
  Example: `client_name = "gasmeter_single_pub_client"`
* `host_name` - IP Address of the MQTT Broker. <br/>
  Example: `host_name = '192.168.0.15'
* `username`and `password` - If you use authentication to access the MQTT broker, this is the username and password to be used. <br/>
  Example:
  ```
  username = "mqtt_broker_username"
  password = "mqtt_broker_passwd"
  ```
* `topic` - The topic used for sending the gas meter's value. <br/>
  Example: `topic = "gasmeter/outside/value"`
* `retain` - Whether to have the broker retain the gas meter's value. <br/>
  Example: `retain = True #True or False.`
**Configure the Logger**
The Logger is setup out of the box to send info, warning and error level logs to the system's syslog logger.  When first using gasmeter_analyzer, you may want more detailed output and you may want it sent instead directly to the console instead of the syslogger.
* `DEBUG   = 0 #set to 1 to get debug information (and all other levels).`
* `INFO    = 1 #set to 1 and DEBUG=0 to send info, warning, and error level information`
* `CONSOLE = 0 #set to 1 to send output to stdout, 0 to local syslog`

## Restrictions/Limits/Quirks
### Lighting
The most important aspect of the analyzer is the lighting on the gasmeter face.  Sunlight of course is great, but at night, artificial lighting is required. During the development of this project, the following problems were discovered:
1. The clear plastic face of the Itron meter is highly reflective.  Any lighting of course has to be positioned to not reflect off of the dials.
2. The needles on the gauges are also reflective.  They are angled relative to the face of the meter, so lighting that is positioned near a dial can also reflect off of a needle when the needle is at certain angles (but not all).
3. The needles can cast shadows.  The needles are essentially a 3D object protruding above the white faceplate of the meter. If there are too few points of lighting shining on the meter, chances are that while most of the dial is nicely illuminated, part of the dial will be darker due to a shadowing effect caused by the needle.  Portions of a gauge's silkscreen has a lot of black.  The '0' position on the gauge is a prime example where there is the "tick" mark in black, followed by the top and then bottom of the number '0' which is black, along with the direction pointing arrow which is also in black. If the needle is casting a shadow along this path, then the gasmeter_analyzer will see a lot of dark grayscale and may falsely interprete the needle as being in this position. <br/>

_My solution was to use "Edison LED filaments" wrapped around the front edge/sides of the meter for the lighting._
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
