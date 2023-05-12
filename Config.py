#!/usr/bin/python
# Модуль для загрузки настроек приложения из Configure.ini
import configparser
import json
import os
import helper
from enum import Enum
from cryptography.fernet import Fernet

from MeasurementProcedure import Cuvette
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


def fix_ownership(path):
    """Change the owner of the file to SUDO_UID"""

    uid = os.environ.get('SUDO_UID')
    gid = os.environ.get('SUDO_GID')
    if uid is not None:
        os.chown(path, int(uid), int(gid))


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
        self.wait_before_hold = 0.06
        self.maximum_sensor_pressure = 101
        # [Measurement]
        self.spi_max_speed_hz = 1000000
        self.vc_large = 60
        self.vc_medium = 40
        self.vc_small = 20
        self.vd_large_and_medium = 20
        self.vd_small = 10
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
        self.pmeas = [90, 0.90, 13.1]
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
        self.v[0].set_ports(self.try_get_device_config('Ports', 'V1', '{0}/{1}'.format(self.v[0].port_open, self.v[0].port_hold)).split("/"))
        self.v[1].set_ports(self.try_get_device_config('Ports', 'V2', '{0}/{1}'.format(self.v[1].port_open, self.v[1].port_hold)).split("/"))
        self.v[2].set_ports(self.try_get_device_config('Ports', 'V3', '{0}/{1}'.format(self.v[2].port_open, self.v[2].port_hold)).split("/"))
        self.v[3].set_ports(self.try_get_device_config('Ports', 'V4', '{0}/{1}'.format(self.v[3].port_open, self.v[3].port_hold)).split("/"))
        self.v[4].set_ports(self.try_get_device_config('Ports', 'V5', '{0}/{1}'.format(self.v[4].port_open, self.v[4].port_hold)).split("/"))

    """Метод для назначения языка программы согласно ini файлу"""

    def set_language(self):
        # [[Language]]
        self.language = self.try_get_application_config('Language', 'language', True)

    def set_correct_data(self, x):
        self.correct_data = x
        self.set_ini('Measurement', 'correct_data', self.correct_data)

    def set_pmeas(self, p_kpa, p_bar, p_psi):
        """Pressure to be applied to the device"""
        print(p_kpa, p_bar, p_psi)
        self.pmeas = [int(p_kpa), float(p_bar), float(p_psi)]

    def calibration_save(self, cuvette, vc, vd):
        if cuvette == Cuvette.Large.value:
            self.vc_large = helper.to_fixed(vc, self.round)
            self.set_device_ini('Measurement', 'VcL', self.vc_large)
            self.vd_large_and_medium = helper.to_fixed(vd, self.round)
            self.set_device_ini('Measurement', 'VdLM', self.vd_large_and_medium)
        if cuvette == Cuvette.Medium.value:
            self.vc_medium = helper.to_fixed(vc, self.round)
            self.set_device_ini('Measurement', 'VcM', self.vc_large)
            self.vd_large_and_medium = helper.to_fixed(vd, self.round)
            self.set_device_ini('Measurement', 'VdLM', self.vd_large_and_medium)
        if cuvette == Cuvette.Small.value:
            self.vc_small = helper.to_fixed(vc, self.round)
            self.set_device_ini('Measurement', 'VcS', self.vc_large)
            self.vd_small = helper.to_fixed(vd, self.round)
            self.set_device_ini('Measurement', 'VdS', self.vd_large_and_medium)

    def load_device_config(self):
        """загружаем все настройки из области прибора"""
        # [Pycnometer]
        self.model = self.try_get_device_config('Pycnometer', 'model', self.model)
        self.small_cuvette = self.try_getboolean_device_config('Pycnometer', 'small_cuvette', self.small_cuvette)
        self.module_spi = self.try_get_device_config('Pycnometer', 'module_spi', self.module_spi)
        self.data_channel = self.try_getint_device_config('Pycnometer', 'data_channel', self.data_channel)
        self.t_channels.clear()
        self.t_channels = json.loads(self.try_get_device_config('Pycnometer', 't_channels', '[{0}]'.format(", ".join(str(x) for x in self.t_channels))))
        self.wait_before_hold = self.try_getfloat_device_config('Pycnometer', 'wait_before_hold', self.wait_before_hold)
        self.maximum_sensor_pressure = self.try_getint_device_config('Pycnometer', 'maximum_sensor_pressure', self.maximum_sensor_pressure)
        # [Measurement]
        self.spi_max_speed_hz = self.try_getint_device_config('Measurement', 'spi_max_speed_hz', self.spi_max_speed_hz)
        self.vc_large = self.try_getfloat_device_config('Measurement', 'VcL', self.vc_large)
        self.vc_medium = self.try_getfloat_device_config('Measurement', 'VcM', self.vc_medium)
        self.vc_small = self.try_getfloat_device_config('Measurement', 'VcS', self.vc_small)
        self.vd_large_and_medium = self.try_getfloat_device_config('Measurement', 'VdLM', self.vd_large_and_medium)
        self.vd_small = self.try_getfloat_device_config('Measurement', 'VdS', self.vd_small)
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
        self.set_device_ini('Pycnometer', 'wait_before_hold', self.wait_before_hold)
        self.set_device_ini('Pycnometer', 'maximum_sensor_pressure', self.maximum_sensor_pressure)
        # [Measurement]
        self.set_device_ini('Measurement', 'spi_max_speed_hz', self.spi_max_speed_hz)
        self.set_device_ini('Measurement', 'VcL', self.vc_large)
        self.set_device_ini('Measurement', 'VcM', self.vc_medium)
        self.set_device_ini('Measurement', 'VcS', self.vc_small)
        self.set_device_ini('Measurement', 'VdLM', self.vd_large_and_medium)
        self.set_device_ini('Measurement', 'VdS', self.vd_small)
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
        self.round = self.try_getint_application_config('Measurement', 'round', False)
        self.periodicity_of_removal_of_sensor_reading = self.try_getfloat_application_config('Measurement', 'periodicity_of_removal_of_sensor_reading', True)
        self.smq_list.clear()
        self.smq_list = json.loads(self.try_get_application_config('Measurement', 'smq_list', False))
        self.smq_now = self.try_getint_application_config('Measurement', 'smq_now', True)
        self.pulse_length = self.try_getint_application_config('Measurement', 'pulse_length', True)
        self.pmeas.clear()
        self.pmeas = json.loads(self.try_get_application_config('Measurement', 'Pmeas', True))
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
        # [Language]
        self.set_ini('Language', 'language', self.language)
        # [Measurement]
        self.set_ini('Measurement', 'pressure', self.pressure.value)
        self.set_ini('Measurement', 'periodicity_of_removal_of_sensor_reading', self.periodicity_of_removal_of_sensor_reading)
        self.set_ini('Measurement', 'smq_now', self.smq_now)
        self.set_ini('Measurement', 'pulse_length', self.pulse_length)
        self.set_ini('Measurement', 'Pmeas', '[{0}, {1}, {2}]'.format(self.pmeas[0], self.pmeas[1], self.pmeas[2]))
        # [ManualControl]
        self.set_ini('ManualControl', 'leak_test_when_starting', self.leak_test_when_starting)
        self.set_ini('ManualControl', 'calibrate_sensor_when_starting', self.calibrate_sensor_when_starting)
        # [ReportSetup]
        self.set_ini('ReportSetup', 'report_measurement_table', self.report_measurement_table)
        self.set_ini('ReportSetup', 'report_header', self.report_header)
        self.set_ini('ReportSetup', 'report_footer', self.report_footer)
        # [SavingResult]
        self.set_ini('SavingResult', 'save_to_flash_drive', self.save_to_flash_drive)
        self.set_ini('SavingResult', 'send_report_to_mail', self.send_report_to_mail)
        self.set_ini_hash('SavingResult', 'email_address', self.email_address)
        self.set_ini_hash('SavingResult', 'wifi_name', self.wifi_name)
        self.set_ini_hash('SavingResult', 'wifi_pass', self.wifi_pass)

    def get_valves(self):
        """Метод возвращает номера портов для клапанов"""
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
        fix_ownership(self.config_user_file)

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
        fix_ownership(self.config_user_file)

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
        fix_ownership(self.config_device_file)

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
        fix_ownership(self.config_device_file)

    def try_get_device_config(self, section, option, default):
        result = default
        if os.path.isfile(self.config_device_file):
            self.config_device.read(self.config_device_file, encoding='utf-8')
            if self.config_device.has_section(section) and self.config_device.has_option(section, option):
                result = self.config_device.get(section, option)
        return result

    def try_getint_device_config(self, section, option, default):
        result = default
        if os.path.isfile(self.config_device_file):
            self.config_device.read(self.config_device_file, encoding='utf-8')
            if self.config_device.has_section(section) and self.config_device.has_option(section, option):
                result = self.config_device.getint(section, option)
        return result

    def try_getfloat_device_config(self, section, option, default):
        result = default
        if os.path.isfile(self.config_device_file):
            self.config_device.read(self.config_device_file, encoding='utf-8')
            if self.config_device.has_section(section) and self.config_device.has_option(section, option):
                result = self.config_device.getfloat(section, option)
        return result

    def try_getboolean_device_config(self, section, option, default):
        result = default
        if os.path.isfile(self.config_device_file):
            self.config_device.read(self.config_device_file, encoding='utf-8')
            if self.config_device.has_section(section) and self.config_device.has_option(section, option):
                result = self.config_device.getboolean(section, option)
        return result

    def try_get_device_config_hash(self, section, option, default):
        result = default
        if os.path.isfile(self.config_device_file):
            self.config_device.read(self.config_device_file, encoding='utf-8')
            if self.config_device.has_section(section) and self.config_device.has_option(section, option):
                result = self.config_device.get(section, option)
                if not result == "":
                    result = (self.cipher_suite.decrypt(bytes(result, encoding='utf-8'))).decode('utf-8')
                else:
                    result = default
        return result

    def crypting(self, text):
        encrypted_text = self.cipher_suite.encrypt(bytes(text, encoding='utf-8'))
        return encrypted_text


class Valve(object):
    """Ports for open valve and hold open"""

    def __init__(self, port_open=0, port_hold=0):
        self.port_open = port_open
        self.port_hold = port_hold

    def __str__(self):
        return "{0}/{1}".format(self.port_open, self.port_hold)

    def __repr__(self):
        return self.__str__()

    def set_ports(self, ports):
        self.port_open = int(ports[0])
        self.port_hold = int(ports[1])

    def is_correct(self):
        return self.port_open != 0 and self.port_hold != 0


class Pressure(Enum):
    """Enum допустимых единиц измерений Давления"""
    kPa = 0
    Bar = 1
    Psi = 2
