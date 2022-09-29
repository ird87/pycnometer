#!/usr/bin/python
# Модуль для загрузки настроек приложения из Configure.ini
import configparser
import json
import os
from enum import Enum
from cryptography.fernet import Fernet
from version import version

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
    self.correct_data - поправка для датчика, рассчитывается при стартовой калибровке
    self.Pmeas_now  - давление, которое должен набрать прибор для текущей ед. измерения
    self.Pmeas - список для всех ед. измерений 
    pmeas_kPa_min - минимальный допуск для давления в кПа
    pmeas_kPa_max - максимальный допуск для давления в кПа
    pmeas_Bar_min - минимальный допуск для давления в Бар
    pmeas_Bar_max - максимальный допуск для давления в Бар
    pmeas_Psi_min - минимальный допуск для давления в psi
    pmeas_Psi_max - максимальный допуск для давления в psi
    self.periodicity_of_removal_of_sensor_reading - сколько секунд пауза между замерами давления в Ручном управлении
    self.spi_max_speed_hz - максимальная скорость получения данных с датчика в модуле SPI
    self.languages - список всех доступных языков
    self.testMode - переменная определяющая запушена ли программа в тестовом режиме 
                                                                        [0 - нет, в нормальном | 1 - да, в тестовом]
"""


class Configure(object):
    """Конструктор класса. Поля класса"""

    def __init__(self):

        # configparsers
        self.config_application = configparser.ConfigParser()  # Создаем экземпляр configparser
        self.config_device_file = os.path.join('conf', 'Configure_device.ini')
        self.config_application_file = os.path.join('conf', 'Configure_application.ini')
        self.config_user_file = os.path.join('conf', 'Configure_user.ini')
        self.config_device = configparser.ConfigParser()  # Создаем экземпляр configparser
        self.config_application.read(self.config_application_file, encoding='utf-8')  # Указываем файл для считывания данных
        self.config_user = configparser.ConfigParser()  # Создаем экземпляр configparser

        # cryptography
        # Fernet.generate_key()
        key = b'nRDnYgvD1i727JwjmwE_SRn30ktYZeLHIHuVPxo_tSw='
        self.cipher_suite = Fernet(key)

        # [DEVICE CONFIG]
        # [Pycnometer]
        self.model = 'Тестовый пикнометр'
        self.small_cuvette = False
        self.module_spi = ""
        self.data_channel = 2
        self.t_channels = []
        self.maximum_sensor_pressure = 101
        # [Measurement]
        self.spi_max_speed_hz = 1000000
        self.VcL = 60
        self.VcM = 40
        self.VcS = 20
        self.VdLM = 20
        self.VdS = 10
        self.correct_data = 0
        self.let_out_pressure_duration = 60
        # [Ports]
        self.v = [Valve(31, 32), Valve(35, 36), Valve(37, 38), Valve(11, 12), Valve(15, 16)]
        # [TestMode]
        self.testMode = True
        self.output_pt_to_xls = False

        # [APPLICATIONS CONFIG]
        # [Pycnometer]
        self.version = version
        # [Language]
        self.language = 'Russian'
        # [Measurement]
        self.pressure = Pressure.kPa
        self.round = 3
        self.periodicity_of_removal_of_sensor_reading = 0.75
        self.smq_list = [100, 500, 1000, 2000, 3000, 5000, 7500, 10000, 50000, 100000]
        self.smq_now = 3000
        self.pulse_length = 2
        self.Pmeas = [90, 0.90, 13.1]
        self.pmeas_kpa_min = 90
        self.pmeas_kpa_max = 110
        self.pmeas_bar_min = 0.9
        self.pmeas_bar_max = 1.1
        self.pmeas_psi_min = 13
        self.pmeas_psi_max = 16
        # [ManualControl]
        self.leak_test_when_starting = False
        self.calibrate_sensor_when_starting = True
        # [ReportSetup]
        self.report_measurement_table = True
        self.report_header = ""
        self.report_footer = ""
        # [SavingResult]
        self.save_to_flash_drive = False
        self.send_report_to_mail = True
        self.email_address = ""
        self.wifi_name = ""
        self.wifi_pass = ""

        self.languages = []

        # Загружаем данные прибора
        self.load_device_config()
        self.save_device_config()

    """Метод для назначения портам указанных в ini файле значений"""

    def set_ports(self):
        # [Ports]
        self.v[0] = self.try_get_device_config('Ports', 'V1', True).split("/")
        self.v[1] = self.try_get_device_config('Ports', 'V2', True).split("/")
        self.v[2] = self.try_get_device_config('Ports', 'V3', True).split("/")
        self.v[3] = self.try_get_device_config('Ports', 'V4', True).split("/")
        self.v[4] = self.try_get_device_config('Ports', 'V5', True).split("/")

    """Метод для назначения языка программы согласно ini файлу"""

    def set_language(self):
        # [[Language]]
        self.language = self.try_get_application_config('Language', 'language', True)

    def set_correct_data(self, x):
        self.correct_data = x
        self.set_ini('Measurement', 'correct_data', self.correct_data)

    def load_device_config(self):
        """загружаем все настройки из области прибора"""
        # [Pycnometer]
        self.model = self.try_get_device_config('Pycnometer', 'model', self.model)
        self.small_cuvette = self.try_getboolean_device_config('Pycnometer', 'small_cuvette', self.small_cuvette)
        self.module_spi = self.try_get_device_config('Pycnometer', 'module_spi', self.module_spi)
        self.data_channel = self.try_getint_device_config('Pycnometer', 'data_channel', self.data_channel)
        self.t_channels.clear()
        self.t_channels = json.loads(self.try_get_device_config('Pycnometer', 't_channels', self.t_channels))
        self.maximum_sensor_pressure = self.try_getint_device_config('Pycnometer', 'maximum_sensor_pressure', self.maximum_sensor_pressure)
        # [Measurement]
        self.spi_max_speed_hz = self.try_getint_device_config('Measurement', 'spi_max_speed_hz', self.spi_max_speed_hz)
        self.VcL = self.try_getfloat_device_config('Measurement', 'VcL', self.VcL)
        self.VcM = self.try_getfloat_device_config('Measurement', 'VcM', self.VcM)
        self.VcS = self.try_getfloat_device_config('Measurement', 'VcS', self.VcS)
        self.VdLM = self.try_getfloat_device_config('Measurement', 'VdLM', self.VdLM)
        self.VdS = self.try_getfloat_device_config('Measurement', 'VdS', self.VdS)
        self.correct_data = self.try_getint_device_config('Measurement', 'correct_data', self.correct_data)
        self.let_out_pressure_duration = self.try_getint_device_config('Measurement', 'let_out_pressure_duration', self.let_out_pressure_duration)
        # [Ports]
        self.set_ports()
        # [TestMode]
        self.testMode = self.try_getboolean_device_config('TestMode', 'testMode', self.testMode)
        self.output_pt_to_xls = self.try_getboolean_device_config('TestMode', 'output_pt_to_xls', self.output_pt_to_xls)

    def save_device_config(self):
        """Сохраняем все настройки из области прибора"""
        # [Pycnometer]
        self.set_device_ini('Pycnometer', 'model', self.model)
        self.set_device_ini('Pycnometer', 'small_cuvette', self.small_cuvette)
        self.set_device_ini('Pycnometer', 'module_spi', self.module_spi)
        self.set_device_ini('Pycnometer', 'data_channel', self.data_channel)
        self.set_device_ini('Pycnometer', 'model', self.model)
        self.set_device_ini('Pycnometer', 't_channels', '[{0}]'.format(", ".join(str(x) for x in self.t_channels)))
        self.set_device_ini('Pycnometer', 'maximum_sensor_pressure', self.maximum_sensor_pressure)
        # [Measurement]
        self.set_device_ini('Measurement', 'spi_max_speed_hz', self.spi_max_speed_hz)
        self.set_device_ini('Measurement', 'VcL', self.VcL)
        self.set_device_ini('Measurement', 'VcM', self.VcM)
        self.set_device_ini('Measurement', 'VcS', self.VcS)
        self.set_device_ini('Measurement', 'VdLM', self.VdLM)
        self.set_device_ini('Measurement', 'VdS', self.VdS)
        self.set_device_ini('Measurement', 'correct_data', self.correct_data)
        self.set_device_ini('Measurement', 'let_out_pressure_duration', self.let_out_pressure_duration)
        # [Ports]
        self.set_device_ini('Ports', 'V1', '{0}/{1}'.format(self.v[0].port_open, self.v[0].port_hold))
        self.set_device_ini('Ports', 'V2', '{0}/{1}'.format(self.v[1].port_open, self.v[1].port_hold))
        self.set_device_ini('Ports', 'V3', '{0}/{1}'.format(self.v[2].port_open, self.v[2].port_hold))
        self.set_device_ini('Ports', 'V4', '{0}/{1}'.format(self.v[3].port_open, self.v[3].port_hold))
        self.set_device_ini('Ports', 'V5', '{0}/{1}'.format(self.v[4].port_open, self.v[4].port_hold))
        # [TestMode]
        self.set_device_ini('TestMode', 'testMode', self.testMode)
        self.set_device_ini('TestMode', 'output_pt_to_xls', self.output_pt_to_xls)

    """Метод для загрузки данных из ini файла"""

    def load_application_config(self):
        # [Pycnometer]
        self.version = self.try_get_application_config('Pycnometer', 'version', False)
        # [Language]
        self.set_language()
        # [Measurement]
        self.pressure = Pressure(self.try_getint_application_config('Measurement', 'pressure', True))
        self.round = self.try_getint_application_config('Measurement', 'round', True)
        self.periodicity_of_removal_of_sensor_reading = self.try_getfloat_application_config('Measurement', 'periodicity_of_removal_of_sensor_reading', True)
        self.smq_list.clear()
        self.smq_list = json.loads(self.try_get_application_config('Measurement', 'smq_list', False))
        self.smq_now = self.try_getint_application_config('Measurement', 'smq_now', True)
        self.pulse_length = self.try_getint_application_config('Measurement', 'pulse_length', True)
        self.Pmeas.clear()
        self.Pmeas = json.loads(self.try_get_application_config('Measurement', 'Pmeas', True))
        self.pmeas_kpa_min = self.try_getfloat_application_config('Measurement', 'pmeas_kPa_min', False)
        self.pmeas_kpa_max = self.try_getfloat_application_config('Measurement', 'pmeas_kPa_max', False)
        self.pmeas_bar_min = self.try_getfloat_application_config('Measurement', 'pmeas_Bar_min', False)
        self.pmeas_bar_max = self.try_getfloat_application_config('Measurement', 'pmeas_Bar_max', False)
        self.pmeas_psi_min = self.try_getfloat_application_config('Measurement', 'pmeas_Psi_min', False)
        self.pmeas_psi_max = self.try_getfloat_application_config('Measurement', 'pmeas_Psi_max', False)
        # [ManualControl]
        self.leak_test_when_starting = self.try_getboolean_application_config('ManualControl', 'leak_test_when_starting', True)
        self.calibrate_sensor_when_starting = self.try_getboolean_application_config('ManualControl', 'calibrate_sensor_when_starting', True)
        # [ReportSetup]
        self.report_measurement_table = self.try_getboolean_application_config('ReportSetup', 'report_measurement_table', True)
        self.report_header = self.try_get_application_config('ReportSetup', 'report_header', True)
        self.report_footer = self.try_get_application_config('ReportSetup', 'report_footer', True)
        # [SavingResult]
        self.save_to_flash_drive = self.try_getboolean_application_config('SavingResult', 'save_to_flash_drive', True)
        self.send_report_to_mail = self.try_getboolean_application_config('SavingResult', 'send_report_to_mail', True)
        self.email_address = self.try_get_application_config_hash('SavingResult', 'email_address', True)
        self.wifi_name = self.try_get_application_config_hash('SavingResult', 'wifi_name', True)
        self.wifi_pass = self.try_get_application_config_hash('SavingResult', 'wifi_pass', True)

    def save_application_config(self):
        # [Pycnometer]
        self.version = self.try_get_application_config('Pycnometer', 'version', False)
        # [Language]
        self.set_language()
        # [Measurement]
        self.pressure = Pressure(self.try_getint_application_config('Measurement', 'pressure', True))
        self.round = self.try_getint_application_config('Measurement', 'round', True)
        self.periodicity_of_removal_of_sensor_reading = self.try_getfloat_application_config('Measurement', 'periodicity_of_removal_of_sensor_reading', True)
        self.smq_list.clear()
        self.smq_list = json.loads(self.try_get_application_config('Measurement', 'smq_list', False))
        self.smq_now = self.try_getint_application_config('Measurement', 'smq_now', True)
        self.pulse_length = self.try_getint_application_config('Measurement', 'pulse_length', True)
        self.Pmeas.clear()
        self.Pmeas = json.loads(self.try_get_application_config('Measurement', 'Pmeas', True))
        self.pmeas_kpa_min = self.try_getfloat_application_config('Measurement', 'pmeas_kPa_min', False)
        self.pmeas_kpa_max = self.try_getfloat_application_config('Measurement', 'pmeas_kPa_max', False)
        self.pmeas_bar_min = self.try_getfloat_application_config('Measurement', 'pmeas_Bar_min', False)
        self.pmeas_bar_max = self.try_getfloat_application_config('Measurement', 'pmeas_Bar_max', False)
        self.pmeas_psi_min = self.try_getfloat_application_config('Measurement', 'pmeas_Psi_min', False)
        self.pmeas_psi_max = self.try_getfloat_application_config('Measurement', 'pmeas_Psi_max', False)
        # [ManualControl]
        self.leak_test_when_starting = self.try_getboolean_application_config('ManualControl', 'leak_test_when_starting', True)
        self.calibrate_sensor_when_starting = self.try_getboolean_application_config('ManualControl', 'calibrate_sensor_when_starting', True)
        # [ReportSetup]
        self.report_measurement_table = self.try_getboolean_application_config('ReportSetup', 'report_measurement_table', True)
        self.report_header = self.try_get_application_config('ReportSetup', 'report_header', True)
        self.report_footer = self.try_get_application_config('ReportSetup', 'report_footer', True)
        # [SavingResult]
        self.save_to_flash_drive = self.try_getboolean_application_config('SavingResult', 'save_to_flash_drive', True)
        self.send_report_to_mail = self.try_getboolean_application_config('SavingResult', 'send_report_to_mail', True)
        self.email_address = self.try_get_application_config_hash('SavingResult', 'email_address', True)
        self.wifi_name = self.try_get_application_config_hash('SavingResult', 'wifi_name', True)
        self.wifi_pass = self.try_get_application_config_hash('SavingResult', 'wifi_pass', True)

    def get_ports(self):
        """Метод возвращает номера портов для работы"""
        return self.v

    def get_language(self):
        """Метод возвращает язык, выбранный для работы"""
        return self.language

    def is_test_mode(self):
        """Метод возвращает True если программа запущена в тестовом режиме (по Windows)"""
        result = False
        if self.testMode == 1:
            result = True
        return result

    def set_ini(self, section, val, s):
        """Метод для сохранения измененных настроек в файл"""
        s = str(s)
        self.config_user.read(self.config_user_file + '.new', encoding='utf-8')
        if not self.config_user.has_section(section):
            self.config_user.add_section(section)
        self.config_user.set(section, val, s)
        with open(self.config_user_file + ".new", "w", encoding='utf-8') as fh:
            self.config_user.write(fh)
        if os.path.isfile(self.config_user_file):
            os.rename(self.config_user_file, self.config_user_file + "~")
            os.rename(self.config_user_file + ".new", self.config_user_file)
            os.remove(self.config_user_file + "~")
        else:
            os.rename(self.config_user_file + ".new", self.config_user_file)

    def set_ini_hash(self, section, val, s):
        """Метод для сохранения измененных настроек в файл"""
        s = str(s)
        s = (self.crypting(s)).decode('utf-8')
        self.config_user.read(self.config_user_file + '.new', encoding='utf-8')
        if not self.config_user.has_section(section):
            self.config_user.add_section(section)
        self.config_user.set(section, val, s)
        with open(self.config_user_file + ".new", "w", encoding='utf-8') as fh:
            self.config_user.write(fh)
        if os.path.isfile(self.config_user_file):
            os.rename(self.config_user_file, self.config_user_file + "~")
            os.rename(self.config_user_file + ".new", self.config_user_file)
            os.remove(self.config_user_file + "~")
        else:
            os.rename(self.config_user_file + ".new", self.config_user_file)

    """Метод для обновления списка всех доступных языков"""

    def reload_languages_list(self):
        self.languages.clear()
        self.languages = os.listdir(os.path.join(os.getcwd(), 'Language'))
        # if self.is_test_mode():
        #     self.languages = os.listdir(os.getcwd() + '\Language\\')
        # if not self.is_test_mode():
        #     self.languages = os.listdir(os.getcwd() + '/Language/')

    def try_get_application_config(self, section, option, user_config):
        self.config_application.read(self.config_application_file, encoding='utf-8')
        result = self.config_application.get(section, option)
        if os.path.isfile(self.config_user_file) and user_config:
            self.config_user.read(self.config_user_file, encoding='utf-8')
            if self.config_user.has_section(section):
                if self.config_user.has_option(section, option):
                    result = self.config_user.get(section, option)
        return result

    def try_getint_application_config(self, section, option, user_config):
        self.config_application.read(self.config_application_file, encoding='utf-8')
        result = self.config_application.getint(section, option)
        if os.path.isfile(self.config_user_file) and user_config:
            self.config_user.read(self.config_user_file, encoding='utf-8')
            if self.config_user.has_section(section):
                if self.config_user.has_option(section, option):
                    result = self.config_user.getint(section, option)
        return result

    def try_getfloat_application_config(self, section, option, user_config):
        self.config_application.read(self.config_application_file, encoding='utf-8')
        result = self.config_application.getfloat(section, option)
        if os.path.isfile(self.config_user_file) and user_config:
            self.config_user.read(self.config_user_file, encoding='utf-8')
            if self.config_user.has_section(section):
                if self.config_user.has_option(section, option):
                    result = self.config_user.getfloat(section, option)
        return result

    def try_getboolean_application_config(self, section, option, user_config):
        self.config_application.read(self.config_application_file, encoding='utf-8')
        result = self.config_application.getboolean(section, option)
        if os.path.isfile(self.config_user_file) and user_config:
            self.config_user.read(self.config_user_file, encoding='utf-8')
            if self.config_user.has_section(section):
                if self.config_user.has_option(section, option):
                    result = self.config_user.getboolean(section, option)
        return result

    def try_get_application_config_hash(self, section, option, user_config):
        self.config_application.read(self.config_application_file, encoding='utf-8')
        result = self.config_application.get(section, option)
        if os.path.isfile(self.config_user_file) and user_config:
            self.config_user.read(self.config_user_file, encoding='utf-8')
            if self.config_user.has_section(section):
                if self.config_user.has_option(section, option):
                    result = self.config_user.get(section, option)
        if not result == "":
            result = (self.cipher_suite.decrypt(bytes(result, encoding='utf-8'))).decode('utf-8')
        return result

    """Метод для сохранения измененных настроек в файл"""

    def set_device_ini(self, section, val, s):
        s = str(s)
        self.config_device.read(self.config_device_file + '.new', encoding='utf-8')
        if not self.config_device.has_section(section):
            self.config_device.add_section(section)
        self.config_device.set(section, val, s)
        with open(self.config_device_file + ".new", "w", encoding='utf-8') as fh:
            self.config_device.write(fh)
        if os.path.isfile(self.config_device_file):
            os.rename(self.config_device_file, self.config_device_file + "~")
            os.rename(self.config_device_file + ".new", self.config_device_file)
            os.remove(self.config_device_file + "~")
        else:
            os.rename(self.config_device_file + ".new", self.config_device_file)

    """Метод для сохранения измененных настроек в файл"""

    def set_device_ini_hash(self, section, val, s):
        s = str(s)
        s = (self.crypting(s)).decode('utf-8')
        self.config_device.read(self.config_device_file + '.new', encoding='utf-8')
        if not self.config_device.has_section(section):
            self.config_device.add_section(section)
        self.config_device.set(section, val, s)
        with open(self.config_device_file + ".new", "w", encoding='utf-8') as fh:
            self.config_device.write(fh)
        if os.path.isfile(self.config_device_file):
            os.rename(self.config_device_file, self.config_device_file + "~")
            os.rename(self.config_device_file + ".new", self.config_device_file)
            os.remove(self.config_device_file + "~")
        else:
            os.rename(self.config_device_file + ".new", self.config_device_file)

    def try_get_device_config(self, section, option, default):
        if not os.path.isfile(self.config_device_file) or not self.config_device.has_section(section) or not self.config_device.has_option(section, option): return default
        self.config_device.read(self.config_device_file, encoding='utf-8')
        result = self.config_device.get(section, option)
        return result

    def try_getint_device_config(self, section, option, default):
        if not os.path.isfile(self.config_device_file) or not self.config_device.has_section(section) or not self.config_device.has_option(section, option): return default
        self.config_device.read(self.config_device_file, encoding='utf-8')
        result = self.config_device.getint(section, option)
        return result

    def try_getfloat_device_config(self, section, option, default):
        if not os.path.isfile(self.config_device_file) or not self.config_device.has_section(section) or not self.config_device.has_option(section, option): return default
        self.config_device.read(self.config_device_file, encoding='utf-8')
        result = self.config_device.getfloat(section, option)
        return result

    def try_getboolean_device_config(self, section, option, default):
        if not os.path.isfile(self.config_device_file) or not self.config_device.has_section(section) or not self.config_device.has_option(section, option): return default
        self.config_device.read(self.config_device_file, encoding='utf-8')
        result = self.config_device.getboolean(section, option)
        print(result)
        return result

    def try_get_device_config_hash(self, section, option, default):
        if not os.path.isfile(self.config_device_file) or not self.config_device.has_section(section) or not self.config_device.has_option(section, option): return default
        self.config_device.read(self.config_device_file, encoding='utf-8')
        result = self.config_device.get(section, option)
        if not result == "":
            result = (self.cipher_suite.decrypt(bytes(result, encoding='utf-8'))).decode('utf-8')
        return result

    def crypting(self, text):
        encrypted_text = self.cipher_suite.encrypt(bytes(text, encoding='utf-8'))
        return encrypted_text


class Valve(object):
    """Ports for open valve and hold open"""

    def __init__(self, port_open=0, port_hold=0):
        self.port_open = port_open
        self.port_hold = port_hold

    def set_ports(self, ports):
        self.port_open = ports[0]
        self.port_hold = ports[1]


class Pressure(Enum):
    """Enum допустимых единиц измерений Давления"""
    kPa = 0
    Bar = 1
    Psi = 2
