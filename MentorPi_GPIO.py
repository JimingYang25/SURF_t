#Driver For GPIO -- Matiner:Jiming Yang


import RPi.GPIO as GPIO 

def GPIO_Init(args=None) -> None:

    """Init GPIO as initial status"""
    GPIO.setmode(GPIO.BCM)

def GPIO_Deinit(args=None) -> None:
    """"Deinit GPIO"""
    GPIO.cleanup()



#Driver For GPIO -- Matiner:Jiming Yang
