#!/usr/bin/python
# Модуль для взаимодействия с Raspberry Pi (Тестовая версия!!!)
import inspect
import os
import time

from Config import Valve
from typing import List

"""Проверака и комментари: 08.01.2019"""

"""
    self.valves - valves setup from config.ini 
    self.wait_before_hold - time delay before hold mode   
"""


class GPIO(object):
    """GPIO for testing mode"""

    def __init__(self, wait_before_hold: float, valves: List[Valve]):
        # Список заявленных к работе портов
        self.valves = valves
        self.wait_before_hold = wait_before_hold

    def port_on(self, valve: Valve):
        """Open valve and activate hold mode"""
        if valve.is_correct():
            print("Valve.OpenPort #{0} is open".format(valve.port_open))
            time.sleep(self.wait_before_hold)
            print("Valve.HoldPort #{0} is open".format(valve.port_hold))
            print("Valve.OpenPort #{0} is close".format(valve.port_open))

    def port_off(self, valve: Valve):
        """Close valve"""
        if valve.is_correct():
            print("Valve.HoldPort #{0} is close".format(valve.port_hold))

    def all_port_off(self):
        """Close all valve"""
        for valve in self.valves:
            print("Valve.OpenPort #{0} is close".format(valve.port_open))
            print("Valve.HoldPort #{0} is close".format(valve.port_hold))

    def clean_up(self):
        """Setup clear"""
        print("Valves setup clear")
