#!/usr/bin/python3
from http.server import BaseHTTPRequestHandler,HTTPServer
import logging
import logging.handlers #Needed for Syslog
import sys
from pathlib import Path

# Can call the camera Python script asynchronously using subprocess
#  or synchronously (i.e. directly).  For now call directly.
#import subprocess
import gasmeter_PiCamera

#Configure the port number the http server will listen on
PORT_NUMBER = 8080 

#Configure file name of camera image (without filename extension)
GASMETER_IMAGE_NAME = "gasmeter_last" #Note: file name extension (.jpg) is in URL request

#Configure directory that http server will go looking for files:
GASMETER_IMAGE_DIRECTORY = "/run/shm" #Leave off last "/". 

#Configure the file where CPU Temperature can be queried for
CPU_TEMP_DIRECTORY = "/sys/class/thermal/thermal_zone0/temp"

# Setup Logger for this server.
#   If you want to see output to the Console, set CONSOLE = 1
#     Otherwise logs go to local syslog server.
#   If you want debug level output, then change the last lines
#      _LOGGER.setLevel from NOTSET to DEBUG. Can also set to INFO.
CONSOLE = 0
_LOGGER = logging.getLogger(__name__)
if CONSOLE:
    formatter = \
        logging.Formatter('%(message)s')
    handler1 = logging.StreamHandler(sys.stdout)
    handler1.setFormatter(formatter)
    handler1.setLevel(logging.NOTSET)
   #handler1.setLevel(logging.DEBUG)
    _LOGGER.addHandler(handler1)
else:
    formatter2 = \
        logging.Formatter('%(levelname)s %(asctime)s %(filename)s - %(message)s')
    handler2 = logging.handlers.SysLogHandler(address = '/dev/log')
    handler2.setFormatter(formatter2)
    handler2.setLevel(logging.NOTSET)
    _LOGGER.addHandler(handler2)

#LOGGER.setLevel(logging.DEBUG)
_LOGGER.setLevel(logging.INFO)
#_LOGGER.setLevel(logging.NOTSET)

#End of Configs

#Handle an incoming request
class myHandler(BaseHTTPRequestHandler):
    """Handle the incoming HTTP GET or POST Request."""

    def process_incoming(self):
        """Process the incoming request."""
        _LOGGER.info("Received Path: %s", self.path)
        _LOGGER.debug("Received The Following Headers: ")
        _LOGGER.debug("%s", self.headers)

        if (self.path.find("/api/capture_image") !=-1 ):
            _LOGGER.info("Running gasmeter_PiCamera .....")
           #p1 = subprocess.Popen(["/usr/bin/python3","/home/pi/gasmeter_PiCamera.py"] )
            gasmeter_PiCamera.main()
            _LOGGER.debug("Done.")
            self.send_response(200)
            #Let's return something even if null.
            mimetype='text/html'
            self.send_header('Content-type',mimetype)
            self.end_headers()
            self.wfile.write(str.encode('Capturing Image...Image Captured.')) #encode string to bytes

        elif (self.path.find( "/api/cpu_temp" ) !=-1 ):
            _LOGGER.info("Getting CPU Temperature.....")
            self.send_response(200)
            mimetype='text/html'
            self.send_header('Content-type',mimetype)
            self.end_headers()
            with open(CPU_TEMP_DIRECTORY,'r') as f:
                f_cpu_temp = f.read()
                cpu_temp_str = str(float(f_cpu_temp)/1000) #Pi returns 34704. Convert to 34.704
                self.wfile.write(str.encode(cpu_temp_str)) #encode string to bytes
        elif (self.path.find( GASMETER_IMAGE_NAME ) !=-1 ):
            _LOGGER.info("Retrieving " + self.path)
            filename = GASMETER_IMAGE_DIRECTORY + self.path #path starts with "/"
            if( Path(filename).is_file() ):
                self.send_response(200)
                #return something even if null.
                if self.path.endswith(".jpg"):
                    mimetype='image/jpeg'
                elif self.path.endswith(".png"):
                    mimetype='image/png'
                else:
                    mimetype='image/jpg'
                self.send_header('Content-type',mimetype)
                self.end_headers()
                with open(filename, 'rb') as file_handle:
                    self.wfile.write(file_handle.read())
            else:
                self.send_error(404,'The requested file was not found: %s' % self.path)
        else:
            self.send_error(404,'The URL request could not be processed: %s' % self.path)
        return

    def do_GET(self):
        """Process incoming GET requests."""
        _LOGGER.debug("Received a GET Request")
        return self.process_incoming()

    def do_POST(self):
        """Process incoming POST requests."""
        return self.process_incoming()

    def log_message(self, format, *args):
        """
        Remove this method if you want to see
        normal http.server output, otherwise
        override the http.server output with
        your own logger.
        """
        _LOGGER.debug("%s - - [%s] %s\n" %
                       (self.client_address[0],
                        self.log_date_time_string(),
                        format%args))
        return

#Main Program
try:
    #Create and startup the server and define the handler to manage
    #  the incoming http requests.
    server = HTTPServer(('', PORT_NUMBER), myHandler)
    _LOGGER.info("Started http server on port: %s", PORT_NUMBER)

    #Run forever
    server.serve_forever()

except KeyboardInterrupt:
    _LOGGER.info('  received, shutting down the server')
finally:
   #print("Closing the socket.  We're Done!")
    _LOGGER.info("Closing the socket.  We're Done!")
    server.socket.close()

