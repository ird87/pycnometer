#!/usr/bin/python
# Модуль для считывания данных с датчика
import inspect
import os
import threading
import sys
import os
from ads1256_ADS1256_definitions import *
from ads1256_pipyadc import ADS1256

import time

### START EXAMPLE ###
################################################################################
###  STEP 0: CONFIGURE CHANNELS AND USE DEFAULT OPTIONS FROM CONFIG FILE: ###
#
# For channel code values (bitmask) definitions, see ADS1256_definitions.py.
# The values representing the negative and positive input pins connected to
# the ADS1256 hardware multiplexer must be bitwise OR-ed to form eight-bit
# values, which will later be sent to the ADS1256 MUX register. The register
# can be explicitly read and set via ADS1256.mux property, but here we define
# a list of differential channels to be input to the ADS1256.read_sequence()
# method which reads all of them one after another.
#
# ==> Each channel in this context represents a differential pair of physical
# input pins of the ADS1256 input multiplexer.
#
# ==> For single-ended measurements, simply select AINCOM as the negative input.
#
# AINCOM does not have to be connected to AGND (0V), but it is if the jumper
# on the Waveshare board is set.
#
# Input pin for the potentiometer on the Waveshare Precision ADC board:
POTI = POS_AIN0|NEG_AINCOM
# Light dependant resistor of the same board:
LDR  = POS_AIN1|NEG_AINCOM
# The other external input screw terminals of the Waveshare board:
EXT2, EXT3, EXT4 = POS_AIN2|NEG_AINCOM, POS_AIN3|NEG_AINCOM, POS_AIN4|NEG_AINCOM
EXT5, EXT6, EXT7 = POS_AIN5|NEG_AINCOM, POS_AIN6|NEG_AINCOM, POS_AIN7|NEG_AINCOM

# You can connect any pin as well to the positive as to the negative ADC input.
# The following reads the voltage of the potentiometer with negative polarity.
# The ADC reading should be identical to that of the POTI channel, but negative.
POTI_INVERTED = POS_AINCOM|NEG_AIN0

# For fun, connect both ADC inputs to the same physical input pin.
# The ADC should always read a value close to zero for this.
SHORT_CIRCUIT = POS_AIN0|NEG_AIN0

# Specify here an arbitrary length list (tuple) of arbitrary input channel pair
# eight-bit code values to scan sequentially from index 0 to last.
# Eight channels fit on the screen nicely for this example..
CH_SEQUENCE = (POTI, LDR, EXT2, EXT3, EXT4, EXT7, POTI_INVERTED, SHORT_CIRCUIT)
################################################################################

"""
"Класс для работы с SPI с Raspberry Pi"

"""

