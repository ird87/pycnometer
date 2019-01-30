#!/usr/bin/python
# coding=utf-8
# Все что происходит во вкладке Измерения обрабатывается здесь
import datetime
import inspect
import math
import os
import time

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate
from reportlab.rl_config import defaultPageSize

pdfmetrics.registerFont(TTFont('Arial-Bold', 'arialbd.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Regular', 'arial.ttf'))
pdfmetrics.registerFont(TTFont('Arial-Italic', 'ariali.ttf'))
pdfmetrics.registerFont(TTFont('Arial-BoldItalic', 'arialbi.ttf'))

from enum import Enum
import threading


from Measurement import Measurement

"""Проверка и комментари: 23.01.2019"""

"""
"Класс для обработки процедуры "Измерения"
    1) Получает данные введенные пользователем в форме и указанные в файле config.ini 
    2) Проводит процедуру измерений, соответсвующуюю указанным настройкам
    3) Формирует таблицу данных и вызывает расчет, основанный на этой таблице.  
        self.measurement_report - список заголовков для отчета.
        self.operator - Данные оператора
        self.organization - Организация
        self.sample - Информация об образце
        self.batch_series - паспорт и серия     
        self.table - ссылка на таблицу, в которую будут записаны результаты измрений
        self.spi - ссылка на модуль SPI, который получает данные с датчика
        self.gpio - ссылка на модуль GPIO, который открывает и закрывает клапаны прибора
        self.ports - массив, в котором хранятся номера портов, соответствующие клапанам: [K1; K2; K3; K4; K5]
        self.block_other_tabs - ссылка на метод, блокирующий на время измерений остальные вкладки программы.
        self.block_userinterface - ссылка на метод, блокирующий на время измерений кнопки, поля, работу 
                                                                                с таблицей и пр... на текущей вкладке
        self.unblock_userinterface ссылка на метод, разблокирующий после окончания измерений остальные вкладки программы
        self.unblock_other_tabs - ссылка на метод, разблокирующий после окончания измерений кнопки, поля, работу 
                                                                                с таблицей и пр... на текущей вкладке
        self.file - записываем название текущего файла 'CalibrationProcedure.py'
        self.debug_log - ссылка на модуль для записи логов программы
        self.measurement_log - ссылка на модуль для записи логов прибора
        self.cuvette - Enum, хранит информацию о используемой кювете. Информация берется из интерфеса 
                    вкладки "Калибровка" и может принимать три значения: Сuvette.Large; Сuvette.Medium; Сuvette.Small; 
        self.sample_preparation - Enum, хранит информацию о типе подготовки образца к измерениям. Информация берется из 
                    интерфеса вкладки "Измерение" и может принимать три значения: Сuvette.Vacuuming, Сuvette.Blow, 
                    Сuvette.Impulsive_blowing
        self.sample_preparation_time - int, время подготовки образца в секундах
        self.sample_mass = float, масса образца, вводится пользователем в интерфейсе "Измерения"
        self.number_of_measurements - int, количество измерений
        self.take_the_last_measurements - int, сколько последних измерений взять в рассчет
        self.VcL - float, объем большой кюветы
        self.VcM - float, объем средней кюветы
        self.VcS - float, объем малой кюветы
        self.VdLM - float, дополнительный объем для большой и средней кюветы
        self.VdS - float, дополнительный объем для малой кюветы
        self.Pmeas - float, давление необходимое для измерений
        self.pulse_length - int, длинна импульса в сек. Указывается в настройках.
        self.measurements - список экземляров класса "измерение", куда будут сохранятся все данные для вывода в таблицу
        self.is_test_mode - ссылка на метод, проверяющий работает программа в тестовом режиме или запущена
        self.test_on - bool, переключатель, показывает выполняется ли в данный момент измерение или нет.   
        self.fail_pressure_set - ссылка на СИГНАЛ, для вывода сообщения о неудачном наборе давления
        self.fail_get_balance - ссылка на СИГНАЛ, для вывода сообщения о неудачном ожидании баланса     
"""

"""Функция для перевода минут, вводимых пользователем, в секунды, используемые программой"""
def set_time_min_to_sec(min):
    sec = min*60
    return sec


