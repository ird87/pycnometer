#!/usr/bin/python
import inspect
import os
import sys
import RPi.GPIO as GPIO
import time
"""Проверака и комментари: 08.01.2019"""

"""
"Класс для работы с GPIO с Raspberry Pi"    
    self.gpio - ссылка на модуль работы с GPIO
    self.gpio - устанавливаем вариант работы с GPIO
    self.ports - берем номера портов из config.ini
"""

class GPIO(object):
    """docstring"""

    """Конструктор класса. Поля класса"""
    def __init__(self, ports):
        import RPi.GPIO as GPIO
        self.gpio = GPIO
        self.gpio.setmode(GPIO.BOARD)
        self.ports = ports
        # установки GPIO
        self.gpio.setup(self.ports, GPIO.OUT, initial = GPIO.LOW)

    """Метод включаем подачу напряжения на указанный порт"""
    def port_on(self, port):
        # проверяем, что порт указан
        if port > 0:
            if(port==36):
                self.gpio.output(36, True)
                time.sleep(0.06)
                self.gpio.output(32, True)
                self.gpio.output(36, False)
            else:            
                self.gpio.output(port, True)

    """Метод отключает подачу напряжения на указанный порт"""
    def port_off(self, port):
        # проверяем, что порт указан
        if port > 0:
            if(port==36):
                self.gpio.output(32, False)
            else: 
                self.gpio.output(port, False)

    """Метод отключает подачу напряжения на все заявленные к использованию порты"""
    def all_port_off(self):
        for port in self.ports:
            self.gpio.output(port, False)

    """Метод для сбрасывания установки"""
    def clean_up(self):
        self.gpio.cleanup()