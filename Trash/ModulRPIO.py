#!/usr/bin/python
import sys  # sys нужен для передачи argv в QApplication
import RPIO
import spidev

class RPIO(object):
    """docstring"""

    def __init__(self):
        """Constructor"""
        self.portsSetup = [0, 0, 0, 0, 0]

    def PortOn(self, x):
        if x>0:
            if self.portsSetup[x-1]==0:
                self.portsSetup[x - 1]=1
                RPIO.setup(x, RPIO.OUT, initial=RPIO.LOW)
            RPIO.output(x, 1)
            print('порт ' + str(x) + ' включен.')
        else:
            print('порт не назначен')

    def PortOff(self, x):
        if x>0:
            if self.portsSetup[x-1]==0:
                self.portsSetup[x - 1]=1
                RPIO.setup(x, RPIO.OUT, initial=RPIO.LOW)
            print('порт ' + str(x) + ' выключен.')
            RPIO.output(x, 0)
        else:
            print('порт не назначен')

    def Exit(self):
        RPIO.cleanup()