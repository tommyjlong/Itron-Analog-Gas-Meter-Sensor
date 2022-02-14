import requests
import cv2
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import io
import logging
import logging.handlers #Needed for Syslog
import sys
from pathlib import Path #Use this to check for file existence
import paho.mqtt.publish as publish

#Analyzer Configs.
data_path = "/opt/homeassistant/venv_3.8/" #Directory to store files.
gasmeter_camera_ip = '192.168.0.10:8080'   #Camera http server ip:port
image_url_postfix = '/gasmeter_last.jpg' #include forward slash
ROTATE_IMAGE = +0.5 #positive values degrees counterclockwise
CIRCLE_RADIUS = 107 
gauge_centers = [
    (1615, 897),   #Least Significant gauge digit
    (1384, 899), 
    (1148, 899), 
    (915, 903),    #Most Signficant gauge digit
   #(556, 635), 
   #(780, 913)
    ]
readout_conventions = [
    "CW",          #Least Signficant gauge digit
    "CCW", 
    "CW", 
    "CCW",         #Most Signficant gauge digit
   #"CCW", 
   #"CCW"
    ]


#MQTT Configs:
broker_auth = {}
client_name = "gasmeter_single_pub_client"
host_name = '192.168.0.11'
#Optionally set a username and password for broker authentication.
#username = "my_username"
#password = "my_passwd"
#broker_auth = {'username':username, 'password':password}
topic = "gasmeter/outside/value"
retain = True #True or False.

# Setup Logger
DEBUG   = 0 #set to 1 to get debug information.
INFO    = 0 #set to 1 and DEBUG=0 to get info level information
CONSOLE = 0 #set to 1 to send output to stdout, 0 to local syslog

_LOGGER = logging.getLogger(__name__)
if CONSOLE:
    formatter = \
        logging.Formatter('%(message)s')
       #logging.Formatter('%(levelname)-8s %(message)s')
    handler1 = logging.StreamHandler(sys.stdout)
    handler1.setFormatter(formatter)
    handler1.setLevel(logging.NOTSET)
    _LOGGER.addHandler(handler1)
else:
    formatter2 = \
        logging.Formatter('%(filename)s %(levelname)-8s - %(message)s')
       #logging.Formatter('%(levelname)s %(asctime)s %(filename)s - %(message)s')
    handler2 = logging.handlers.SysLogHandler(address = '/dev/log')
    handler2.setFormatter(formatter2)
    handler2.setLevel(logging.NOTSET)
    _LOGGER.addHandler(handler2)

if DEBUG:
    _LOGGER.setLevel(logging.DEBUG)
#   _LOGGER.debug("The following Log levels are active:")
#   _LOGGER.critical("    Critical, ")
#   _LOGGER.error("    Error, ")
#   _LOGGER.warning("    Warning, ")
#   _LOGGER.info("    Info, ")
#   _LOGGER.debug("    Debug ")
elif INFO:
    _LOGGER.setLevel(logging.INFO)
else:
    _LOGGER.setLevel(logging.NOTSET)


def http_get_image(gasmeter_url, gasmeter_timeout=10):
        try:
            resp = requests.get(gasmeter_url, timeout=gasmeter_timeout)
            http_code = resp.status_code
            resp.raise_for_status() #For HTTPError
        except requests.exceptions.ConnectTimeout:
            print("Could not connect to Gasmeter: Timeout")
            gasmeter_reachable = False
            return False
        except requests.exceptions.ConnectionError:
            print("Could not connect to Gasmeter: Connection Error")
            gasmeter_reachable = False
            return False
        except requests.exceptions.HTTPError as err:
            print("Hub - HTTP Error: %s", err)
            if http_code == 401:
                LOG.info("Bad username or password for Gasmeter")
            else:
                print("HTTP return code from Gasmeter %s", http_code)
            gasmeter_reachable = False
            return False
        except requests.exceptions.RequestException as e:
            print("Error on Gas Meter is: %s", e)
            gasmeter_reachable = False
            return False
        gasmeter_reachable = True
        return resp