class MeasurementProcedure(object):
    """docstring"""

    """Конструктор класса. Поля класса"""
    def __init__(self, table, spi, gpio, ports, block_other_tabs, block_userinterface,
                 unblock_userinterface, unblock_other_tabs, debug_log, measurement_log, is_test_mode,
                 fail_pressure_set, fail_get_balance):
        self.measurement_report = []
        self.operator = ''
        self.organization = ''
        self.sample = ''
        self.batch_series = ''
        self.table = table
        self.round = self.table.round
        self.spi = spi
        self.gpio = gpio
        self.ports = ports
        self.block_other_tabs = block_other_tabs
        self.block_userinterface = block_userinterface
        self.unblock_userinterface = unblock_userinterface
        self.unblock_other_tabs = unblock_other_tabs
        self.file = os.path.basename(__file__)
        self.debug_log = debug_log
        self.measurement_log = measurement_log
        self.cuvette = Сuvette.Large
        self.sample_preparation = Sample_preparation.Vacuuming
        self.sample_preparation_time = 0                        # время в секундах
        self.sample_mass = 0
        self.number_of_measurements = 0
        self.take_the_last_measurements = 0
        self.VcL = 0
        self.VcM = 0
        self.VcS = 0
        self.VdLM = 0
        self.VdS = 0
        self.Pmeas = 0
        self.pulse_length = 0
        self.measurements = []
        self.is_test_mode = is_test_mode
        self.test_on = False
        self.fail_pressure_set = fail_pressure_set
        self.fail_get_balance = fail_get_balance

    """Метод для проверки. Возвращает True, если измерение запущено иначе False"""
    def is_test_on(self):
        result = False
        if self.test_on:
            result = True
        return result

    """Метод для установки состояния переключателя работы измерения в положение True/False"""
    def set_test_on(self, s):
        self.test_on = s

    """Загружаем выбранные на вкладке "Измерения" установки."""
    def set_settings(self, measurement_report, operator, organization, sample, batch_series, _cuvette, _sample_preparation, _sample_preparation_time_in_minute, _sample_mass,
                     _number_of_measurements, _take_the_last_measurements, _VcL, _VcM, _VcS, _VdLM, _VdS,
                     _Pmeas, _pulse_length):
        # self.test_on должен быть False перед началом калибровки
        self.test_on = False
        self.measurement_report = measurement_report
        self.operator = operator
        self.organization = organization
        self.sample = sample
        self.batch_series = batch_series
        self.cuvette = _cuvette
        self.sample_preparation = _sample_preparation
        # В следующей строке переводим время в секунды
        self.sample_preparation_time = set_time_min_to_sec(_sample_preparation_time_in_minute)
        self.sample_mass = _sample_mass
        self.number_of_measurements = _number_of_measurements
        self.take_the_last_measurements = _take_the_last_measurements
        # VcL; VcM: VcS; VdLM; VdS беруться из config.ini, устанавливаются и записываются туда при калибровке.
        self.VcL = _VcL
        self.VcM = _VcM
        self.VcS = _VcS
        self.VdLM = _VdLM
        self.VdS = _VdS
        self.Pmeas = _Pmeas
        self.pulse_length = _pulse_length
        # self.measurements должен быть очищен перед началом новых калибровок
        self.measurements.clear()
        txt = 'The following measurement settings are set:' \
            '\nCuvette = {0}' \
            '\nSample preparation = {1}' \
            '\nSample preparation time = {2}' \
            '\nSample mass = {3}' \
            '\nNumber of measurements = {4}' \
            '\nTake the last measurements = {5}' \
            '\nVcL = {6}' \
            '\nVcM = {7}' \
            '\nVcS = {8}' \
            '\nVdLM = {9}' \
            '\nVdS = {10}' \
            '\nPmeas = {11}'.format(self.cuvette, self.sample_preparation, self.sample_preparation_time,
                                    self.sample_mass, self.number_of_measurements, self.take_the_last_measurements,
                                    self.VcL, self.VcM, self.VcS, self.VdLM, self.VdS, self.Pmeas)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, txt)

    """Метод для запуска отдельного потока измерения прибора"""
    def start_measurements(self):
        # Проверяем, что измерение еще не запущено
        if not self.is_test_on():
            # Устанавливаем состояние измерения в режим "запущена"
            self.set_test_on(True)
            # Это команда присваивает отдельному потоку исполняемую процедуру измерения
            self.my_thread = threading.Thread(target=self.measurements_procedure)
            # Запускаем поток и процедуру калибровки
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Thread "Measurement" started')
            self.my_thread.start()

    """Метод для выключения отдельного потока измерения прибора"""
    def close_measurements(self):
        # Проверяем, что измерение запущено
        if self.is_test_on():
            # Устанавливаем состояние измерения в режим "не запущено"
            self.set_test_on(False)
            # Вызываем выключение потока
            self.my_thread.join()
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Thread "Measurement" finished')

    """Метод, где расположена процедура обработки измрения в отдельном потоке"""
    def measurements_procedure(self):
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement started')
        # Блокируем остальные вкладки для пользователя.
        self.block_other_tabs()
        # Блокируем кнопки, поля и работу с таблицей на текущей вкладке.
        self.block_userinterface()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Interface locked, Current tab = Measurement')
        # Этап 1. Подготовка образца. Вызываем соответствующую процедуру в зависимости от выбранного типа подготовки
        if self.sample_preparation == Sample_preparation.Vacuuming:
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Vacuuming.....')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Vacuuming.....')
            self.sample_preparation_vacuuming()
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Vacuuming.....'
                                                                                   'Done.')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Vacuuming.....Done.')
        if self.sample_preparation == Sample_preparation.Blow:
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Blow.....')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Blow.....')
            self.sample_preparation_blow()
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                                                            'Sample preparation: Blow.....Done.')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Blow.....Done.')
        if self.sample_preparation == Sample_preparation.Impulsive_blowing:
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Impulsive '
                                                                                   'blowing.....')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Impulsive '
                                                                             'blowing.....')
            self.sample_preparation_impulsive_blowing()
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                                                    'Sample preparation: Impulsive blowing.....Done.')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Impulsive '
                                                                             'blowing.....Done.')

        # Этап 2. Измерения. Есть два вида: для большой и средней кюветы и для малой кюветы.
        if self.cuvette == Сuvette.Small:
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Small.....')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Small.....')
            measurement = self.measurement_cuvette_small()
            # обрабатываем проблему набора давления
            if not measurement == Pressure_Error.No_Error:
                self.measurement_fail(measurement)
                return
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                                                            'Measurement for Сuvette.Small.....Done.')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Small.....Done.')
        if not self.cuvette == Сuvette.Small:
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Large '
                                                                                   'or Cuvette.Medium.....')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Large '
                                                                             'or Cuvette.Medium.....')
            measurement = self.measurement_cuvette_large_or_medium()
            # обрабатываем проблему набора давления
            if not measurement == Pressure_Error.No_Error:
                self.measurement_fail(measurement)
                return
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Large '
                                                                                  'or Cuvette.Medium.....Done.')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Large '
                                                                             'or Cuvette.Medium.....Done.')

        # Этап 3. Вычисления.
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation.....')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation.....')
        self.density_calculation()
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation..... Done.')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation..... Done.')
        # Разлокируем остальные вкладки для пользователя.
        self.unblock_other_tabs()
        # Разблокируем кнопки, поля и работу с таблицей на текущей вкладке.
        self.unblock_userinterface()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'Interface unlocked, Current tab = Measurement')
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement finished')

    """Метод обработки прерывания измерения из-за низкого давления"""
    def measurement_fail(self, measurement):
        self.set_test_on(False)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement..... Fail.')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement..... Fail.')
        # выключаем все порты
        self.gpio.all_port_off()
        # Разлокируем остальные вкладки для пользователя.
        self.unblock_other_tabs()
        # Разблокируем кнопки, поля и работу с таблицей на текущей вкладке.
        self.unblock_userinterface()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'Interface unlocked, Current tab = Measurement')
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement interrupted')
        if measurement == Pressure_Error.Pressure_Set:
            self.fail_pressure_set.emit()
        if measurement == Pressure_Error.Get_Balance:
            self.fail_get_balance.emit()

    """Метод, подготовки образца с помощью Вакууминга"""
    def sample_preparation_vacuuming(self):
        """-открыть К3, К2, К5
        -ждать время указанное в окошке Подготовка образца>>Время (посмотри в чем указывается время в программе, скорее 
        всего секунды, на форме надо оставить минуты чтобы вводились)
        -закрыть К5
        -открыть К1
        -ждать 15 секунд
        -закрыть К1
        - открыть К4
        -ждать 2 секунды
        -закрыть К4, К2, К3
        """
        self.gpio.port_on(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.gpio.port_on(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.gpio.port_on(self.ports[Ports.K5.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K5 = {0}'.format(self.ports[Ports.K5.value]))
        self.time_sleep(self.sample_preparation_time)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(self.sample_preparation_time))
        self.gpio.port_off(self.ports[Ports.K5.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K5 = {0}'.format(self.ports[Ports.K5.value]))
        self.gpio.port_on(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.time_sleep(15)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(15))
        self.gpio.port_off(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.gpio.port_on(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.time_sleep(2)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(2))
        self.gpio.port_off(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.gpio.port_off(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.gpio.port_off(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K3 = {0}'.format(self.ports[Ports.K3.value]))

    """Метод, подготовки образца с помощью Продувки"""
    def sample_preparation_blow(self):
        """-открыть К1, К2, К3, К4
        -ждать время указанное в окошке Подготовка образца>>Время (посмотри в чем указывается время в программе, скорее 
        всего секунды, на форме надо оставить минуты чтобы вводились)
        -закрыть К1
        -ждать 2 секунды
        -закрыть К4, К2, К3
        """
        self.gpio.port_on(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.gpio.port_on(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.gpio.port_on(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.gpio.port_on(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.time_sleep(self.sample_preparation_time)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(self.sample_preparation_time))
        self.gpio.port_off(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.time_sleep(2)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(2))
        self.gpio.port_off(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.gpio.port_off(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.gpio.port_off(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K3 = {0}'.format(self.ports[Ports.K3.value]))

    """Метод, подготовки образца с помощью Импульсной продувки"""
    def sample_preparation_impulsive_blowing(self):
        """Если галочка на Имп продувке, то: (во вкладке Настройки необходим параметр длина импульса (в секундах)
        открыть К1, К2, К3, К4
        ждать 3 секунды
        For i = 1 to ОКРУГЛИТЬ((общее время подготовки с вкладки измерения в сек)/(длину импульса с вкладки Настройки))
        закрыть К3
        ждать 1 сек
        открыть К3
        ждать (длина импульса с вкладки Настройки)
                    Next i
        Закрыть К1, К2, К3, К4
        """
        self.gpio.port_on(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.gpio.port_on(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.gpio.port_on(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.gpio.port_on(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.time_sleep(3)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(3))
        try:
            t = round(self.sample_preparation_time / self.pulse_length)
        except ArithmeticError:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Division by zero when calculating t, '
                                 'denominator: self.pulse_length={0}'.format(self.pulse_length))
            t = 0

        for i in range(t):
            self.gpio.port_off(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
            self.time_sleep(1)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(1))
            self.gpio.port_on(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
            self.time_sleep(self.pulse_length)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(self.pulse_length))
        self.gpio.port_off(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.gpio.port_off(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.gpio.port_off(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.gpio.port_off(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K3 = {0}'.format(self.ports[Ports.K3.value]))

    """Метод, Измерения для кюветы большой или средней"""
    def measurement_cuvette_large_or_medium(self):
        """Открыть К2, К3, К4
        Ждать 5 секунд
        Закрыть К4
        
        For i=1 to “Количество измерений”
        Ждать 2 сек
        Измерить давление Р0
        Закрыть К3
        Открыть К1
        Ждать Т1
        Закрыть К1
        Ждать Т2 сек
        Измерить давление Р1
        Открыть К3
        Ждать Т3 сек
        Измерить давление Р2
        Ждать 2 сек
        Открыть К4
        Ждать Т4 сек
        Закрыть К4
        рассчитываем объем образца для таблицы: Vобразца = ((P2-P0)*(Vd+Vc)-(P1-P0)*Vd)/(P2-P0)
        рассчитываем плотность для таблицы: масса образца / Vобразца        
        Next i        
        Закрыть К3, К2
        """
        self.gpio.port_on(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.gpio.port_on(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.gpio.port_on(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.time_sleep(5)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(5))
        self.gpio.port_off(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K4 = {0}'.format(self.ports[Ports.K4.value]))
        # Запускаем цикл по количству измерений.
        for i in range(self.number_of_measurements):
            # Создаем пустой экземпляр для записей результатов измерений как новый элемент списка измерений
            self.measurements.append(Measurement())
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(2))
            # Замеряем давление P0, ('p0') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.measurements[i].p0 = self.spi.get_pressure('p0')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : p0 = {1}'.format(i, self.measurements[i].p0))
            self.gpio.port_off(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
            self.gpio.port_on(self.ports[Ports.K1.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K1 = {0}'.format(self.ports[Ports.K1.value]))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We expect a set of pressure')
            p, success, duration = self.gain_Pmeas()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure set - fail, P = {0}/{1}, time has passed: {2}'.format(p, self.Pmeas, duration))
                return Pressure_Error.Pressure_Set
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure set - success, P = {0}/{1}, time has passed: {2}'.format(p, self.Pmeas, duration))
            self.gpio.port_off(self.ports[Ports.K1.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K1 = {0}'.format(self.ports[Ports.K1.value]))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            balance, success, duration = self.get_balance()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - fail, balance = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
                return Pressure_Error.Get_Balance
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - success, balance = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
            # Замеряем давление P1, ('p1') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.measurements[i].p1 = self.spi.get_pressure('p1')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : p1 = {1}'.format(i, self.measurements[i].p1))
            self.gpio.port_on(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            balance, success, duration = self.get_balance()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - fail, balance = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
                return Pressure_Error.Get_Balance
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - success, P = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
            # Замеряем давление P2, ('p2') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.measurements[i].p2 = self.spi.get_pressure('p2')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : p2 = {1}'.format(i, self.measurements[i].p2))
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(2))
            self.gpio.port_on(self.ports[Ports.K4.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            balance, success, duration = self.get_balance()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - fail, balance = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
                return Pressure_Error.Get_Balance
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - success, P = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
            self.gpio.port_off(self.ports[Ports.K4.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K4 = {0}'.format(self.ports[Ports.K4.value]))
            # Берем нужное (в зависимости от кюветы) значение Vc
            Vc = 0
            if self.cuvette == Сuvette.Large:
                Vc = self.VcL
            if self.cuvette == Сuvette.Medium:
                Vc = self.VcM
            # и значение Vd
            Vd = self.VdLM
            P0 = self.measurements[i].p0
            P1 = self.measurements[i].p1
            P2 = self.measurements[i].p2
            mass = self.sample_mass
            # Считаем объем.
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation volume.....')
            try:
                volume = ((P2 - P0) * (Vd + Vc) - (P1 - P0) * Vd) / (P2 - P0)
            except ArithmeticError:
                self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                     'Division by zero when calculating volume, '
                                     'denominator: (P2={0} - P0={1})={2}'.format(P2, P0, (P2-P0)))
                volume = 0
            self.measurements[i].volume = volume
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : volume = {1}'.format(i, self.measurements[i].volume))
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation volume.....Done')
            # Считаем плотность.
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation density.....')
            try:
                density = mass / volume
            except ArithmeticError:
                self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                     'Division by zero when calculating density, '
                                     'denominator: volume={0}'.format(volume))
                density = 0           
            self.measurements[i].density = density
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : density = {1}'.format(i, self.measurements[i].density))
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation volume.....Done')
            # deviation мы пока не можем посчитать, так что присваиваем ему None
            self.measurements[i].deviation = None
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Add measurements data to the table.....')
            # Добавляем полученные измерения калибровки в таблицу
            self.table.add_measurement(self.measurements[i])
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Add measurements data to the table.....'
                                                                             'Done')
        self.gpio.port_off(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.gpio.port_off(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
        return Pressure_Error.No_Error

    """Метод, Измерения для кюветы малой"""
    def measurement_cuvette_small(self):
        """Открыть К2, К3
        For i= 1 to количество измерений
               - Ждать 2 сек
        -Измерить Р0
        -Закрыть К3
        -Открыть К1
        -Ждать Т1
        -Закрыть К1, К2
        -Ждать Т2
        -Измерить Р1
        -Открыть К3
        - Ждать Т3
        -Измерить Р2
        - Открыть К2, К4
        -Ждать Т4
        -Закрыть К4
        
        рассчитываем объем образца для таблицы: Vобразца = ((P2-P0)*(Vds+Vcs)-(P1-P0)*Vd)/(P2-P0)
        рассчитываем плотность для таблицы: масса образца / Vобразца
        
        Next i
        
        Закрыть К3, К2
        """
        self.gpio.port_on(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.gpio.port_on(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
        # Запускаем цикл по количству измерений.
        for i in range(self.number_of_measurements):
            # Создаем пустой экземпляр для записей результатов измерений как новый элемент списка измерений
            self.measurements.append(Measurement())
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(2))
            # Замеряем давление P0, ('p0') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.measurements[i].p0 = self.spi.get_pressure('p0')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : p0 = {1}'.format(i, self.measurements[i].p0))
            self.gpio.port_off(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
            self.gpio.port_on(self.ports[Ports.K1.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K1 = {0}'.format(self.ports[Ports.K1.value]))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We expect a set of pressure')
            p, success, duration = self.gain_Pmeas()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure set - fail, P = {0}/{1}, time has passed: {2}'.format(p, self.Pmeas, duration))
                return False
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure set - success, P = {0}/{1}, time has passed: {2}'.format(p, self.Pmeas, duration))
            self.gpio.port_off(self.ports[Ports.K1.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K1 = {0}'.format(self.ports[Ports.K1.value]))
            self.gpio.port_off(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            balance, success, duration = self.get_balance()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - fail, balance = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
                return Pressure_Error.Get_Balance
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - success, P = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
            # Замеряем давление P1, ('p1') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.measurements[i].p1 = self.spi.get_pressure('p1')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : p1 = {1}'.format(i, self.measurements[i].p1))
            self.gpio.port_on(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            balance, success, duration = self.get_balance()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - fail, balance = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
                return Pressure_Error.Get_Balance
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - success, P = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
            # Замеряем давление P2, ('p2') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.measurements[i].p2 = self.spi.get_pressure('p2')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : p2 = {1}'.format(i, self.measurements[i].p2))
            self.gpio.port_on(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
            self.gpio.port_on(self.ports[Ports.K4.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            balance, success, duration = self.get_balance()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - fail, balance = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
                return Pressure_Error.Get_Balance
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - success, P = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
            self.gpio.port_off(self.ports[Ports.K4.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K4 = {0}'.format(self.ports[Ports.K4.value]))
            # Берем нужное значение Vc
            Vc = self.VcS
            # и Vd
            Vd = self.VdS
            P0 = self.measurements[i].p0
            P1 = self.measurements[i].p1
            P2 = self.measurements[i].p2
            mass = self.sample_mass
            # Считаем объем.
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation volume.....')
            try:
                volume = ((P2 - P0) * (Vd + Vc) - (P1 - P0) * Vd) / (P2 - P0)
            except ArithmeticError:
                self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                     'Division by zero when calculating volume, '
                                     'denominator: (P2={0} - P0={1})={2}'.format(P2, P0, (P2-P0)))
                volume = 0
            self.measurements[i].volume = volume
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : volume = {1}'.format(i,self.measurements[i].volume))
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation volume.....Done')
            # Считаем плотность.
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation density.....')
            try:
                density = mass / volume
            except ArithmeticError:
                self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                     'Division by zero when calculating density, '
                                     'denominator: volume={0}'.format(volume))
                density = 0
            self.measurements[i].density = density
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : density = {1}'.format(i,self.measurements[i].density))
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation volume.....Done')
            # deviation мы пока не можем посчитать, так что присваиваем ему None
            self.measurements[i].deviation = None
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Add measurements data to the table.....')
            # Добавляем полученные измерения калибровки в таблицу
            self.table.add_measurement(self.measurements[i])
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Add measurements data to the table.....'
                                                                             'Done')
        self.gpio.port_off(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.gpio.port_off(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
        return True

    """Метод обсчета полученных данных. Так как все данные хранятся в таблице с динамическим пересчетом, 
                                                                                    мы просто вызываем этот пересчет"""
    def density_calculation(self):
        # Передаем в таблицу информацию о том, сколько последних вычислений надо учитывать в рассчете.
        self.table.last_numbers_result(self.take_the_last_measurements)
        # и вызываем пересчет
        self.table.recalculation_results()

    """Метод для обработки ожидания. Для тестового режима программыожидание - опускается"""
    def time_sleep(self, t):
        if not self.is_test_mode():
            time.sleep(t)

    """Метод набора требуемого давления"""
    def gain_Pmeas(self):
        """с частотой 0,1 сек проверять не набрано ли уже давление Ризм, снимая показания датчика,
        если набрано, переходить к следующему пункту в алгоритме.

        ограничение на 30 сек, если за это время не набрал давление, то останавливать полностью измерение или
        калибровку, выдавать окошко “Низкий поток газа, измерение прервано”.
        """
        time_start = datetime.datetime.now()
        Pmeas = self.Pmeas
        p_test = False
        success = False
        p = 0
        duration = 0
        while not p_test:
            self.time_sleep(0.1)
            # Замеряем давление p, ('p1') - нужно только для тестового режима, чтобы имитировать похожее давление.
            p = self.spi.get_pressure('p1')
            # Если текущее давление больше или равно требуемому, то завершаем набор давления, успех.
            if p >= Pmeas:
                p_test = True
                success = True
            time_now = datetime.datetime.now()
            duration = round((time_now - time_start).total_seconds(), 1)
            # Если время набора давления достигло 30 сек, то завершаем набор давления, неуспех.
            if duration >= 30:
                p_test = True
        return p, success, duration

    """Метод установки равновесия"""
    def get_balance(self):
        """Установка равновесия (вместо Т2, Т3 и Т4)

        Необходимо ожидать пока давление перестанет изменяться.

        То есть необходимо измерять давление каждую секунду и если оно не меняется больше чем на 1% по сравнению с предыдущим, то переходим к следующему шагу
        строчку “Ждать Т2” в итоге заменит что то вроде:

        Ждать 3 сек
        Измерить Рпред
        Ждать 1 сек
        Измерить Рслед
        Пока Модуль((Рслед-Рпред)/Рпред)>0.01
           Ждать 1 сек
           Рпред=Рслед
           Измерить Р (Рслед=Р)
        Ждать 3 сек

        Переходим к следующему шагу в общем алгоритме

        Здесь тоже необходима проверка по общему времени, но тут 5 минут.

        """
        time_start = datetime.datetime.now()
        p_test = False
        success = False
        balance = 0
        duration = 0
        self.time_sleep(3)
        # Замеряем давление p_previous, ('p1') - нужно только для тестового режима, чтобы имитировать похожее давление.
        p_previous = self.spi.get_pressure('p1')
        self.time_sleep(1)
        # Замеряем давление p_next, ('p1') - нужно только для тестового режима, чтобы имитировать похожее давление.
        p_next = self.spi.get_pressure('p1')
        while not p_test:
            self.time_sleep(1)
            # p_next становиться p_previous
            p_previous = p_next
            # Замеряем новое p_next, ('p1') - нужно только для тестового режима, чтобы имитировать похожее давление.
            p_next = self.spi.get_pressure('p1')

            # Считаем баланс.
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation balance.....')
            try:
                balance = math.fabs((p_next - p_previous) / p_previous)
            except ArithmeticError:
                self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                        'Division by zero when calculating balance, denominator: '
                        '((p_next = {0} - p_previous = {1}) / p_previous = {2}'.format(p_next, p_previous, p_previous))
                balance = 0
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation balance.....Done')
            # Если отклонение давлений в пределах погрешности
            if balance <= 0.01:
                p_test = True
                success = True
            time_now = datetime.datetime.now()
            duration = round((time_now - time_start).total_seconds(), 1)
            # Если время набора давления достигло 5 минут, то завершаем набор давления, неуспех.
            if duration >= 300:
                p_test = True
            self.time_sleep(3)
        return balance, success, duration

    """Метод вывода отчета по процедуре "Измерение"."""
    def create_report(self):
        # эти переменные нужна, чтобы найти следующий порядковый номер файла.
        find_name = True
        number = 0
        report_name=''
        # Ветка для программы в тестовом режиме.
        if self.is_test_mode():
            # Определяем следующее подходящее имя файла.
            while find_name:
                number += 1
                # для тестового режима (Windows) нужны такие команды:
                report_name = os.getcwd() + '\Reports\Measurement' + ' - ' + self.get_today_date() + ' - ' + str(
                    number) + '.pdf'
                find_name = os.path.isfile(report_name)

        # Ветка для программы в нормальном режиме.
        if not self.is_test_mode():
            # Определяем следующее подходящее имя файла.
            while find_name:
                number += 1
                # для нормального режима (Linux) нужны такие команды:
                report_name = os.getcwd() + '/Reports/Measurement' + ' - ' + self.get_today_date() + ' - ' + str(
                    number) + '.pdf'
                find_name = os.path.isfile(report_name)

        doc = SimpleDocTemplate(report_name, pagesize = letter, encoding = 'WINDOWS-1251')

        # сюда мы будем добавлять созданные таблицы.
        elements = []

        # Определяем размеры страницы.
        PAGE_WIDTH = defaultPageSize[0]
        PAGE_HEIGHT = defaultPageSize[1]

        # Таблица 1 "Общая информация", устанавливаем нужное количество строк, столбцов
        # и отталкиваясь от этого, считаем ширину ячейки.
        table_row1 = 5
        table_column1 = 2
        x1 = (PAGE_WIDTH - 20) / table_column1 / inch
        y1 = 0.4

        # Создаем массив данных для добавления в таблицу.
        data1 = [
                [self.measurement_report['t1_title']],
                [self.measurement_report['t1_operator'], self.operator],
                [self.measurement_report['t1_organization'], self.organization],
                [self.measurement_report['t1_sample'], self.sample],
                [self.measurement_report['t1_batch_series'], self.batch_series]]

        # Добавляем данные в таблицу и форматируем ее.
        t1 = Table(data1, table_column1 * [x1 * inch], table_row1 * [y1 * inch])
        t1.setStyle(TableStyle([
            ('SPAN', (0, 0), (1, 0)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONT', (0, 0), (-1, -1), 'Arial-Regular'),
            ('FONT', (0, 0), (0, 0), 'Arial-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black)
        ]))

        # Таблица 2 "Экспериментальные изменения", устанавливаем нужное количество строк, столбцов

        table_row2 = 2
        table_column2 = 6

        # Создаем массив данных для добавления в таблицу.
        data2 = [
                [self.measurement_report['t2_title']],
                [self.measurement_report['t2_p0'], self.measurement_report['t2_p1'], self.measurement_report['t2_p2'],
                 self.measurement_report['t2_volume'], self.measurement_report['t2_density'],
                 self.measurement_report['t2_deviation']],
                ]

        # Добавляем в массив данных наши измерения и считаем сколько в итоге будет строк.
        from Main import toFixed
        for m in self.measurements:
            if m.active:
                data2.append([toFixed(m.p0, self.round), toFixed(m.p1, self.round), toFixed(m.p2, self.round),
                              toFixed(m.volume, self.round), toFixed(m.density, self.round),
                              toFixed(m.deviation, self.round)])
                table_row2 += 1

        # и отталкиваясь от этого, считаем ширину ячейки.
        x2 = (PAGE_WIDTH - 20) / table_column2 / inch
        y2 = 0.4

        # Добавляем данные в таблицу и форматируем ее.
        t2 = Table(data2, table_column2 * [x2 * inch], table_row2 * [y2 * inch])
        t2.setStyle(TableStyle([
            ('SPAN', (0, 0), (5, 0)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONT', (0, 0), (-1, -1), 'Arial-Regular'),
            ('FONT', (0, 0), (5, 1), 'Arial-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black)
        ]))

        # Таблица 3 "Результаты измерений", устанавливаем нужное количество строк, столбцов
        # и отталкиваясь от этого, считаем ширину ячейки.
        table_row3 = 3
        table_column3 = 4
        x3 = (PAGE_WIDTH - 20) / table_column3 / inch
        y3 = 0.4

        # Создаем массив данных для добавления в таблицу.
        data3 = [
                [self.measurement_report['t3_title']],
                [self.measurement_report['t3_medium_volume'], toFixed(self.table.m_medium_volume, self.round),
                 self.measurement_report['t3_m_sd'], toFixed(self.table.m_SD, self.round)],
                [self.measurement_report['t3_medium_density'], toFixed(self.table.m_medium_density, self.round),
                 self.measurement_report['t3_m_sd_per'], toFixed(self.table.m_SD_per, self.round)],
                ]

        # Добавляем данные в таблицу и форматируем ее.
        t3 = Table(data3, table_column3 * [x3 * inch], table_row3 * [y3 * inch])
        t3.setStyle(TableStyle([
            ('SPAN', (0, 0), (3, 0)),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONT', (0, 0), (-1, -1), 'Arial-Regular'),
            ('FONT', (0, 0), (0, 0), 'Arial-Bold'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('VALIGN', (0, 0), (0, 0), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.25, colors.black)
        ]))

        # Создаем общий массив данных стостоящий из 3-х наших таблиц.
        data = [
            [t1],
            [''],
            [t2],
            [''],
            [t3]
        ]

        # Добавляем данные в итоговую таблицу
        shell_table = Table(data)

        # Добавляем итоговую таблицу в наш массив элементов.
        elements.append(shell_table)
        doc.build(elements)

    """Метод получения текущей дате в формате год-месяц-день, так нужно для удобства сортировки файлов в папке"""
    def get_today_date(self):
        logname = datetime.datetime.now().strftime("%Y-%m-%d")
        return logname

# Enum Размер кюветы
class Сuvette(Enum):
    Large = 0
    Medium = 1
    Small = 2

# Enum Тип подготовки образца
class Sample_preparation(Enum):
    Vacuuming = 0
    Blow = 1
    Impulsive_blowing = 2

# Enum тип ошибки при наборе газа
class Pressure_Error(Enum):
    No_Error = 0
    Pressure_Set = 1
    Get_Balance = 2


# Enum для наглядного вызова портов
class Ports(Enum):
    K1 = 0
    K2 = 1
    K3 = 2
    K4 = 3
    K5 = 4

    #
    # для канваса
    # c = canvas.Canvas(doc)
    # PAGE_WIDTH = defaultPageSize[0]
    # PAGE_HEIGHT = defaultPageSize[1]
    # font_size = 20
    # tab = 15
    # c.setFont('Arial', font_size)
    # # c.setFillColor(black)
    #
    # text = "Отчет с результатами измерений плотности на Пикнометре"
    # text_width = c.stringWidth(text)
    # x = (PAGE_WIDTH - text_width) / 2.0
    # y = PAGE_HEIGHT - font_size - tab  # wherever you want your text to appear
    # c.drawString(x, y, text)
    # c.showPage()
    # c.save()


    # styles.add(ParagraphStyle(
    # styles = getSampleStyleSheet()
    #
    #     'Arial_Bold',
    #     parent = styles['Normal'],
    #     fontName = 'Arial-Bold',
    #     fontSize = 12,
    #     alignment = TA_CENTER,
    #
    # ))
    # styles.add(ParagraphStyle(
    #     'Arial',
    #     parent = styles['Normal'],
    #     fontName = 'Arial-Regular',
    #     fontSize = 12,
    #     alignment = TA_CENTER,
    # ))
