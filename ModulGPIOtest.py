#!/usr/bin/python
# Модуль для взаимодействия с Raspberry Pi (Тестовая версия!!!)
import inspect
import os
import time

from Config import Valve

"""Проверака и комментари: 08.01.2019"""

"""
    self.valves - valves setup from config.ini    
"""


class GPIO(object):
    """GPIO for testing mode"""

    def __init__(self, valves: list[Valve]):
        # Список заявленных к работе портов
        self.valves = valves

    def port_on(self, valve: Valve):
        """Open valve and activate hold mode"""
        if valve.is_correct():
            print("Valve.OpenPort #{0} is open".format(valve.port_open))
            time.sleep(0.06)
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