def rotate(image, angle, center = None, scale = 1.0):
    (h, w) = image.shape[:2]

    if center is None:
        center = (w / 2, h / 2)

    # Perform the rotation. Positive values rotate CCW
    M = cv2.getRotationMatrix2D(center, angle, scale)
    rotated = cv2.warpAffine(image, M, (w, h))
    return rotated

def find_needle(image, circ_col, circ_row, circ_rad):   

    #The coordinates reference that we will use is that of the image
    # in which starts at the upper left (0,0), except that we will
    # work in (column,row) order rather than the image's native (row,column) order.

    # Start w. an all-0s blank image (same size as our image, but only 1 channel).
    #   Draw a circle centered around the gauge center point.
    #   Extract the pixel indices (col,row) of the drawn circle perimeter.
    blank = np.zeros(image.shape[:2], dtype=np.uint8)

    cv2.circle(blank, (circ_col, circ_row), circ_rad, 255, thickness=1)
    ind_row, ind_col = np.nonzero(blank)
    indices = list(zip(ind_col, ind_row))  #This contains the pixel coords of the drawn circle.
   

    # Get the top of the drawn circle's coordinates in (col,row) order.
    #   We use this later as an index into a Panda's dataframe
    #   to get at other important information.
    # Technically the top is located at "radius" rows above the gauge's column center.
    #   We could assume the circle drawing tool will draw on this pixel,
    #   but for now we'll search the drawn circle itself just in case it doesn't.
    top_yval = min([y for (x,y) in indices])
    top_pixel = [(x, y) for (x, y) in indices if y == top_yval][0]


    # Translate Drawn Circle's absolute col, row cordinates
    #   to have (0,0) referenced at Gauge Center.
    #   This will allow us to use numpy vector math to
    #   compute the angle between points on the circle perimeter
    translated = []
    for (x, y) in indices:
        translated.append((x - circ_col, circ_row - y))

    # Construct dataframe holding various coordinate representations and pixel values
    df = pd.DataFrame({"indices":indices, "trans": translated })

    # Identify the pixel which is the topmost point of the drawn circle.
    #  We can't assume the drawn circle starts at the top, so search the circle pixel coords.
    df["top_pixel"] = (df["indices"] == top_pixel)

    #Trick in Pandas:  df.loc(row,col)
    #  If you provide a list of booleans
    #  (=True or False; non-string must start w. Capital)) that is the same size
    #  as the number of rows in the dataframe, you can use the
    #  position of "True" values as an index into the dataframe's rows.
    #  Here the top_pixel column of the dataframe can also be used
    #  to provide a list of booleans, and in this case, there will
    #  only be one value that is true, and its position in the list
    #  will be used to find the translated coordinate.
    #  df.loc will return the row and the value at (row,col), so select
    #  the value at (row,col) using .values[0]
    top_trans_pix = df.loc[df["top_pixel"], "trans"].values[0]

    # Compute "Angle" between top pixel vector ((0,0),top pixel) and
    #  circle perimeter vector ((0,0), circle perimeter pixel pt)
    #    The top pixel vector will be at 12 o'clock
    #  Note: In numpy, if the circle perimeter vector is counter-clockwise
    #        of the top pixel vector, the angle will be positive.
    angles = []
    for vec in df["trans"].values:
        angles.append((180 / np.pi) * np.arccos(np.dot(top_trans_pix, vec) / \
          (np.linalg.norm(top_trans_pix) * np.linalg.norm(vec))))
    df["angle"] = angles

    # Compute "Clock Angle" which is computed as the "Angle" relative to 12 o'clock 0/360 degrees.
    # For example, since top pixel vector is same as 12 o'clock, a
    # circle perimeter vector that is slightly counter-clockwise to the top pixel vector
    # will be say +5 degrees.  We want the clock angle to be 355 degrees.
    # Another example, if the circle perimeter vector is
    # slightly clockwise to the top pixel vector, say +5 degrees, we want the clock
    # angle to be +5 degrees.  So clock angle has to determine if the
    # perimeter pixel of interest has a column coordinate that is negative or positive
    # relative to the gauge center's column coordinate.
    df["clock_angle"] = df["angle"] + \
      (-2*df["angle"] + 360)*(df["trans"].apply(lambda x: x[0] < 0)).astype(int)


    # Draw lines between gauge center and perimeter pixels
    #   and compute mean and std dev of pixels along lines
    stds = []
    means = []
    gray_values = []

    #For each line to be drawn:
    #Start with a Blank all-0s image, same size as orginal.
    #Draw a line to each circle perimeter pixel and extract
    #  line's drawn coordinates (will be non-zero).
    #Given the lines coordinates, find the original image's
    #  corresponding coordinates and get the BGR values and compute gray values.
    #  Compute mean and standard deviation for all the gray values.
    for (pt_col, pt_row) in df["indices"].values:
        blank = np.zeros(image.shape[:2], dtype=np.uint8)
        cv2.line(blank, (circ_col, circ_row), (pt_col, pt_row), 255, thickness=2)  # Draw function wants center point in (col, row) order like coordinates
        ind_row, ind_col = np.nonzero(blank)
        b = image[:, :, 0][ind_row, ind_col]
        g = image[:, :, 1][ind_row, ind_col]
        r = image[:, :, 2][ind_row, ind_col]


        # Compute grayscale with naive equation.
        #   This is done for all pixels making up the drawn line.
        grays = (b.astype(int) + g.astype(int) + r.astype(int))/3

        stds.append(np.std(grays))
        means.append(np.mean(grays))
        gray_values.append(grays)

    #Add to Dataframe: Line's Standard Deviation, Mean, and all its Gray values
    df["stds"] = stds
    df["means"] = means
    df["gray_values"] = gray_values

    # Search DataFrame and find Line with smallest mean value.
    #   (This will be the predicted Gauge Needle location)
    # The DataFrame index of this Line will also
    #   provide the index to the corresponding needle clock angle.
    min_mean = df["means"].min()
    needle_angle = df.loc[df["means"] == min_mean, "clock_angle"].values[0]  # Find needle angle

    return df, needle_angle

