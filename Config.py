#!/usr/bin/python
# Модуль для загрузки настроек приложения из Configure.ini
import configparser
import json
import os
from enum import Enum
from cryptography.fernet import Fernet

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
    self.spi_t - сколько секунд пауза между замерами давления в Ручном управлении
    self.spi_max_speed_hz - максимальная скорость получения данных с датчика в модуле SPI
    self.languages - список всех доступных языков
    self.testMode - переменная определяющая запушена ли программа в тестовом режиме 
                                                                        [0 - нет, в нормальном | 1 - да, в тестовом]
"""

class Configure(object):
    """Конструктор класса. Поля класса"""
    def __init__(self):
        
        # configparsers
        self.config_application = configparser.ConfigParser()   # Создаем экземпляр configparser
        self.config_device_file = os.path.join('conf','Configure_device.ini')
        self.config_application_file = os.path.join('conf','Configure_application.ini')        
        self.config_user_file = os.path.join('conf','Configure_user.ini')        
        self.config_device = configparser.ConfigParser()   # Создаем экземпляр configparser
        self.config_application.read(self.config_application_file, encoding = 'utf-8')           # Указываем файл для считывания данных
        self.config_user = configparser.ConfigParser()   # Создаем экземпляр configparser
        
        # cryptography
        # Fernet.generate_key()
        key = b'nRDnYgvD1i727JwjmwE_SRn30ktYZeLHIHuVPxo_tSw='
        self.cipher_suite = Fernet(key)

        # [DEVICE CONFIG]

        self.model = 'Тестовый пикнометр'
        self.let_out_pressure_duration = 60
        self.testMode = True
        self.output_pt_to_xls = False

        self.p = [0, 0, 0, 0, 0]                    # Массив для записи номеров портов
        self.small_cuvette = False
        self.language = ''
        self.version = ''
        
        self.round = 3
        self.pressure = Pressure.kPa
        self.smq_now = 0
        self.smq_list = []
        self.VcL = 0
        self.VcM = 0
        self.VcS = 0
        self.VdLM = 0
        self.VdS = 0
        self.module_spi = ""
        self.data_channel = 0
        self.t_channels = []
        self.maximum_sensor_pressure = 0
        self.pulse_length = 0
        self.correct_data = 0
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
        self.periodicity_of_removal_of_sensor_reading = 0
        self.leak_test_when_starting = False
        self.сalibrate_sensor_when_starting = True
        self.report_measurement_table = True
        self.report_header = ""
        self.report_footer = ""
        self.save_to_flash_drive = False
        self.send_report_to_mail = True
        self.email_adress = ""
        self.wifi_name = ""
        self.wifi_pass = ""
        

        # Загружаем данные из файла
        self.load_device_config()
        self.save_device_config()


        # [Ports]
        self.set_ports()
        
        

    """Метод для назначения портам указанных в ini файле значений"""
    def set_ports(self):
        # [Ports]
        self.p[0] = self.try_getint_user_config('Ports', 'p1', True)
        self.p[1] = self.try_getint_user_config('Ports', 'p2', True)
        self.p[2] = self.try_getint_user_config('Ports', 'p3', True)
        self.p[3] = self.try_getint_user_config('Ports', 'p4', True)
        self.p[4] = self.try_getint_user_config('Ports', 'p5', True)

    """Метод для назначения языка программы согласно ini файлу"""
    def set_language(self):
        # [[Language]]
        self.language = self.try_get_user_config('Language', 'language', True)

    def set_correct_data(self, x):
        self.correct_data = x
        self.set_ini('Measurement', 'correct_data', self.correct_data)

    def load_device_config(self):
        """загружаем все настройки из области прибора"""  
        self.model = self.try_get_device_config('Pycnometer', 'model', self.model)
        self.testMode = self.try_getboolean_device_config('TestMode', 'testMode', self.testMode)   
        self.output_pt_to_xls = self.try_getboolean_device_config('TestMode', 'output_pt_to_xls', self.output_pt_to_xls)
        self.let_out_pressure_duration= self.try_getint_device_config('Measurement', 'let_out_pressure_duration', self.let_out_pressure_duration)   

    def save_device_config(self):
        """Сохраняем все настройки из области прибора"""  
        self.set_device_ini('Pycnometer', 'model', self.model)
        self.set_device_ini('TestMode', 'testMode', self.testMode)
        self.set_device_ini('TestMode', 'output_pt_to_xls', self.output_pt_to_xls)
        self.set_device_ini('Measurement', 'let_out_pressure_duration', self.let_out_pressure_duration)

    """Метод для загрузки данных из ini файла"""
    def set_measurement(self):

        self.pressure = Pressure(self.try_getint_user_config('Measurement', 'pressure', True))
        self.small_cuvette = self.try_getboolean_user_config('Pycnometer', 'small_cuvette', False)
        self.version = self.try_get_user_config('Pycnometer', 'version', False)
        self.module_spi = self.try_get_user_config('Pycnometer', 'module_spi', False)
        self.data_channel = self.try_getint_user_config('Pycnometer', 'data_channel', False)
        self.t_channels.clear()
        self.t_channels = json.loads(self.try_get_user_config('Pycnometer', 't_channels', True))
        self.maximum_sensor_pressure = self.try_getint_user_config('Pycnometer', 'maximum_sensor_pressure', False)
        self.smq_now = self.try_getint_user_config('Measurement', 'smq_now', True)
        self.smq_list.clear()
        self.smq_list = json.loads(self.try_get_user_config('Measurement', 'smq_list', False))
        self.VcL = self.try_getfloat_user_config('Measurement', 'VcL', True)
        self.VcM = self.try_getfloat_user_config('Measurement', 'VcM', True)
        self.VcS = self.try_getfloat_user_config('Measurement', 'VcS', True)
        self.VdLM = self.try_getfloat_user_config('Measurement', 'VdLM', True)
        self.VdS = self.try_getfloat_user_config('Measurement', 'VdS', True)
        self.spi_t = self.try_getfloat_user_config('Measurement', 'spi_t', True)

        self.spi_max_speed_hz = self.try_getint_user_config('Measurement', 'spi_max_speed_hz', False)
        self.round = self.try_getint_user_config('Measurement', 'round', True)
        self.pulse_length = self.try_getint_user_config('Measurement', 'pulse_length', True)
        self.correct_data = self.try_getint_user_config('Measurement', 'correct_data', False)
        self.Pmeas.clear()
        self.Pmeas = json.loads(self.try_get_user_config('Measurement', 'Pmeas', True))
        self.pmeas_kPa_min = self.try_getfloat_user_config('Measurement', 'pmeas_kPa_min', False)
        self.pmeas_kPa_max = self.try_getfloat_user_config('Measurement', 'pmeas_kPa_max', False)
        self.pmeas_Bar_min = self.try_getfloat_user_config('Measurement', 'pmeas_Bar_min', False)
        self.pmeas_Bar_max = self.try_getfloat_user_config('Measurement', 'pmeas_Bar_max', False)
        self.pmeas_Psi_min = self.try_getfloat_user_config('Measurement', 'pmeas_Psi_min', False)
        self.pmeas_Psi_max = self.try_getfloat_user_config('Measurement', 'pmeas_Psi_max', False)
        self.Pmeas_now = float(self.Pmeas[self.pressure.value])
        self.periodicity_of_removal_of_sensor_reading = self.try_getfloat_user_config('ManualControl', 'periodicity_of_removal_of_sensor_reading', False)
        self.leak_test_when_starting = self.try_getboolean_user_config('ManualControl', 'leak_test_when_starting', True)
        self.сalibrate_sensor_when_starting = self.try_getboolean_user_config('ManualControl', 'сalibrate_sensor_when_starting', True)
        self.report_measurement_table = self.try_getboolean_user_config('ReportSetup', 'report_measurement_table', True )
        self.report_header = self.try_get_user_config('ReportSetup', 'report_header', True)
        self.report_footer = self.try_get_user_config('ReportSetup', 'report_footer', True)
        self.save_to_flash_drive = self.try_getboolean_user_config('SavingResult', 'save_to_flash_drive', True)
        self.send_report_to_mail = self.try_getboolean_user_config('SavingResult', 'send_report_to_mail', True)
        self.email_adress = self.try_get_user_config_hash('SavingResult', 'email_adress', True)
        self.wifi_name = self.try_get_user_config_hash('SavingResult', 'wifi_name', True)
        self.wifi_pass = self.try_get_user_config_hash('SavingResult', 'wifi_pass', True)



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
        s=str(s)
        self.config_user.read(self.config_user_file+'.new', encoding = 'utf-8')
        if not self.config_user.has_section(section):
            self.config_user.add_section(section)
        self.config_user.set(section, val, s)
        with open(self.config_user_file+".new", "w", encoding = 'utf-8') as fh:
            self.config_user.write(fh)
        if os.path.isfile(self.config_user_file):
            os.rename(self.config_user_file, self.config_user_file+"~")
            os.rename(self.config_user_file+".new", self.config_user_file)
            os.remove(self.config_user_file+"~")
        else:
            os.rename(self.config_user_file+".new", self.config_user_file)

    """Метод для сохранения измененных настроек в файл"""
    def set_ini_hash(self, section, val, s):
        s=str(s)
        s = (self.crypting(s)).decode('utf-8')
        self.config_user.read(config_user_file+'.new', encoding = 'utf-8')
        if not self.config_user.has_section(section):
            self.config_user.add_section(section)
        self.config_user.set(section, val, s)
        with open(self.config_user_file+".new", "w", encoding = 'utf-8') as fh:
            self.config_user.write(fh)
        if os.path.isfile(self.config_user_file):
            os.rename(self.config_user_file, self.config_user_file+"~")
            os.rename(self.config_user_file+".new", self.config_user_file)
            os.remove(self.config_user_file+"~")
        else:
            os.rename(self.config_user_file+".new", self.config_user_file)

    """Метод для обновления списка всех доступных языков"""
    def reload_languages_list(self):
        self.languages.clear()
        self.languages = os.listdir(os.path.join(os.getcwd(), 'Language'))
        # if self.is_test_mode():
        #     self.languages = os.listdir(os.getcwd() + '\Language\\')
        # if not self.is_test_mode():
        #     self.languages = os.listdir(os.getcwd() + '/Language/')
            
    def try_get_user_config(self, section, option, user_config):
        self.config_application.read(self.config_application_file, encoding = 'utf-8')
        result = self.config_application.get(section, option)
        if os.path.isfile(self.config_user_file) and user_config:
            self.config_user.read(self.config_user_file, encoding = 'utf-8')
            if self.config_user.has_section(section):
                if self.config_user.has_option(section, option):
                    result = self.config_user.get(section, option)
        return result

    def try_getint_user_config(self, section, option, user_config):
        self.config_application.read(self.config_application_file, encoding = 'utf-8')
        result = self.config_application.getint(section, option)
        if os.path.isfile(self.config_user_file) and user_config:
            self.config_user.read(self.config_user_file, encoding = 'utf-8')
            if self.config_user.has_section(section):
                if self.config_user.has_option(section, option):
                    result = self.config_user.getint(section, option)
        return result

    def try_getfloat_user_config(self, section, option, user_config):
        self.config_application.read(self.config_application_file, encoding = 'utf-8')
        result = self.config_application.getfloat(section, option)
        if os.path.isfile(self.config_user_file) and user_config:
            self.config_user.read(self.config_user_file, encoding = 'utf-8')
            if self.config_user.has_section(section):
                if self.config_user.has_option(section, option):
                    result = self.config_user.getfloat(section, option)
        return result

    def try_getboolean_user_config(self, section, option, user_config):
        self.config_application.read(self.config_application_file, encoding = 'utf-8')
        result = self.config_application.getboolean(section, option)
        if os.path.isfile(self.config_user_file) and user_config:
            self.config_user.read(self.config_user_file, encoding = 'utf-8')
            if self.config_user.has_section(section):
                if self.config_user.has_option(section, option):
                    result = self.config_user.getboolean(section, option)
        return result

    def try_get_user_config_hash(self, section, option, user_config):
        self.config_application.read(self.config_application_file, encoding = 'utf-8')
        result = self.config_application.get(section, option)
        if os.path.isfile(self.config_user_file) and user_config:
            self.config_user.read(self.config_user_file, encoding = 'utf-8')
            if self.config_user.has_section(section):
                if self.config_user.has_option(section, option):
                    result = self.config_user.get(section, option)
        if not result=="":
            result = (self.cipher_suite.decrypt(bytes(result, encoding='utf-8'))).decode('utf-8')
        return result

    """Метод для сохранения измененных настроек в файл"""
    def set_device_ini(self, section, val, s):
        s=str(s)
        self.config_device.read(self.config_device_file+'.new', encoding = 'utf-8')
        if not self.config_device.has_section(section):
            self.config_device.add_section(section)
        self.config_device.set(section, val, s)
        with open(self.config_device_file+".new", "w", encoding = 'utf-8') as fh:
            self.config_device.write(fh)
        if os.path.isfile(self.config_device_file):
            os.rename(self.config_device_file, self.config_device_file+"~")
            os.rename(self.config_device_file+".new", self.config_device_file)
            os.remove(self.config_device_file+"~")
        else:
            os.rename(self.config_device_file+".new", self.config_device_file)

    """Метод для сохранения измененных настроек в файл"""
    def set_device_ini_hash(self, section, val, s):
        s=str(s)
        s = (self.crypting(s)).decode('utf-8')
        self.config_device.read(config_device_file+'.new', encoding = 'utf-8')
        if not self.config_device.has_section(section):
            self.config_device.add_section(section)
        self.config_device.set(section, val, s)
        with open(self.config_device_file+".new", "w", encoding = 'utf-8') as fh:
            self.config_device.write(fh)
        if os.path.isfile(self.config_device_file):
            os.rename(self.config_device_file, self.config_device_file+"~")
            os.rename(self.config_device_file+".new", self.config_device_file)
            os.remove(self.config_device_file+"~")
        else:
            os.rename(self.config_device_file+".new", self.config_device_file)

    def try_get_device_config(self, section, option, default):
        if not os.path.isfile(self.config_device_file) or not self.config_device.has_section(section) or not self.config_device.has_option(section, option): return default
        self.config_device.read(self.config_device_file, encoding = 'utf-8')
        result = self.config_device.get(section, option)        
        return result

    def try_getint_device_config(self, section, option, default):
        if not os.path.isfile(self.config_device_file) or not self.config_device.has_section(section) or not self.config_device.has_option(section, option): return default
        self.config_device.read(self.config_device_file, encoding = 'utf-8')
        result = self.config_device.getint(section, option)
        return result

    def try_getfloat_device_config(self, section, option, default):
        if not os.path.isfile(self.config_device_file) or not self.config_device.has_section(section) or not self.config_device.has_option(section, option): return default
        self.config_device.read(self.config_device_file, encoding = 'utf-8')
        result = self.config_device.getfloat(section, option)
        return result

    def try_getboolean_device_config(self, section, option, default):
        if not os.path.isfile(self.config_device_file) or not self.config_device.has_section(section) or not self.config_device.has_option(section, option): return default
        self.config_device.read(self.config_device_file, encoding = 'utf-8')
        result = self.config_device.getboolean(section, option)
        print(result)
        return result

    def try_get_device_config_hash(self, section, option, default):
        if not os.path.isfile(self.config_device_file) or not self.config_device.has_section(section) or not self.config_device.has_option(section, option): return default
        self.config_device.read(self.config_device_file, encoding = 'utf-8')
        result = self.config_device.get(section, option)
        if not result=="":
            result = (self.cipher_suite.decrypt(bytes(result, encoding='utf-8'))).decode('utf-8')
        return result

    def crypting(self, text):
        encrypted_text = self.cipher_suite.encrypt(bytes(text, encoding='utf-8'))
        return encrypted_text


"""Enum допустимых единиц измерений Давления"""
class Pressure(Enum):
    kPa = 0
    Bar = 1
    Psi = 2

