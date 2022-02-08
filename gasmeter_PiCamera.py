from gpiozero import LED
from time import sleep
#from picamera import PiCamera
from picamerax import PiCamera
import subprocess
import numpy as np
import warnings #picamera uses this

#Turn off any warnings produced by picamera
warnings.simplefilter("ignore")

#Camera Capture Resolution
#  camera.resolution = (CAMERA_REZ_HORZ,CAMERA_REZ_HORZ)
#  Examples:
#    camera.resolution = (2592, 1944)
#    camera.resolution = (1920, 1080)
#    camera.resolution = (1296, 972)
#    camera.resolution = (640, 480)
CAMERA_REZ_HORZ = 2592
CAMERA_REZ_VERT = 1944
#CAMERA_REZ_HORZ = 640
#CAMERA_REZ_VERT = 480

class active_led:
    """ Class that manages Pi' onboard ACTivity LED """
    def led_on_off(self,value):
        """
          run the shell command:
          echo $value | sudo tee /sys/class/leds/led0/brightness
        """
        filename = "/sys/class/leds/led0/brightness"
        p1 = subprocess.Popen(["echo",value], stdout=subprocess.PIPE)
        p2 = subprocess.Popen(["sudo","tee",filename], stdin=p1.stdout,
                        stdout=subprocess.PIPE)
        p2.communicate()
    def on(self):
        self.led_on_off("1")
    def off(self):
        self.led_on_off("0")

def main():
    led= LED(17)   # LED1 is connected to GPIO 17 (3.3 V on a Pi Zero)
    led2 = LED(27) # LED2 is connected to GPIO 27 (3.3 V on a Pi Zero)
    led_act = active_led() # Pi Zero ACTivity LED
    
    # Turn on Illuminating LEDs. Turn Off Pi's ACTivity LED
    led.on() 
    led2.on() 
    led_act.off()
    
    camera = PiCamera()

    #Future to do someday: turn off the camera's LED.
    #camera.led = False #requires RPi.GPIO package installed and in BCM mode.

    camera.resolution = (CAMERA_REZ_HORZ, CAMERA_REZ_VERT)
   #camera.sensor_mode=3 #This causes "Timed out waiting for capture to end" error.

    #Setup a Numpy Array for capturing images.
    #  For Numpy Array, according to PiCamera Docs
    #  horizontal: round up nearest x32, vertical: round up nearest x16
    np_vert = int( np.ceil(CAMERA_REZ_VERT/16)*16 )
    np_horz = int( np.ceil(CAMERA_REZ_HORZ/32)*32 )
   #print("np_vert: %i, np_horz: %i" % (np_vert, np_horz) )
   #output = np.empty((1952, 2592, 3), dtype=np.uint8)
    output = np.empty((np_vert, np_horz, 3), dtype=np.uint8)

    # If you want to preview it on the display, uncoment the next line.
    #camera.start_preview()
    
    # Meter Mode
    #   All modes set up two regions: 
    #   - centeral region, 
    #   - outer region
    #camera.meter_mode    = 'average' #default
    camera.meter_mode    = 'spot'    #smallest central region
    #camera.meter_mode    = 'backlit' #largest central region
    #camera.meter_mode    = 'matrix'  #

    # Exposure Mode
    #camera.exposure_mode = 'off'
    #camera.exposure_mode = 'auto'
    camera.exposure_mode = 'nightpreview'
    #camera.exposure_mode = 'night'
    #camera.exposure_mode = 'fireworks' #don't use this. Too dark
    #camera.exposure_mode = 'verylong'  #don't use this. Too dark
    #camera.exposure_mode = 'snow'      #don't use this. Too dark
    #camera.exposure_mode = 'backlight' #About the same as auto
    #camera.exposure_mode = 'spotlight' #don't use this. Its black.

    # Flash Mode
    #camera.flash_mode = 'redeye'

    # Average White Balance Mode
    #camera.awb_mode = 'off'         #requires adjusting gains manually.
    #camera.awb_mode = 'auto'
    #camera.awb_mode = 'incandescent'#warm still shows some yellow-ish white
    #camera.awb_mode = 'tungsten'    #2500K to 3500K
    #camera.awb_mode = 'fluorescent' #2500K to 4500K
    #camera.awb_mode = 'sun'         #5000K to 6500K
    #camera.awb_mode = 'cloud'       #6500K to 12000K
    #camera.awb_mode = 'flash'  	 #should make less blue
    camera.awb_mode = 'greyworld' #Mimic IRFilter.Not valid w. regular PiCamera

    #Other settings you may want to play with
    #camera.iso = 800 #makes a little darker. Non-0 nullifies Exposure mode
    #camera.brightness = 80
    #camera.contrast = 80
    #camera.sharpness = 100 #default=0 range -100 to +100
    #camera.color_effects = (128,128)

    sleep(2)
    #Capture an image for both JPEG and Numpy 
    #  Put it in RAM file system /run/shm/ to minimize wear on SD card
    camera.capture('/run/shm/gasmeter_last.jpg')
    camera.capture(output,format='rgb') #Note:set to 'bgr' did not work
    np.save('/run/shm/gasmeter_last', output) #extension is .npy

    #If you are running preview, then uncomment next line
    #camera.stop_preview()

    sleep(1)  #Makes a very very slight difference.

    #Future to do someday: turn back on the camera's LED.
    #camera.led = True


    camera.close()

    led.off()
    led2.off()
    led_act.on()

if __name__ == "__main__":
    main()
