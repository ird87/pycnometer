#!/usr/bin/python
# -*- coding: utf-8 -*-

# Модуль для считывания данных с датчика, адаптированный для новой библиотеки 2025 года.

import inspect
import threading
import os
import xlwt
import time

# Импортируем новую библиотеку
# Предполагается, что файлы ADS1256.py и config.py находятся в папке SPI_Driver_2025
try:
    from SPI_Driver_2025 import ADS1256
    from SPI_Driver_2025 import config
except ImportError:
    print("Ошибка: Не удалось импортировать новую библиотеку SPI_Driver_2025.")
    print("Убедитесь, что папка 'SPI_Driver_2025' существует и содержит файлы 'ADS1256.py' и 'config.py'.")
    exit()

"""
Класс для работы с SPI с Raspberry Pi, использующий библиотеку 2025 года.
"""


class SPI(object):
    """docstring"""

    """Конструктор класса. Поля класса"""

    def __init__(self, main):
        self.main = main
        self.config = self.main.config
        self.t = 0
        self.const_data = 6300000
        self.p_channel = self.config.data_channel

        # Заведем переменную для массива каналов, измеряющих температуру.
        self.t_channels = []
        # Переберем каналы из настроек и добавим их в переменную.
        for t_channel in self.config.t_channels:
            # номер канала должен быть между 1 и 8 и он не должен повторяться.
            if 1 <= t_channel <= 8 and not (t_channel) in self.t_channels:
                self.t_channels.append(t_channel)

        # 1. Инициализация объекта АЦП с использованием новой библиотеки
        self.ads = ADS1256.ADS1256()
        # Инициализация модуля и проверка соединения
        if self.ads.ADS1256_init() == -1:
            raise RuntimeError("Не удалось инициализировать ADS1256. Проверьте подключение.")

        # 2. Самокалибровка усиления и смещения
        self.ads.ADS1256_WriteCmd(ADS1256.CMD['CMD_SELFCAL'])
        time.sleep(1)  # Даем время на калибровку

        self.smq_now = 0
        self.set_option()
        self.test_on = False
        self.file = os.path.basename(__file__)
        self.debug_log = self.main.debug_log
        self.measurement_log = self.main.measurement_log
        self.is_test_mode = self.main.config.is_test_mode
        self.message = self.main.set_pressure_message
        self.correct_data = self.main.config.correct_data

        self.create_xls_file()

    def set_correct_data(self, x):
        self.config.set_correct_data(x)
        self.correct_data = self.config.correct_data

    """Метод для применения настроек"""

    def set_option(self):
        self.test_on = False
        # Тест должен быть выключен для применения настроек.
        self.close_test()
        # Присваиваем значения.
        self.t = self.config.periodicity_of_removal_of_sensor_reading
        self.maximum_sensor_pressure = self.config.maximum_sensor_pressure
        self.smq_now = self.config.smq_now
        self.correct_data = self.config.correct_data

    """Метод для проверки. Возвращает True, если измерение давления запущено иначе False"""

    def is_test_on(self):
        return self.test_on

    """Метод для установки состояния переключателя работы измерения давления"""

    def set_test_on(self, s):
        self.test_on = s

    """Метод для запуска отдельного потока для измерения давления"""

    def start_test(self):
        p = self.get_pressure()
        # Проверяем, что измерение давления еще не запущено
        if not self.is_test_on():
            # Устанавливаем состояние в режим "запущена"
            self.set_test_on(True)
            self.my_thread = threading.Thread(target=self.implementation_test)
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Thread "Pressure measurement" started in the NORMAL MODE')
            self.my_thread.start()

    """Метод для выключения отдельного потока измерения"""

    def close_test(self):
        if self.is_test_on():
            self.set_test_on(False)
            if hasattr(self, 'my_thread'):
                self.my_thread.join()
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Thread "Pressure measurement" finished in the NORMAL MODE')

    """Метод, где расположена процедура обработки измерения давления в отдельном потоке"""

    def implementation_test(self):
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   f'Pressure measurement for Manual control started\n'
                                   f'self.t = {self.t}\nself.smq_now = {self.smq_now}')
        while self.test_on:
            p = self.get_pressure()
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       f'Pressure = {p}')
            self.message.emit(p)
            time.sleep(self.t)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Pressure measurement for Manual control finished')

    """Метод, где мы получаем данные с датчика (адаптирован под новую библиотеку)"""

    def read_channel(self):
        num_channels = 1 + len(self.t_channels)
        data = [0] * num_channels

        if self.smq_now == 0:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'smq_now is 0, division by zero avoided.')
            return data

        # делаем цикл по требуемому количеству замеров согласно config.ini
        for _ in range(self.smq_now):
            # 3. Получаем данные
            # Считываем канал давления
            data[0] += self.ads.ADS1256_GetChannalValue(self.p_channel)

            # Считываем каналы температуры
            for i, t_channel in enumerate(self.t_channels):
                data[i + 1] += self.ads.ADS1256_GetChannalValue(t_channel)

        # берем среднее значение
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculating average data.....')
        for i in range(len(data)):
            data[i] = data[i] / self.smq_now

        raw_pressure_data = data[0]
        if self.main.config.output_pt_to_xls:
            pressure_kpa = self.calc_pressure(raw_pressure_data)[0]
            self.save_p_xls(raw_pressure_data, pressure_kpa)

        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation data..... Done.')
        return data

    def create_xls_file(self):
        self.file = os.path.join(os.getcwd(), "temperature & pressure.xls")
        if os.path.isfile(self.file):
            os.remove(self.file)
        if self.main.config.output_pt_to_xls:
            self.wb = xlwt.Workbook(encoding='WINDOWS-1251')
            self.wb_style = xlwt.easyxf("align: horiz centre; borders: left thin, right thin, top thin, bottom thin;")
            self.wsp = self.wb.add_sheet(f"{time.strftime('%Y-%m-%d', time.localtime())} | pressure")
            self.wsp_row = 0
            self.wsp.write(self.wsp_row, 0, 'Data', self.wb_style)
            self.wsp.write(self.wsp_row, 1, 'P', self.wb_style)
            self.wst = self.wb.add_sheet(f"{time.strftime('%Y-%m-%d', time.localtime())} | temperature")
            self.wst_row = 0
            self.wst.write(self.wst_row, 0, 'Time', self.wb_style)
            self.wst.write(self.wst_row, 1, 'P', self.wb_style)
            for i in range(4):  # Предполагаем до 4 датчиков температуры
                self.wst.write(self.wst_row, i + 2, f'T{i + 1}', self.wb_style)
            self.wb.save(self.file)

    def save_t_xls(self, p, t):
        if self.main.config.output_pt_to_xls:
            self.wst_row += 1
            self.wst.write(self.wst_row, 0, time.strftime("%H:%M:%S", time.localtime()), self.wb_style)
            self.wst.write(self.wst_row, 1, str(p), self.wb_style)
            for i in range(len(t)):
                self.wst.write(self.wst_row, i + 2, str(t[i]), self.wb_style)
            self.wb.save(self.file)

    def save_p_xls(self, data, p):
        if self.main.config.output_pt_to_xls:
            self.wsp_row += 1
            self.wsp.write(self.wsp_row, 0, str(data), self.wb_style)
            self.wsp.write(self.wsp_row, 1, str(p), self.wb_style)
            self.wb.save(self.file)

    """Метод рассчета давления на основание данных с датчика"""

    def calc_pressure(self, data_p):
        p1 = self.getkPa(data_p)
        p2 = self.getBar(data_p)
        p3 = self.getPsi(data_p)
        return [p1, p2, p3]

    def calc_temperature(self, data_t):
        result = []
        for _data_t in data_t:
            t = _data_t * 1  # Здесь должен быть ваш коэффициент для расчета температуры
            result.append(t)
        return result

    """Метод для получения давления с датчика"""

    def get_pressure(self, crutch="p"):
        data = self.read_channel()
        result = data[0] - self.correct_data
        _p = self.calc_pressure(result)
        p = _p[self.config.pressure.value]

        if len(self.t_channels) > 0:
            data_t = data[1:]  # Все элементы после первого
            t = self.calc_temperature(data_t)
            self.save_t_xls(p, t)

        return p

    """Метод, который на основание измерения высчитывает давление в кПа"""

    def getkPa(self, data):
        return data / self.const_data * self.maximum_sensor_pressure

    """Метод, который на основание измерения высчитывает давление в Бар"""

    def getBar(self, data):
        return data / self.const_data * self.maximum_sensor_pressure * 0.01

    """Метод, который на основание измерения высчитывает давление в psi"""

    def getPsi(self, data):
        return data / self.const_data * self.maximum_sensor_pressure * 0.14503773773

    """Метод, который возвращает из давление в кПа значение измерения"""

    def getDataFromkPa(self, p):
        return p * self.const_data / self.maximum_sensor_pressure

    """Метод, который возвращает из давление в Бар значение измерения"""

    def getDataFromBar(self, p):
        return p * self.const_data / self.maximum_sensor_pressure / 0.01

    """Метод, который возвращает из давление в psi значение измерения"""

    def getDataFromPsi(self, p):
        return p * self.const_data / self.maximum_sensor_pressure / 0.14503773773
