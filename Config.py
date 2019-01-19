#!/usr/bin/python
# Модуль для загрузки настроек приложения из Configure.ini
import configparser
import json
import os
from enum import Enum

"""Проверака и комментари: 13.01.2019"""

"""
"Класс загружает и сохраняет все настройки в файл Config.ini
    self.p - Массив, в который будут загруженны технические данные по используемым портам.
    self.config - экземпляр модуля, который позволяет работать с ini файлами
    self.language - переменная, в которую будет загружена ссылка на файл с используемым языком
    self.pressure - переменная для хранения используемой единицы измерения давления
    self.smq_now - переменная, для хранения текущего количества измерений датчика
    self.smq_list - список всех возможных значений для self.smq_now
    self.VcL - Объем большой кюветы
    self.VcM - Объем средней кюветы
    self.VcS - Объем малой кюветы
    self.VdLM - Дополнительный объем большой или средней кюветы
    self.VdS - Дополнительный объем малой кюветы
    self.pulse_length - длинна импульса для Импульсивной продувки
    self.Pmeas_now  - давление, которое должен набрать прибор для текущей ед. измерения
    self.Pmeas - список для всех ед. измерений 
    pmeas_kPa_min - минимальный допуск для давления в кПа
    pmeas_kPa_max - максимальный допуск для давления в кПа
    pmeas_Bar_min - минимальный допуск для давления в Бар
    pmeas_Bar_max - максимальный допуск для давления в Бар
    pmeas_Psi_min - минимальный допуск для давления в psi
    pmeas_Psi_max - максимальный допуск для давления в psi
    self.spi_t - сколько секунд пауза между замерами давления в Ручном управлении
    self.spi_max_speed_hz - максимальная скорость получения данных с датчика в модуле SPI
    self.languages - список всех доступных языков
    self.testMode - переменная определяющая запушена ли программа в тестовом режиме 
                                                                        [0 - нет, в нормальном | 1 - да, в тестовом]
"""

class Configure(object):
    """Конструктор класса. Поля класса"""
    def __init__(self):
        self.p = [0, 0, 0, 0, 0]                    # Массив для записи номеров портов
        self.config = configparser.ConfigParser()   # Создаем экземпляр configparser
        self.config.read('Configure.ini')           # Указываем файл для считывания данных
        self.language = ''
        self.pressure = Pressure.kPa
        self.smq_now = 0
        self.smq_list = []
        self.VcL = 0
        self.VcM = 0
        self.VcS = 0
        self.VdLM = 0
        self.VdS = 0
        self.pulse_length = 0
        self.Pmeas = []
        self.Pmeas_now = 0
        self.pmeas_kPa_min = 0
        self.pmeas_kPa_max = 0
        self.pmeas_Bar_min = 0
        self.pmeas_Bar_max = 0
        self.pmeas_Psi_min = 0
        self.pmeas_Psi_max = 0
        self.spi_t = 0
        self.spi_max_speed_hz = 0
        self.languages = []
        # Загружаем данные из файла
        # [Ports]
        self.set_ports()

        # [[TestMode]]
        self.testMode = self.config.getint('TestMode', 'testMode')

    """Метод для назначения портам указанных в ini файле значений"""
    def set_ports(self):
        # [Ports]
        self.p[0] = self.config.getint('Ports', 'p1')
        self.p[1] = self.config.getint('Ports', 'p2')
        self.p[2] = self.config.getint('Ports', 'p3')
        self.p[3] = self.config.getint('Ports', 'p4')
        self.p[4] = self.config.getint('Ports', 'p5')

    """Метод для назначения языка программы согласно ini файлу"""
    def set_language(self):
        # [[Language]]
        self.config.read('Configure.ini')
        self.language = self.config.get('Language', 'language')

    """Метод для загрузки данных из ini файла"""
    def set_measurement(self):
        self.config.read('Configure.ini')
        self.pressure = Pressure(self.config.getint('Measurement', 'pressure'))
        self.smq_now = self.config.getint('Measurement', 'smq_now')
        self.smq_list.clear()
        self.smq_list = json.loads(self.config.get('Measurement', 'smq_list'))
        self.VcL = self.config.getfloat('Measurement', 'VcL')
        self.VcM = self.config.getfloat('Measurement', 'VcM')
        self.VcS = self.config.getfloat('Measurement', 'VcS')
        self.VdLM = self.config.getfloat('Measurement', 'VdLM')
        self.VdS = self.config.getfloat('Measurement', 'VdS')
        self.spi_t = self.config.getint('Measurement', 'spi_t')
        self.spi_max_speed_hz = self.config.getint('Measurement', 'spi_max_speed_hz')
        self.pulse_length = self.config.getint('Measurement', 'pulse_length')
        self.Pmeas.clear()
        self.Pmeas = json.loads(self.config.get('Measurement', 'Pmeas'))
        self.pmeas_kPa_min = self.config.getfloat('Measurement', 'pmeas_kPa_min')
        self.pmeas_kPa_max = self.config.getfloat('Measurement', 'pmeas_kPa_max')
        self.pmeas_Bar_min = self.config.getfloat('Measurement', 'pmeas_Bar_min')
        self.pmeas_Bar_max = self.config.getfloat('Measurement', 'pmeas_Bar_max')
        self.pmeas_Psi_min = self.config.getfloat('Measurement', 'pmeas_Psi_min')
        self.pmeas_Psi_max = self.config.getfloat('Measurement', 'pmeas_Psi_max')
        self.Pmeas_now = float(self.Pmeas[self.pressure.value])


    """Метод возвращает номера портов для работы"""
    def get_ports(self):
        return self.p

    """Метод возвращает язык, выбранный для работы"""
    def get_language(self):
        return self.language

    """Метод возвращает True если программа запущена в тестовом режиме (по Windows)"""
    def is_test_mode(self):
        result = False
        if self.testMode == 1:
            result = True
        return result

    """Метод для сохранения измененных настроек в файл"""
    def set_ini(self, section, val, s):
        self.config.read('Configure.ini')
        self.config.set(section, val, s)
        with open("Configure.ini.new", "w") as fh:
            self.config.write(fh)
        os.rename("Configure.ini", "Configure.ini~")
        os.rename("Configure.ini.new", "Configure.ini")
        os.remove("Configure.ini~")

    """Метод для обновления списка всех доступных языков"""
    def reload_languages_list(self):
        self.languages.clear()
        if self.is_test_mode():
            self.languages = os.listdir(os.getcwd() + '\Language\\')
        if not self.is_test_mode():
            self.languages = os.listdir(os.getcwd() + '/Language/')


"""Enum допустимых единиц измерений Давления"""
class Pressure(Enum):
    kPa = 0
    Bar = 1
    Psi = 2