def read_gauge(angle, convention):
    # Gauge readout according to convention
    if convention == "CW":
        readout = 10*angle/360
    else:
        readout = 10 - (10*angle/360)

   #print("Readout= ", readout)
   #readout = round(readout,2) 
    readout = float(np.round(readout, 2))
   #print("Readout= ", readout)
    if readout >= 10.0:
        readout = 0
    return readout

def handle_readouts(readout_digit):
    #tolerance = 0.25 #Around +/- 9 degress from a digit
    #tolerance = 0.50 
    tolerance = 0.40 

    #Meter digits right to left are listed left to right
    #readout_digit = [0.72, 0.03, 9.97, 9.77]
    #readout_digit = [1.72, 2.03, 9.30, 6.90]
    #readout_digit = [2.59, 0.14, 0.18, 9.58]
    digit = []
    number = 0.0
    
    for i,v in enumerate(readout_digit):
        digit.append(np.floor(readout_digit[i]) )
        if i > 0:
            _LOGGER.debug("")
            _LOGGER.debug("readout digit [%i] is %.2f", i, readout_digit[i] )
    
            if (np.ceil(readout_digit[i]) - readout_digit[i]) < tolerance:
                #Note: if readout_digit[i] is 1.00, np.ceiling(1.00) is also 1.00
                _LOGGER.debug("  Between digits within tolerance in UPPER portion.")
                _LOGGER.debug("  Has it crossed a digit boundary? Check w. previous digit")
                _LOGGER.debug("  Previous digit is %.2f", digit[i-1])
                if (digit[i-1] >= 0 and digit[i-1]) < 5.0:
                    _LOGGER.debug("  Previous digit >= 0 && <5.")
                    _LOGGER.debug("  This digit has crossed a digit boundary. Rounding UP")
                    #Note Boundary Condition - Upper Portion
                    #  if digit[i] is 1.00 exactly, np.ceiling(1.00) is 1.00. 
                    #  No need to round up/down further.
                    digit[i] = np.ceil(readout_digit[i]) 
                    if digit[i] >= 10.0:
                        digit[i] = 0.0
                else: 
                    _LOGGER.debug("  No it has not crossed digit boundary. Rounding Down as normal")
                    digit[i] = np.floor(readout_digit[i])

                    #Note Boundary Condition - Upper Portion at x.00
                    #  Ex. readout_digit[i] = 1.00, np.floor(1.00) will also be 1.00.
                    #      So if it has not crossed digit boundary, np.floor will not round down.
                    if (readout_digit[i] == np.floor(readout_digit[i]) ):
                        digit[i] = digit[i] -1
            else:
                if (readout_digit[i] - np.floor(readout_digit[i]) ) < tolerance:
                    _LOGGER.debug("  Between digits within tolerance in LOWER Portion.")
                    _LOGGER.debug("  Did it actually cross a digit boundary? Check with previous digit")
                    _LOGGER.debug("    Previous digit is %.2f", digit[i-1])
                    if digit[i-1] >= 5.0 :
                        _LOGGER.debug("  Previous digit >= 5. This digit has NOT yet crossed a digit. Rounding DOWN -1")
                        #Note Boundary Condition - Lower Portion
                        #  if readout_digit = 1.00, np.floor(1.00) is 1.00.
                        digit[i] = np.floor(readout_digit[i]) -1
                        if digit[i] <= 0.0:
                            digit[i] = 9.0
                    else:
                        _LOGGER.debug("  Yes it did cross boundary. Rounding Down as normal")
                        digit[i] = np.floor(readout_digit[i])
                else: 
                    _LOGGER.debug("  OK as is. Rounding Down as normal")

        else:
            _LOGGER.debug("readout digit[0] is %.2f" % readout_digit[0] )
           #digit[i] = np.floor(readout_digit[i])
            digit[i] = readout_digit[i]
    
        number = number + digit[i]*10**(i)
        _LOGGER.debug("  digit[%i] is determined to be %.2f", i, digit[i])

   #_LOGGER.debug("Final number is %.2f", number)
    return number


