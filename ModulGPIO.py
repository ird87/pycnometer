#!/usr/bin/python
import inspect
import os
import sys
import time
from Config import Valve
from typing import List

"""
    self.gpio - GPIO Module
    self.gpio.setmode - set mode GPIO (BOARD / BCM)
    
    ---------------------------------------------------------------------
    |    POWER    |   3.3V    |   1   |   2   |  5V       |    POWER    |
    ---------------------------------------------------------------------
    |   SDA1 I2C  |   GPIO2   |   3   |   4   |  5V       |    POWER    |
    ---------------------------------------------------------------------
    |   SCL1 I2C  |   GPIO3   |   5   |   6   |  GROUND   |             |
    ---------------------------------------------------------------------    
    |             |   GPIO4   |   7   |   8   |  GPIO14   |  UART0_TXD  |
    ---------------------------------------------------------------------
    |             |   GROUND  |   9   |   10  |  GPIO15   |  UART0_RXD  |
    ---------------------------------------------------------------------
    |             |   GPIO17  |  11   |   12  |  GPIO18   |   PCM_CLK   |
    ---------------------------------------------------------------------
    |             |   GPIO27  |  13   |   14  |  GROUND   |             |  
    ---------------------------------------------------------------------
    |             |   GPIO22  |  15   |   16  |  GPIO23   |             | 
    ---------------------------------------------------------------------
    |    POWER    |   3.3V    |  17   |   18  |  GPIO24   |             | 
    ---------------------------------------------------------------------  
    |  SPI0_MOSI  |   GPIO10  |  19   |   20  |  GROUND   |             |
    ---------------------------------------------------------------------
    |  SPI0_MISO  |   GPIO9   |  21   |   22  |  GPIO25   |             |
    ---------------------------------------------------------------------
    |  SPI0_SCLK  |   GPIO11  |  23   |   24  |  GPIO8    | SPI0_CE0_N  |
    ---------------------------------------------------------------------
    |             |   GROUND  |  25   |   26  |  GPIO7    | SPI0_CE1_N  |
    ---------------------------------------------------------------------  
    |I2C ID EEPROM|   ID_SD   |  27   |   28  |  ID_SC    |I2C ID EEPROM|
    --------------------------------------------------------------------- 
    |             |   GPIO5   |  29   |   30  |  GROUND   |             |
    ---------------------------------------------------------------------
    |             |   GPIO6   |  31   |   32  |  GPIO12   |             |  
    ---------------------------------------------------------------------
    |             |   GPIO13  |   33  |   34  |  GROUND   |             |  
    ---------------------------------------------------------------------
    |             |   GPIO19  |   35  |   36  |  GPIO16   |             |  
    ---------------------------------------------------------------------
    |             |   GPIO26  |   37  |   38  |  GPIO20   |             |  
    ---------------------------------------------------------------------
    |             |   GROUND  |   39  |   40  |  GPIO21   |             |  
    ---------------------------------------------------------------------  
    
    self.valves - valves setup from config.ini 
    self.wait_before_hold - time delay before hold mode   
"""


class GPIO(object):
    """GPIO for working mode"""

    def __init__(self, wait_before_hold: float, valves: List[Valve]):
        import RPi.GPIO as GPIO
        self.gpio = GPIO
        self.gpio.setmode(GPIO.BOARD)
        self.valves = valves
        
        ports = []
        for valve in valves:
            ports.append(valve.port_open)
            ports.append(valve.port_hold)
        # установки GPIO
        self.gpio.setup(ports, GPIO.OUT, initial=GPIO.LOW)
        self.wait_before_hold = wait_before_hold

    def port_on(self, valve: Valve):
        """Open valve and activate hold mode"""
        # проверяем, что порт указан
        if valve.is_correct():
            self.gpio.output(valve.port_open, True)
            time.sleep(self.wait_before_hold)
            self.gpio.output(valve.port_hold, True)
            self.gpio.output(valve.port_open, False)

    def port_off(self, valve: Valve):
        """Close valve"""
        # проверяем, что порт указан
        if valve.is_correct():
            self.gpio.output(valve.port_hold, False)

    def all_port_off(self):
        """Close all valve"""
        for valve in self.valves:
            self.gpio.output(valve.port_open, False)
            self.gpio.output(valve.port_hold, False)

    def clean_up(self):
        """Setup clear"""
        self.gpio.cleanup()