# Модуль для взаимодействия с Raspberry Pi
class SPI(object):
    """docstring"""

    """Конструктор класса. Поля класса"""
    def __init__(self, main):
        self.main = main
        self.config = self.main.config
        self.t = 0
        self.const_data = 8388607
        self.channal = 0

        ### STEP 1: Initialise ADC object using default configuration:
        # (Note1: See ADS1256_default_config.py, see ADS1256 datasheet)
        # (Note2: Input buffer on means limited voltage range 0V...3V for 5V supply)
        self.ads = ADS1256()

        ### STEP 2: Gain and offset self-calibration:
        self.ads.cal_self()

        self.smq_now = 0
        self.set_option()
        self.test_on = False
        self.file = os.path.basename(__file__)
        self.debug_log = self.main.debug_log
        self.measurement_log = self.main.measurement_log
        self.is_test_mode = self.main.config.is_test_mode
        self.message = self.main.set_pressure_message
        self.correct_data = 0

    def set_correct_data(self, x):
        self.correct_data = x

    """Метод для применения настроек"""
    def set_option(self):
        self.test_on = False
        # Тест должен быть выключен для применения настроек. Ситуации, когда настройки применяются, а он включен
        # быть не должно, но на всякий случай мы явно вызовем его выключение.
        self.close_test()
        # Присваиваем значения.
        self.t = self.config.spi_t
        # self.spi.max_speed_hz = self.config.spi_max_speed_hz
        self.smq_now = self.config.smq_now

    """Метод для проверки. Возвращает True, если измерение давления запущено иначе False"""
    def is_test_on(self):
        result = False
        if self.test_on:
            result = True
        return result

    """Метод для установки состояния переключателя работы измерения давления в положение True/False"""
    def set_test_on(self, s):
        self.test_on = s

    """Метод для запуска отдельного потока для измерения давления"""
    def start_test(self):
        # Проверяем, что измерение давления еще не запущео
        if not self.is_test_on():
            # Устанавливаем состояние в режим "запущена"
            self.set_test_on(True)
            # Это команда присваивает отдельному потоку исполняемую процедуру калибровки
            self.my_thread = threading.Thread(target=self.implementation_test)
            # Запускаем поток и процедуру измерения давления
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Thread "Pressure measurement" started in the NORMAL MODE')
            self.my_thread.start()

    """Метод для выключения отдельного потока калибровки прибора"""
    def close_test(self):
        # Проверяем, что измерение давления запущено
        if self.is_test_on():
            # Устанавливаем состояние в режим "не запущено"
            self.set_test_on(False)
            # Вызываем выключение потока
            self.my_thread.join()
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Thread "Pressure measurement" finished '
                                                                             'in the NORMAL MODE')

    """Метод, где расположена процедура обработки измерения давления в отдельном потоке"""
    def implementation_test(self):
        # до тех пор пока процедура активна
        # (а она активна, пока пользователь не покинет вкладку "Ручное управление") выполняем:
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Pressure measurement for Manual control started\n'
                                   'self.t = {0}\nself.smq_now  = {1}'.format(str(self.t), str(self.smq_now)))
        while self.test_on:
            # получить данные с датчика
            result = self.read_channel()-self.correct_data
            # рассчитать на их основе давление сразу во всех единицах измерения
            p = self.calc_pressure(result)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Pressure = {0}Pa\t{1}Bar\t{2}psi'.format(str(p[0]), str(p[1]), str(p[2])))
            # отправляем сообщение о том, что давление рассчитано и его можно выводить в форму
            self.message.emit(p)
            # ожидание в соответсвии с config.ini
            time.sleep(self.t)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Pressure measurement for Manual control finished')

    """Метод, где мы получаем данные с датчика"""
    def read_channel(self):
        # инициализируем под измерение переменную data
        data = 0
        # делаем цикл по требуемому количеству замеров согласно config.ini
        for i in range(self.smq_now):
            # считываем данные с датчика
            ### STEP 3: Get data:
            raw_channels = self.ads.read_sequence(CH_SEQUENCE)
            data = data + raw_channels
            print("raw_channels: {0}". format(raw_channels))
            # voltages = [i * self.ads.v_per_digit for i in raw_channels]

        # берем среднее значение
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation data.....')
        try:
            data = data[self.channal] / self.smq_now
        except ArithmeticError:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Division by zero when calculating data, '
                                 'denominator: self.smq_now = {0}'.format(str(self.smq_now)))
            data = 0
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation data..... Done.')
        return data

    """Метод рассчета давления на основание данных с датчика"""
    def calc_pressure(self, data):
        # считаем сразу в кПа, Бар и psi и заворачиваем в массив
        p1 = self.getkPa(data)  # кПа
        p2 = self.getBar(data)  # Бар
        p3 = self.getPsi(data)  # psi
        # Возвращаем массив
        return [p1, p2, p3]

    """Метод для получения давления с датчика"""
    def get_pressure(self, crutch):
        # получить данные с датчика
        result = self.read_channel()-self.correct_data

        # рассчитать на их основе давление сразу во всех единицах измерения
        p = self.calc_pressure(result)
        # передаем давление в нужной единице измерения.
        s = p[self.config.pressure.value]
        return s

    """Метод, который на основание измерения высчитывает давление в кПа"""
    def getkPa(self, data):
        p = data / self.const_data * 130 # кПа
        return p

    """Метод, который на основание измерения высчитывает давление в Бар"""
    def getBar(self, data):
        p = data / self.const_data * 1.3  # Бар
        return p

    """Метод, который на основание измерения высчитывает давление в psi"""
    def getPsi(self, data):
        p = data / self.const_data * 130 * 0.14503773773  # psi
        return p

    """Метод, который возвращает из давление в кПа значение измерения"""
    def getDataFromkPa(self, p):
        data = p * self.const_data / 130  # кПа
        return data

    """Метод, который возвращает из давление в Бар значение измерения"""
    def getDataFromBar(self, p):
        data = p * self.const_data / 1.3  # кПа
        return data

    """Метод, который возвращает из давление в psi значение измерения"""
    def getDataFromPsi(self, p):
        data = p * self.const_data / 130 / 0.14503773773  # кПа
        return data