#Start of Main program
_LOGGER.info("Starting Gas Meter Analyzer")
_LOGGER.debug("Getting camera image via HTTP GET....")
#gasmeter_url = 'http://' + gasmeter_camera_ip + '/gasmeter_crop.jpg'
gasmeter_url = 'http://' + gasmeter_camera_ip + image_url_postfix
response = http_get_image(gasmeter_url,60)

if (response != False):
    _LOGGER.debug("  http response is: %s", response)
    #print('body is ', response.text) #don't do this for images
    if ( gasmeter_url.endswith('.jpg') ):
        with open(data_path + 'image1_retrieved.jpg', 'wb') as f:
            f.write(response.content)
        image = cv2.imread(data_path + 'image1_retrieved.jpg')
    elif ( gasmeter_url.endswith('.png') ):
        with open(data_path + 'image1_retrieved.png', 'wb') as f:
            f.write(response.content)
        image = cv2.imread(data_path + 'image1_retrieved.png')
    elif ( gasmeter_url.endswith('.npy') ):
        io_buf = io.BytesIO(response.content)
        rgb_image = np.load(io_buf)  #Assume retrieved file was saved in RGB order.
        image = cv2.cvtColor(rgb_image, cv2.COLOR_RGB2BGR)
        cv2.imwrite(data_path + 'image1_retrieved.png', image)
    else:
        _LOGGER.error("Specified File extension unsupported")

    _LOGGER.debug("Rotating Image .....")
    imcopy_pre_rot = image.copy()
    imcopy = rotate(imcopy_pre_rot, ROTATE_IMAGE )
    cv2.imwrite(data_path + 'image2_rotated.jpg', imcopy)
    

    circ_radius = CIRCLE_RADIUS 
    
    _LOGGER.debug("Computing Gauge Angles and Values .....")
    readout_digit = [] 
    
    # For each gauge, get gauge readout and visualize results
    for i, ((c, r), convention) in enumerate(zip(gauge_centers, readout_conventions)):
        
        # Find needle angle
        df, needle_angle = find_needle(image=image, circ_col=c, circ_row=r, circ_rad = circ_radius)
    
        # 
        # Draw gauge needle radial line and circle onto the copy of original image.
        #  (pt_col,pt_row) is coordinates for circle point the needle was found to point to
        #
        (pt_col, pt_row) = df.loc[df["clock_angle"] == needle_angle, "indices"].values[0]
        
        # Draw tiny Green circle for radial line start.  Note: center point in (col, row) order
        cv2.circle(imcopy, (c, r), 5, (0, 255, 0), thickness=3)  
    
        # Draw Green needle radial line itself
        cv2.line(imcopy, (c, r), (pt_col, pt_row), (0, 255, 0), thickness=2)  
    
        # Draw Red circle
        cv2.circle(imcopy, (c, r), circ_radius, (0,0,255), thickness=4)  
    
        # Gauge readout according to convention
        readout_digit.append( read_gauge(needle_angle, convention) )
        _LOGGER.debug("  Gauge #%i angle is %.2f reading is %.2f", i+1, needle_angle, readout_digit[i] )
    
    #Save to disk the image copy of original with drawn needle radial lines and circles    
    cv2.imwrite(data_path + 'image3_pre_subplot.jpg', imcopy)
    
    #Create a plot showing y=row, x=columns of pre_subplot image
    plot_imcopy = cv2.cvtColor(imcopy, cv2.COLOR_BGR2RGB)
    fig, ax = plt.subplots(figsize=(18, 6))
    ax.imshow(plot_imcopy)
    #plt.imsave('gauges_readout.png', plot_imcopy) #This writes the image w/o axis
    plt.savefig(data_path + 'gauges_readout.jpg') #This writes the image w. axis.
    
    _LOGGER.debug("Convert Gauge readout values to a single value number...")
    meter_value = handle_readouts(readout_digit)
    meter_value = np.round(meter_value, 2)
    _LOGGER.info("Meter value is %f", meter_value )

    #Compare current value with previous.
    #  To avoid a problem  encountered a couple of times
    #  when using floating point, we'll convert to int.
    int_meter_value = int(meter_value * 100 ) 

    file = Path(data_path + 'last_read.txt')  
    if (file.is_file() ):
        with open(data_path + 'last_read.txt', 'r+') as g: #rd/wr
            last_value = int(g.read())
            _LOGGER.debug("Reading last_read.txt. Value: %i" , last_value)
            
            if (last_value > int_meter_value):
                _LOGGER.warning("Previously read value:%i > just read value:i. Not using meter value.",last_value, int_meter_value)
            else:
                _LOGGER.debug("Previous value:%i vs curent value:%i ... check passes. Updating last_read.txt", last_value, int_meter_value)
                g.seek(0) #start at file beginning
                g.write(str(int_meter_value))
               
                if (len(broker_auth) == 0):
                    broker_auth = None
                _LOGGER.debug("Publishing to MQTT broker")
                publish.single(topic=topic, payload=meter_value, retain=retain, \
                               hostname=host_name,client_id=client_name,\
                               auth=broker_auth)
    else:
        _LOGGER.warning("last_read.txt does not exist. Creating it.")
        with open(data_path + 'last_read.txt', 'w') as g:
            g.write(str(meter_value))
else:
    _LOGGER.warning("HTTP response is false. Could not get camera image. Exiting")
