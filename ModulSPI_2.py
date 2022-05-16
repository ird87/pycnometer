#!/usr/bin/python
# Модуль для считывания данных с датчика
import inspect
import threading
import os

import xlwt

from SPI_Driver.ads1256_ADS1256_definitions import *
from SPI_Driver.ads1256_pipyadc import ADS1256

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
POTI = POS_AIN0 | NEG_AINCOM
# Light dependant resistor of the same board:
LDR = POS_AIN1 | NEG_AINCOM
# The other external input screw terminals of the Waveshare board:
EXT2, EXT3, EXT4 = POS_AIN2 | NEG_AINCOM, POS_AIN3 | NEG_AINCOM, POS_AIN4 | NEG_AINCOM
EXT5, EXT6, EXT7 = POS_AIN5 | NEG_AINCOM, POS_AIN6 | NEG_AINCOM, POS_AIN7 | NEG_AINCOM

# You can connect any pin as well to the positive as to the negative ADC input.
# The following reads the voltage of the potentiometer with negative polarity.
# The ADC reading should be identical to that of the POTI channel, but negative.
POTI_INVERTED = POS_AINCOM | NEG_AIN0

# For fun, connect both ADC inputs to the same physical input pin.
# The ADC should always read a value close to zero for this.
SHORT_CIRCUIT = POS_AIN0 | NEG_AIN0

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
        self.const_data = 6300000
        self.p_channel = self.config.data_channel
        # Заведем переменную для массива каналов, измеряющих температуру.
        self.t_channels = []
        # Переберем каналы из настроек и добавим их в переменную.
        for t_channel in self.config.t_channels:
            #  номер канала должен быть между 1 и 8 и он не должен повторяться.
            if 1 <= t_channel <= 8 and not (t_channel) in self.t_channels:
                self.t_channels.append(t_channel)

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
        self.correct_data = self.main.config.correct_data

        # region open textfile
        # self.file = os.path.join(os.getcwd(), "temperature.txt")
        # if os.path.isfile(self.file):
        #     os.remove(self.file)
        # handle = open(self.file, "w")
        # handle.write("{0}".format(time.strftime("%Y-%m-%d", time.localtime())))
        # handle.close()
        #
        # self.file_p = os.path.join(os.getcwd(), "pressure.txt")
        # if os.path.isfile(self.file_p):
        #     os.remove(self.file_p)
        # handle = open(self.file_p, "w")
        # handle.write("{0}".format(time.strftime("%Y-%m-%d", time.localtime())))
        # handle.close()
        # endregion

        self.create_xls_file()

    def set_correct_data(self, x):
        self.config.set_correct_data(x)
        self.correct_data = self.config.correct_data

    """Метод для применения настроек"""

    def set_option(self):
        self.test_on = False
        # Тест должен быть выключен для применения настроек. Ситуации, когда настройки применяются, а он включен
        # быть не должно, но на всякий случай мы явно вызовем его выключение.
        self.close_test()
        # Присваиваем значения.
        self.t = self.config.spi_t
        self.maximum_sensor_pressure = self.config.maximum_sensor_pressure
        # self.spi.max_speed_hz = self.config.spi_max_speed_hz
        self.smq_now = self.config.smq_now
        self.correct_data = self.config.correct_data

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
            self.my_thread = threading.Thread(target = self.implementation_test)
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
            # получить давление
            p = self.get_pressure()
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Pressure = {0}'.format(p))
            # отправляем сообщение о том, что давление рассчитано и его можно выводить в форму
            self.message.emit(p)
            # ожидание в соответсвии с config.ini
            time.sleep(self.t)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Pressure measurement for Manual control finished')

    """Метод, где мы получаем данные с датчика"""

    def read_channel(self):
        # инициализируем под измерение переменную data
        data = []
        data_channels = []
        # Канал, измеряющий давление всегда: [0]
        data_channels.append(CH_SEQUENCE[self.p_channel])
        data.append(0)
        # Теперь добавим каналы для температуры, если они есть.
        if len(self.t_channels) > 0:
            for t_channel in self.t_channels:
                data_channels.append(CH_SEQUENCE[t_channel])
                data.append(0)

        # делаем цикл по требуемому количеству замеров согласно config.ini
        for i in range(self.smq_now):
            # считываем данные с датчика
            ### STEP 3: Get data:
            raw_channels = self.ads.read_sequence(data_channels)
            if self.main.config.output_pt_to_xls:
                self.save_p_xls(raw_channels[0], self.calc_pressure(raw_channels[0])[0])
            for channel in range(len(raw_channels)):
                data[channel] += raw_channels[channel]
                # print("raw_channels: {0}". format(raw_channels))
                # # voltages = [i * self.ads.v_per_digit for i in raw_channels]
                # print("pressure PA: " + str(self.calc_pressure(raw_channels[0])[0]))

        # берем среднее значение
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation data.....')
        for i in range(len(data)):
            try:
                data[i] = data[i] / self.smq_now
            except ArithmeticError:
                self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                     'Division by zero when calculating data[{0}], '
                                     'denominator: self.smq_now = {1}'.format(i, str(self.smq_now)))
                data[i] = 0
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation data..... Done.')
        return data

    # region add text to file
    # def print_t(self, p, t):
    #     txt = "\n{0} -> P={1}".format(time.strftime("%H:%M:%S", time.localtime()), p)
    #     for i in range(len(t)):
    #         txt += "\tT{0}={1}".format(i, t[i])
    #     handle = open(self.file, "a+")
    #     handle.write(txt)
    #     handle.close()
    #
    # def print_p(self, p):
    #     txt = "\n{0}".format(p)
    #     handle = open(self.file_p, "a+")
    #     handle.write(txt)
    #     handle.close()
    # endregion

    def create_xls_file(self):
        self.file = os.path.join(os.getcwd(), "temperature & pressure.xls")
        if os.path.isfile(self.file):
            os.remove(self.file)
        if self.main.config.output_pt_to_xls:
            self.wb = xlwt.Workbook(encoding = 'WINDOWS-1251')
            self.wb_style = xlwt.easyxf("align: horiz centre; borders: left thin, right thin, top thin, bottom thin;")
            self.wsp = self.wb.add_sheet("{0} | pressure".format(time.strftime("%Y-%m-%d", time.localtime())))
            self.wsp_row = 0
            self.wsp.write(self.wsp_row, 0, 'Data', self.wb_style)
            self.wsp.write(self.wsp_row, 1, 'P', self.wb_style)
            self.wst = self.wb.add_sheet("{0} | temperature".format(time.strftime("%Y-%m-%d", time.localtime())))
            self.wst_row = 0
            self.wst.write(self.wst_row, 0, 'Time', self.wb_style)
            self.wst.write(self.wst_row, 1, 'P', self.wb_style)
            self.wst.write(self.wst_row, 2, 'T1', self.wb_style)
            self.wst.write(self.wst_row, 3, 'T2', self.wb_style)
            self.wst.write(self.wst_row, 4, 'T3', self.wb_style)
            self.wst.write(self.wst_row, 5, 'T4', self.wb_style)
            self.wb.save(self.file)

    def save_t_xls(self, p, t):
        if self.main.config.output_pt_to_xls:
            self.wst_row += 1
            self.wst.write(self.wst_row, 0, time.strftime("%H:%M:%S", time.localtime()), self.wb_style)
            self.wst.write(self.wst_row, 1, str(p), self.wb_style)
            for i in range(len(t)):
                self.wst.write(self.wst_row, i + 2, str(t[i]), self.wb_style)
            self.wb.save(self.file)

    def save_p_xls(self,data, p):
        if self.main.config.output_pt_to_xls:
            self.wsp_row += 1
            self.wsp.write(self.wsp_row, 0, str(data), self.wb_style)
            self.wsp.write(self.wsp_row, 1, str(p), self.wb_style)
            self.wb.save(self.file)

    """Метод рассчета давления на основание данных с датчика"""

    def calc_pressure(self, data_p):
        # считаем сразу в кПа, Бар и psi и заворачиваем в массив
        p1 = self.getkPa(data_p)  # кПа
        p2 = self.getBar(data_p)  # Бар
        p3 = self.getPsi(data_p)  # psi
        # Возвращаем массив
        return [p1, p2, p3]

    def calc_temperature(self, data_t):
        result = []
        for _data_t in data_t:
            t = _data_t * 1
            result.append(t)
        return result

    """Метод для получения давления с датчика"""

    def get_pressure(self, crutch="p"):
        # получить данные с датчика
        data = self.read_channel()
        result = data[0] - self.correct_data

        # рассчитать на их основе давление сразу во всех единицах измерения
        _p = self.calc_pressure(result)
        # передаем давление в нужной единице измерения.
        p = _p[self.config.pressure.value]
        if len(self.t_channels) > 0:
            data_t = data
            data_t.pop(0)
            t = self.calc_temperature(data_t)
            self.save_t_xls(p, t)
        return p

    """Метод, который на основание измерения высчитывает давление в кПа"""

    def getkPa(self, data):
        p = data / self.const_data * self.maximum_sensor_pressure  # кПа
        return p

    """Метод, который на основание измерения высчитывает давление в Бар"""

    def getBar(self, data):
        p = data / self.const_data * self.maximum_sensor_pressure * 0.01  # Бар
        return p

    """Метод, который на основание измерения высчитывает давление в psi"""

    def getPsi(self, data):
        p = data / self.const_data * self.maximum_sensor_pressure * 0.14503773773  # psi
        return p

    """Метод, который возвращает из давление в кПа значение измерения"""

    def getDataFromkPa(self, p):
        data = p * self.const_data / self.maximum_sensor_pressure  # кПа
        return data

    """Метод, который возвращает из давление в Бар значение измерения"""

    def getDataFromBar(self, p):
        data = p * self.const_data / self.maximum_sensor_pressure * 0.01  # кПа
        return data

    """Метод, который возвращает из давление в psi значение измерения"""

    def getDataFromPsi(self, p):
        data = p * self.const_data / self.maximum_sensor_pressure / 0.14503773773  # кПа
        return data
