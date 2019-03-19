#!/usr/bin/python
# Модуль для загрузки настроек приложения из Configure.ini
import configparser
import json
import os
from enum import Enum
from pathlib import Path

"""Проверака и комментари: 13.01.2019"""

"""
"Класс загружает и сохраняет все настройки в файл Config.ini
    self.p - Массив, в который будут загруженны технические данные по используемым портам.
    self.config - экземпляр модуля, который позволяет работать с ini файлами
    self.language - переменная, в которую будет загружена ссылка на файл с используемым языком
    self.round - количество знаков после запятой у измерений
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
        self.small_cuvette = False
        self.language = ''
        self.round = 3
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
        self.testMode = self.try_getint_user_config('TestMode', 'testMode')

    """Метод для назначения портам указанных в ini файле значений"""
    def set_ports(self):
        # [Ports]
        self.p[0] = self.try_getint_user_config('Ports', 'p1')
        self.p[1] = self.try_getint_user_config('Ports', 'p2')
        self.p[2] = self.try_getint_user_config('Ports', 'p3')
        self.p[3] = self.try_getint_user_config('Ports', 'p4')
        self.p[4] = self.try_getint_user_config('Ports', 'p5')

    """Метод для назначения языка программы согласно ini файлу"""
    def set_language(self):
        # [[Language]]
        self.language = self.try_get_user_config('Language', 'language')

    """Метод для загрузки данных из ini файла"""
    def set_measurement(self):
        self.pressure = Pressure(self.try_getint_user_config('Measurement', 'pressure'))
        self.small_cuvette = self.try_getboolean_user_config('Pycnometer', 'small_cuvette')
        self.smq_now = self.try_getint_user_config('Measurement', 'smq_now')
        self.smq_list.clear()
        self.smq_list = json.loads(self.try_get_user_config('Measurement', 'smq_list'))
        self.VcL = self.try_getfloat_user_config('Measurement', 'VcL')
        self.VcM = self.try_getfloat_user_config('Measurement', 'VcM')
        self.VcS = self.try_getfloat_user_config('Measurement', 'VcS')
        self.VdLM = self.try_getfloat_user_config('Measurement', 'VdLM')
        self.VdS = self.try_getfloat_user_config('Measurement', 'VdS')
        self.spi_t = self.try_getfloat_user_config('Measurement', 'spi_t')
        self.spi_max_speed_hz = self.try_getint_user_config('Measurement', 'spi_max_speed_hz')
        self.pulse_length = self.try_getint_user_config('Measurement', 'pulse_length')
        self.Pmeas.clear()
        self.Pmeas = json.loads(self.try_get_user_config('Measurement', 'Pmeas'))
        self.pmeas_kPa_min = self.try_getfloat_user_config('Measurement', 'pmeas_kPa_min')
        self.pmeas_kPa_max = self.try_getfloat_user_config('Measurement', 'pmeas_kPa_max')
        self.pmeas_Bar_min = self.try_getfloat_user_config('Measurement', 'pmeas_Bar_min')
        self.pmeas_Bar_max = self.try_getfloat_user_config('Measurement', 'pmeas_Bar_max')
        self.pmeas_Psi_min = self.try_getfloat_user_config('Measurement', 'pmeas_Psi_min')
        self.pmeas_Psi_max = self.try_getfloat_user_config('Measurement', 'pmeas_Psi_max')
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
        self.config.read('Configure_user.ini.new')
        self.config.set(section, val, s)
        with open("Configure_user.ini.new", "w") as fh:
            self.config.write(fh)
        if os.path.isfile('Configure_user.ini'):
            os.rename("Configure_user.ini", "Configure_user.ini~")
            os.rename("Configure_user.ini.new", "Configure_user.ini")
            os.remove("Configure_user.ini~")
        else:
            os.rename("Configure_user.ini.new", "Configure_user.ini")

    """Метод для обновления списка всех доступных языков"""
    def reload_languages_list(self):
        self.languages.clear()
        self.languages = os.listdir(Path(os.getcwd() + '/Language/'))
        # if self.is_test_mode():
        #     self.languages = os.listdir(os.getcwd() + '\Language\\')
        # if not self.is_test_mode():
        #     self.languages = os.listdir(os.getcwd() + '/Language/')
            
    def try_get_user_config(self, section, option):
        self.config.read('Configure.ini')
        result = self.config.get(section, option)
        if os.path.isfile('Configure_user.ini'):
            self.config.read('Configure_user.ini')
            if self.config.has_section(section):
                if self.config.has_option(section, option):
                    result = self.config.get(section, option)
        return result

    def try_getint_user_config(self, section, option):
        self.config.read('Configure.ini')
        result = self.config.getint(section, option)
        if os.path.isfile('Configure_user.ini'):
            self.config.read('Configure_user.ini')
            if self.config.has_section(section):
                if self.config.has_option(section, option):
                    result = self.config.getint(section, option)
        return result

    def try_getfloat_user_config(self, section, option):
        self.config.read('Configure.ini')
        result = self.config.getfloat(section, option)
        if os.path.isfile('Configure_user.ini'):
            self.config.read('Configure_user.ini')
            if self.config.has_section(section):
                if self.config.has_option(section, option):
                    result = self.config.getfloat(section, option)
        return result

    def try_getboolean_user_config(self, section, option):
        self.config.read('Configure.ini')
        result = self.config.getboolean(section, option)
        if os.path.isfile('Configure_user.ini'):
            self.config.read('Configure_user.ini')
            if self.config.has_section(section):
                if self.config.has_option(section, option):
                    result = self.config.getboolean(section, option)
        return result


"""Enum допустимых единиц измерений Давления"""
class Pressure(Enum):
    kPa = 0
    Bar = 1
    Psi = 2

