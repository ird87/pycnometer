#!/usr/bin/python
import sys  # sys нужен для передачи argv в QApplication

class RPIO(object):
    """docstring"""

    def __init__(self):
        """Constructor"""
        #self.ports = [1, 2, 3, 4, 5]

    def PortOn(self, x):
        if x>0:
            print('порт ' + str(x) + ' включен.')
        else:
            print('порт не назначен')

    def PortOff(self, x):
        if x>0:
            print('порт ' + str(x) + ' выключен.')
        else:
            print('порт не назначен')

    def Exit(self):
        print('Выключили все!')