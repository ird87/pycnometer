#!/usr/bin/python
# coding=utf-8
# Все что происходит во вкладке Измерения обрабатывается здесь
import datetime
import inspect
import math
import os
import time
import configparser

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
        self.m_medium_volume - float, сюда записывается рассчитанное в результате калибровки среднее значение объема.
        self.m_medium_density - float, сюда записывается рассчитанное в результате калибровки среднее значение плотности.
        self.m_SD - float, сюда записывается рассчитанное в результате калибровки значение СКО, г/см3.
        self.m_SD_per - float, сюда записывается рассчитанное в результате калибровки значение СКО, %.
        self.is_test_mode - ссылка на метод, проверяющий работает программа в тестовом режиме или запущена
        self.test_on - bool, переключатель, показывает выполняется ли в данный момент измерение или нет.   
        self.fail_pressure_set - ссылка на СИГНАЛ, для вывода сообщения о неудачном наборе давления
        self.fail_get_balance - ссылка на СИГНАЛ, для вывода сообщения о неудачном ожидании баланса     
"""

"""Функция для перевода минут, вводимых пользователем, в секунды, используемые программой"""
def set_time_min_to_sec(min):
    sec = min*60
    return sec

def set_time_sec_to_min(sec):
    min = int(sec/60)
    return min


class MeasurementProcedure(object):
    """docstring"""

    """Конструктор класса. Поля класса"""
    def __init__(self, main):
        self.main = main
        self.measurement_report = []
        self.operator = ''
        self.organization = ''
        self.sample = ''
        self.batch_series = ''
        self.table = self.main.t1_tableMeasurement
        self.round = self.table.round
        self.spi = self.main.spi
        self.gpio = self.main.gpio
        self.ports = self.main.ports
        self.block_other_tabs = self.main.block_other_tabs
        self.block_userinterface = self.main.block_userinterface_measurement
        self.unblock_userinterface = self.main.unblock_userinterface_measurement
        self.unblock_other_tabs = self.main.unblock_other_tabs
        self.file = os.path.basename(__file__)
        self.debug_log = self.main.debug_log
        self.measurement_log = self.main.measurement_log
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
        self.m_medium_volume = 0.0
        self.m_medium_density = 0.0
        self.m_SD = 0.0
        self.m_SD_per = 0.0
        self.is_test_mode = self.main.config.is_test_mode
        self.test_on = False
        self.set_measurement_results = self.main.measurement_results_message
        self.fail_pressure_set = self.main.fail_pressure_set
        self.fail_get_balance = self.main.fail_get_balance
        self.fail_let_out_pressure = self.main.fail_let_out_pressure
        self.measurement_file = ''
        self.result_file_reader = configparser.ConfigParser()
        self.abort_procedure = self.main.abort_procedure
        self.abort_procedure_on = False

    """Метод для проверки включено ли измерение в рассчеты"""
    def get_measurement_active(self, i):
        return self.measurements[i].active

    """Метод для проверки. Возвращает True, если измерение запущено иначе False"""
    def is_test_on(self):
        result = False
        if self.test_on:
            result = True
        return result

    """Метод для установки состояния переключателя работы измерения в положение True/False"""
    def set_test_on(self, s):
        self.test_on = s

    """Метод для установки состояния переключателя прерывающего процедуру"""
    def set_abort_procedure(self, s):
        self.abort_procedure_on = s

    """Метод для проверки. Возвращает True, если запущено прерывание процедуры"""
    def is_abort_procedure(self):
        result = False
        if self.abort_procedure_on:
            result = True
        return result

    """Загружаем выбранные на вкладке "Измерения" установки."""
    def set_settings(self, operator, organization, sample, batch_series, _cuvette, _sample_preparation, _sample_preparation_time_in_minute, _sample_mass,
                     _number_of_measurements, _take_the_last_measurements, _VcL, _VcM, _VcS, _VdLM, _VdS,
                     _Pmeas, _pulse_length):
        # self.test_on и abort_procedure_on должены быть False перед началом калибровки
        self.test_on = False
        self.abort_procedure_on = False
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
        # Откроем новый файл для записи результатов
        self.new_measurement_file()
        # Запишем данные.
        self.save_measurement_result()
        # self.measurements должен быть очищен перед началом новых измерений
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

    """Метод, где расположена процедура обработки измерения в отдельном потоке"""
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
            try:
                self.sample_preparation_vacuuming()
            except Exception as e:
                self.interrupt_procedure(e.args[0])
                return
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Vacuuming.....'
                                                                                   'Done.')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Vacuuming.....Done.')
        if self.sample_preparation == Sample_preparation.Blow:
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Blow.....')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Blow.....')
            try:
                self.sample_preparation_blow()
            except Exception as e:
                self.interrupt_procedure(e.args[0])
                return
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                                                            'Sample preparation: Blow.....Done.')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Blow.....Done.')
        if self.sample_preparation == Sample_preparation.Impulsive_blowing:
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Impulsive '
                                                                                   'blowing.....')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Impulsive '
                                                                          'blowing.....')
            try:
                self.sample_preparation_impulsive_blowing()
            except Exception as e:
                self.interrupt_procedure(e.args[0])
                return
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                                                    'Sample preparation: Impulsive blowing.....Done.')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Sample preparation: Impulsive '
                                                                             'blowing.....Done.')
        self.main.unblock_t1_gM_button4()
        # Этап 2. Измерения. Есть два вида: для большой и средней кюветы и для малой кюветы.
        if self.cuvette == Сuvette.Small:
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Small.....')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Small.....')
            try:
                self.measurement_cuvette_small()
            except Exception as e:
                self.interrupt_procedure(e.args[0])
                return
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                                                            'Measurement for Сuvette.Small.....Done.')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Small.....Done.')
        if not self.cuvette == Сuvette.Small:
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Large '
                                                                                   'or Cuvette.Medium.....')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Large '
                                                                             'or Cuvette.Medium.....')
            try:
                self.measurement_cuvette_large_or_medium()
            except Exception as e:
                self.interrupt_procedure(e.args[0])
                return
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Large '
                                                                                  'or Cuvette.Medium.....Done.')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement for Сuvette.Large '
                                                                             'or Cuvette.Medium.....Done.')

        # Этап 3. Вычисления.
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation.....')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation.....')
        self.last_numbers_result()
        try:
            self.calculation()
        except Exception as e:
            self.interrupt_procedure(e.args[0])
            return
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
    def interrupt_procedure(self, measurement):
        self.set_test_on(False)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement..... ' + measurement.name + '.')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement..... ' + measurement.name + '.')
        # выключаем все порты
        self.gpio.all_port_off()
        # Разлокируем остальные вкладки для пользователя.
        self.unblock_other_tabs()
        # Разблокируем кнопки, поля и работу с таблицей на текущей вкладке.
        self.unblock_userinterface()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'МЫ ТУТУ! Interface unlocked, Current tab = Measurement')
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measurement interrupted')
        if measurement == Abort_Type.Pressure_below_required:
            self.fail_pressure_set.emit()
        if measurement == Abort_Type.Could_not_balance:
            self.fail_get_balance.emit()
        if measurement == Abort_Type.Interrupted_by_user:
            self.abort_procedure.emit()
        if measurement == Abort_Type.Let_out_pressure_fail:
            self.fail_let_out_pressure.emit()

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
        self.main.progressbar_start.emit(self.main.languages.TitlesForProgressbar_SamplePreparation, self.main.languages.t1_gSP_gRB_rb1, self.sample_preparation_time + 17)
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K5.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K5 = {0}'.format(self.ports[Ports.K5.value]))
        self.check_for_interruption()
        self.time_sleep(self.sample_preparation_time)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(self.sample_preparation_time))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K5.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K5 = {0}'.format(self.ports[Ports.K5.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.check_for_interruption()
        self.time_sleep(15)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(15))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.check_for_interruption()
        self.time_sleep(2)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(2))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.main.progressbar_exit.emit()

    """Метод, подготовки образца с помощью Продувки"""
    def sample_preparation_blow(self):
        """-открыть К1, К2, К3, К4
        -ждать время указанное в окошке Подготовка образца>>Время (посмотри в чем указывается время в программе, скорее 
        всего секунды, на форме надо оставить минуты чтобы вводились)
        -закрыть К1
        -ждать 2 секунды
        -закрыть К4, К2, К3
        """
        self.main.progressbar_start.emit(self.main.languages.TitlesForProgressbar_SamplePreparation, self.main.languages.t1_gSP_gRB_rb2, self.sample_preparation_time + 2)
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.check_for_interruption()
        self.time_sleep(self.sample_preparation_time)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(self.sample_preparation_time))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.check_for_interruption()
        self.time_sleep(2)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(2))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.main.progressbar_exit.emit()

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
        try:
            t = round(self.sample_preparation_time / self.pulse_length)
        except ArithmeticError:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Division by zero when calculating t, '
                                 'denominator: self.pulse_length={0}'.format(self.pulse_length))
            t = 0
        self.main.progressbar_start.emit(self.main.languages.TitlesForProgressbar_SamplePreparation, self.main.languages.t1_gSP_gRB_rb3, self.sample_preparation_time + 3 + t * (self.pulse_length + 1))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.check_for_interruption()
        self.time_sleep(3)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(3))

        self.check_for_interruption()
        for i in range(t):
            self.check_for_interruption()
            self.gpio.port_off(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
            self.check_for_interruption()
            self.time_sleep(1)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(1))
            self.check_for_interruption()
            self.gpio.port_on(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
            self.check_for_interruption()
            self.time_sleep(self.pulse_length)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(self.pulse_length))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.main.progressbar_exit.emit()

    """Метод, Измерения для кюветы большой или средней"""
    def measurement_cuvette_large_or_medium(self):
        """Открыть К2, К3, К4
        Ждать 5 секунд
        Закрыть К2, К3, К4
        
        For i=1 to “Количество измерений”
        Ждать 2 сек
        Измерить давление Р0
        Открыть К1
		Открыть К2
        Ждать Т1
        Закрыть К1
		Закрыть К2
        Ждать Т2 сек
		Ждать 2 сек
        Измерить давление Р1
		Открыть К2		
        Открыть К3
        Ждать Т3 сек
		Закрыть К2
		Закрыть К3
		Ждать 2 сек
        Измерить давление Р2
        Ждать 2 сек
        Открыть К2, К3, К4
        Ждать Т4 сек
        Закрыть К2, К3, К4
        рассчитываем объем образца для таблицы: Vобразца = ((P2-P0)*(Vd+Vc)-(P1-P0)*Vd)/(P2-P0)
        рассчитываем плотность для таблицы: масса образца / Vобразца        
        Next i        
        """
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.check_for_interruption()
        self.time_sleep(5)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(5))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K4 = {0}'.format(self.ports[Ports.K4.value]))
        # Запускаем цикл по количству измерений.
        self.check_for_interruption()
        for i in range(self.number_of_measurements):
            # Создаем пустой экземпляр для записей результатов измерений как новый элемент списка измерений
            self.measurements.append(Measurement())
            self.check_for_interruption()
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(2))
            # Замеряем давление P0, ('p0') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.check_for_interruption()
            self.measurements[i].p0 = self.spi.get_pressure('p0')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : p0 = {1}'.format(i, self.measurements[i].p0))
            self.check_for_interruption()
            self.gpio.port_on(self.ports[Ports.K1.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K1 = {0}'.format(self.ports[Ports.K1.value]))
            self.check_for_interruption()
            self.gpio.port_on(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K2 = {0}'.format(self.ports[Ports.K2.value]))						   
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We expect a set of pressure')
            self.check_for_interruption()
            p, success, duration = self.gain_Pmeas()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure set - fail, P = {0}/{1}, time has passed: {2}'.format(p, self.Pmeas, duration))
                raise Exception(Abort_Type.Pressure_below_required)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure set - success, P = {0}/{1}, time has passed: {2}'.format(p, self.Pmeas, duration))
            self.check_for_interruption()
            self.gpio.port_off(self.ports[Ports.K1.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K1 = {0}'.format(self.ports[Ports.K1.value]))
            self.check_for_interruption()
            self.gpio.port_off(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K2 = {0}'.format(self.ports[Ports.K2.value]))									   
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            self.check_for_interruption()
            balance, success, duration = self.get_balance()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - fail, balance = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
                raise Exception(Abort_Type.Could_not_balance)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - success, balance = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
            self.check_for_interruption()
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(2))
            # Замеряем давление P1, ('p1') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.check_for_interruption()
            self.measurements[i].p1 = self.spi.get_pressure('p1')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : p1 = {1}'.format(i, self.measurements[i].p1))
            self.check_for_interruption()
            self.gpio.port_on(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
            self.check_for_interruption()
            self.gpio.port_on(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            self.check_for_interruption()
            balance, success, duration = self.get_balance()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - fail, balance = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
                raise Exception(Abort_Type.Could_not_balance)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - success, P = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
            self.check_for_interruption()
            self.gpio.port_off(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
            self.check_for_interruption()
            self.gpio.port_off(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K3 = {0}'.format(self.ports[Ports.K3.value]))									   
            self.check_for_interruption()
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(2))
            # Замеряем давление P2, ('p2') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.check_for_interruption()
            self.measurements[i].p2 = self.spi.get_pressure('p2')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : p2 = {1}'.format(i, self.measurements[i].p2))
            self.check_for_interruption()
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(2))
            self.check_for_interruption()
            self.gpio.port_on(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
            self.check_for_interruption()
            self.gpio.port_on(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K3 = {0}'.format(self.ports[Ports.K3.value]))		
            self.check_for_interruption()									   
            self.gpio.port_on(self.ports[Ports.K4.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            self.check_for_interruption()
            success, duration = self.let_out_pressure(self.measurements[i].p0)
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure let_out - fail, time '
                            'has passed: {0}'.format(duration))
                raise Exception(Abort_Type.Let_out_pressure_fail)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure let_out - success, time '
                            'has passed: {0}'.format(duration))
            self.check_for_interruption()
            self.gpio.port_off(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
            self.check_for_interruption()
            self.gpio.port_off(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K3 = {0}'.format(self.ports[Ports.K3.value]))		
            self.check_for_interruption()
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
                print("\n((P2 - P0) * (Vd + Vc) - (P1 - P0) * Vd) / (P2 - P0)")
                print("(({0} - {1}) * ({2} + {3}) - ({4} - {5}) * {6}) / ({7} - {8})".format(P2, P0, Vd, Vc, P1, P0, Vd, P2, P0))
                print("VcL = {0}\nVcM = {1}\nVcS = {2}\nVdLM = {3}\nVdS = {4}".format(self.VcL, self.VcM, self.VcS, self.VdLM, self.VdS ))
                volume = ((P2 - P0) * (Vd + Vc) - (P1 - P0) * Vd) / (P2 - P0)
                print("volume = {0}".format(volume))
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
            # Добавляем полученные измерения в таблицу
            self.save_measurement_result()
            self.table.add_measurement(self.measurements[i])
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Add measurements data to the table.....'
                                                                             'Done')

    """Метод, Измерения для кюветы малой"""
    def measurement_cuvette_small(self):
        """
		Открыть К2, К3, К4
        Ждать 5 секунд
        Закрыть К2, К3, К4
        For i= 1 to количество измерений
        -Ждать 2 сек
        -Измерить Р0
        -Открыть К1
		-Открыть К2
        -Ждать Т1
        -Закрыть К1
        -Закрыть К2
        -Ждать Т2
		-Ждать 2 сек
        -Измерить Р1
        -Открыть К3
        - Ждать Т3
		-Закрыть К3
		-Ждать 2 сек
        -Измерить Р2
        -Открыть К2, К3, К4
        -Ждать Т4
        -Закрыть К2, К3, К4
        
        рассчитываем объем образца для таблицы: Vобразца = ((P2-P0)*(Vds+Vcs)-(P1-P0)*Vd)/(P2-P0)
        рассчитываем плотность для таблицы: масса образца / Vобразца
        
        Next i
        
        Закрыть К3, К2
        """
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.check_for_interruption()
        self.time_sleep(5)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(5))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K4 = {0}'.format(self.ports[Ports.K4.value]))
        # Запускаем цикл по количству измерений.
        self.check_for_interruption()
        for i in range(self.number_of_measurements):
            # Создаем пустой экземпляр для записей результатов измерений как новый элемент списка измерений
            self.measurements.append(Measurement())
            self.check_for_interruption()
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(2))
            # Замеряем давление P0, ('p0') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.check_for_interruption()
            self.measurements[i].p0 = self.spi.get_pressure('p0')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : p0 = {1}'.format(i, self.measurements[i].p0))
            self.check_for_interruption()
            self.gpio.port_on(self.ports[Ports.K1.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K1 = {0}'.format(self.ports[Ports.K1.value]))
            self.check_for_interruption()
            self.gpio.port_on(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K2 = {0}'.format(self.ports[Ports.K2.value]))						   
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We expect a set of pressure')
            self.check_for_interruption()
            p, success, duration = self.gain_Pmeas()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure set - fail, P = {0}/{1}, time has passed: {2}'.format(p, self.Pmeas, duration))
                raise Exception(Abort_Type.Pressure_below_required)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure set - success, P = {0}/{1}, time has passed: {2}'.format(p, self.Pmeas, duration))
            self.check_for_interruption()
            self.gpio.port_off(self.ports[Ports.K1.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K1 = {0}'.format(self.ports[Ports.K1.value]))
            self.check_for_interruption()
            self.gpio.port_off(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            self.check_for_interruption()
            balance, success, duration = self.get_balance()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                           'pressure stops changing - fail, balance = {0}/{1}, time '
                                           'has passed: {2}'.format(balance, 0.01, duration))
                raise Exception(Abort_Type.Could_not_balance)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'pressure stops changing - success, P = {0}/{1}, time '
                                       'has passed: {2}'.format(balance, 0.01, duration))
            self.check_for_interruption()
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(2))
            # Замеряем давление P1, ('p1') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.check_for_interruption()
            self.measurements[i].p1 = self.spi.get_pressure('p1')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : p1 = {1}'.format(i, self.measurements[i].p1))
            self.check_for_interruption()
            self.gpio.port_on(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            self.check_for_interruption()
            balance, success, duration = self.get_balance()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - fail, balance = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
                raise Exception(Abort_Type.Could_not_balance)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - success, P = {0}/{1}, time '
                            'has passed: {2}'.format(balance, 0.01, duration))
            self.check_for_interruption()
            self.gpio.port_off(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
            self.check_for_interruption()
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(2))            
			# Замеряем давление P2, ('p2') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.check_for_interruption()
            self.measurements[i].p2 = self.spi.get_pressure('p2')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured P[{0}] : p2 = {1}'.format(i, self.measurements[i].p2))
            self.check_for_interruption()
            self.gpio.port_on(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K2 = {0}'.format(self.ports[Ports.K2.value]))
            self.check_for_interruption()
            self.gpio.port_on(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K3 = {0}'.format(self.ports[Ports.K3.value]))
            self.check_for_interruption()
            self.gpio.port_on(self.ports[Ports.K4.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            self.check_for_interruption()
            success, duration = self.let_out_pressure(self.measurements[i].p0)
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure let_out - fail, time '
                            'has passed: {0}'.format(duration))
                raise Exception(Abort_Type.Let_out_pressure_fail)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure let_out - success, time '
                            'has passed: {0}'.format(duration))
            self.check_for_interruption()
            self.gpio.port_off(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
            self.check_for_interruption()
            self.gpio.port_off(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
            self.check_for_interruption()
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
            self.save_measurement_result()
            self.table.add_measurement(self.measurements[i])
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Add measurements data to the table.....')

    """Метод обсчета полученных данных. Так как все данные хранятся в таблице с динамическим пересчетом, 
                                                                                    мы просто вызываем этот пересчет"""
    def calculation(self):
        volume_sum = 0
        density_sum = 0

        # --------------------------------------------------------------------------------------------------------------

        # заведем переменную для подсчета количества данных списка, включенных в рассчет
        counter1 = 0

        # Считаем средний объем и среднюю плотность
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'Calculation medium_volume & medium_density.....')
        for m in self.measurements:
            if m.active:
                # для включенных в рассчет данных суммируем значение объема
                volume_sum += m.volume
                # и плотности
                density_sum += m.density
                # и само количество включенных измерений
                counter1 += 1
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation medium_volume.....')
        try:
            # Рассчитываем средний объем
            self.m_medium_volume = volume_sum / counter1
        except ArithmeticError:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Division by zero when calculating medium_volume, '
                                 'denominator: counter1={0}'.format(counter1))
            self.m_medium_volume = 0
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Measured : Medium volume = {0}'.format(self.m_medium_volume))
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation medium_volume..... Done.')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation medium_density.....')
        try:
            # Рассчитываем средн.. плотность
            self.m_medium_density = density_sum / counter1
        except ArithmeticError:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Division by zero when calculating medium_density, '
                                 'denominator: counter1={0}'.format(counter1))
            self.m_medium_density = 0
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Measured : Medium volume = {0}'.format(self.m_medium_volume))
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation medium_density..... Done.')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'Calculation medium_volume & medium_density..... Done.')

        # --------------------------------------------------------------------------------------------------------------

        # заведем переменную для подсчета количества данных списка, включенных в рассчет
        counter2 = 0
        # Теперь считаем отклонения для каждой строки
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation for ALL.....')
        for m in self.measurements:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Calculation deviation for Measured[{0}].....'.format(counter2))
            try:
                # Рассчитываем отклонение
                deviation = (self.m_medium_volume - m.volume) / self.m_medium_volume * 100
            except ArithmeticError:
                self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                     'Division by zero when calculating deviation, '
                                     'denominator: medium_volume={0}'.format(self.m_medium_volume))
                deviation = 0
            if m.active:
                m.deviation = deviation
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                           'Measured[{0}] deviation = {1}'.format(counter2, m.deviation))
            if not m.active:
                m.deviation = ''
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                           'Measured[{0}] this measurement is not active'.format(counter2))
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Calculation deviation for Measured[{0}]..... Done.'.format(counter2))
            # Добавляем в таблицу в столбец для отклонений
            self.table.add_item(m.deviation, counter2, 5, m.active)
            counter2 += 1
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation for ALL..... Done.')

        # --------------------------------------------------------------------------------------------------------------

        # заведем переменную для подсчета количества данных списка, включенных в рассчет
        counter3 = 0
        # заведем переменную для суммы квадратов всех отклонений
        squared_of_density_deviations_sum = 0

        # Считаем СКО и СКО%:
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation SKO & SKO%.....')
        for m in self.measurements:
            if m.active:
                # для всех активных измерений считаем сумму квадратов их отклонений
                squared_of_density_deviations_sum += (self.m_medium_volume - m.volume) ** 2
                counter3 += 1
        # Считаем СКО:
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation SKO.....')
        try:
            self.m_SD = math.sqrt(squared_of_density_deviations_sum / counter3)
        except ArithmeticError:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Division by zero when calculating SKO, denominator: '
                                 'counter3={0}'.format(counter3))
            self.m_SD = 0
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Measured : SKO = {0}'.format(self.m_SD))
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation SKO..... Done.')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation SKO%.....')
        try:
            self.m_SD_per = (self.m_SD / self.m_medium_volume) * 100
        except ArithmeticError:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Division by zero when calculating SKO%, denominator: '
                                 'counter3={0}'.format(self.m_medium_volume))
            self.m_SD_per = 0
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Measured : SKO% = {0}%'.format(self.m_SD_per))
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation SKO%..... Done.')

        # -----------------------------------------------------------------------------------------------------

        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation SKO & SKO%..... Done.')
        # Сохраняем результаты
        self.save_measurement_result()
        # Вызываем вывод результатов на форму.
        self.set_measurement_results.emit()



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
            self.check_for_interruption()
            self.time_sleep_without_interruption(0.1)
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
        self.time_sleep_without_interruption(3)
        # Замеряем давление p_previous, ('p1') - нужно только для тестового режима, чтобы имитировать похожее давление.
        p_previous = self.spi.get_pressure('p1')
        self.time_sleep_without_interruption(1)
        # Замеряем давление p_next, ('p1') - нужно только для тестового режима, чтобы имитировать похожее давление.
        p_next = self.spi.get_pressure('p1')
        while not p_test:
            self.check_for_interruption()
            self.time_sleep_without_interruption(1)
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

    """Метод сброса давления"""
    def let_out_pressure(self, p0):
        time_start = datetime.datetime.now()
        p_test = False
        success = False
        duration = 0
        while not p_test:
            self.check_for_interruption()
            self.time_sleep_without_interruption(0.1)
            # Замеряем новое p_let_out_pressure, ('p1') - нужно только для тестового режима, чтобы имитировать похожее давление.
            p_let_out_pressure = self.spi.get_pressure('p1')
            # Проверяем достаточно ли низкое давление.
            print("Давление = {0} < p0*2 = {1}".format(p_let_out_pressure, p0*2))
            # if p_let_out_pressure < p0*2 or self.is_test_mode():
            if duration > 10 or self.is_test_mode():
                p_test = True
                success = True
            time_now = datetime.datetime.now()
            duration = round((time_now - time_start).total_seconds(), 1)
            # Если время выпуска давления достигло 2 минут, то завершаем процедуру давления, неуспех.
            if duration >= 120:
                p_test = True
            self.time_sleep_without_interruption(2)
        return success, duration

    """Метод вывода отчета по процедуре "Измерение"."""
    def create_report(self):
        # эти переменные нужна, чтобы найти следующий порядковый номер файла.
        find_name = True
        number = 0
        report_name = ''
        self.measurement_report = self.main.measurement_report

        if not os.path.isdir(os.path.join(os.getcwd(), 'Reports')):
            os.makedirs(os.path.join(os.getcwd(), 'Reports'))
        # Определяем следующее подходящее имя файла.
        while find_name:
            number += 1
            # для нормального режима (Linux) нужны такие команды:
            report_name = os.path.join(os.getcwd(), 'Reports', 'Measurement' + ' - ' + self.get_today_date() + ' - ' + str(
                number) + '.pdf')
            find_name = os.path.isfile(report_name)

        doc = SimpleDocTemplate(report_name, pagesize = letter, encoding = 'WINDOWS-1251')

        # # Ветка для программы в тестовом режиме.
        # if self.is_test_mode():
        #     if not os.path.isdir(os.getcwd() + '\Reports'):
        #         os.makedirs(os.getcwd() + '\Reports')
        #     # Определяем следующее подходящее имя файла.
        #     while find_name:
        #         number += 1
        #         # для тестового режима (Windows) нужны такие команды:
        #         report_name = os.getcwd() + '\Reports\Measurement' + ' - ' + self.get_today_date() + ' - ' + str(
        #             number) + '.pdf'
        #         find_name = os.path.isfile(report_name)
        #
        # # Ветка для программы в нормальном режиме.
        # if not self.is_test_mode():
        #     if not os.path.isdir(os.getcwd() + '/Reports'):
        #         os.makedirs(os.getcwd() + '/Reports')
        #     # Определяем следующее подходящее имя файла.
        #     while find_name:
        #         number += 1
        #         # для нормального режима (Linux) нужны такие команды:
        #         report_name = os.getcwd() + '/Reports/Measurement' + ' - ' + self.get_today_date() + ' - ' + str(
        #             number) + '.pdf'
        #         find_name = os.path.isfile(report_name)

        # doc = SimpleDocTemplate(report_name, pagesize = letter, encoding = 'WINDOWS-1251')

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
                [self.measurement_report['t3_medium_volume'], toFixed(self.m_medium_volume, self.round),
                 self.measurement_report['t3_m_sd'], toFixed(self.m_SD, self.round)],
                [self.measurement_report['t3_medium_density'], toFixed(self.m_medium_density, self.round),
                 self.measurement_report['t3_m_sd_per'], toFixed(self.m_SD_per, self.round)],
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

    """Метод для выключения из расчета данных в соответствие с переменной с выбором пользователя перед началом изменений"""
    def last_numbers_result(self):
        for i in range(len(self.measurements) - self.take_the_last_measurements):
            self.measurements[i].set_active_off()
            self.table.set_color_to_row_unactive(i)

    """Метод устанавливает текущий файл измерений. В него можно записать данные и из него можно загрузить их"""
    def set_measurement_file(self, file_name):
        self.measurement_file = file_name

    """Метод создает новый текущий файл измерений. В него можно записать данные и из него можно загрузить их"""
    def new_measurement_file(self):
        # проверим наличие каталога, если его нет - создадим.
        self.check_result_dir()
        find_name = True
        number = 0

        # Определяем следующее подходящее имя файла.
        while find_name:
            number += 1
            # для нормального режима (Linux) нужны такие команды:
            self.measurement_file = os.path.join(os.getcwd(), 'Results', 'Measurements', 'Measurement' + ' - ' + self.get_today_date() + ' - ' + str(
                number) + '.result')
            find_name = os.path.isfile(self.measurement_file)
        self.result_file_reader.read(self.measurement_file, encoding = 'WINDOWS-1251')

        # # Ветка для программы в тестовом режиме.
        # if self.is_test_mode():
        #     # Определяем следующее подходящее имя файла.
        #     while find_name:
        #         number += 1
        #         # для тестового режима (Windows) нужны такие команды:
        #         self.measurement_file = os.getcwd() + '\Results\Measurements\Measurement' + ' - ' + self.get_today_date() + ' - ' + str(
        #             number) + '.result'
        #         find_name = os.path.isfile(self.measurement_file)
        #     self.result_file_reader.read(self.measurement_file)
        #
        # # Ветка для программы в нормальном режиме.
        # if not self.is_test_mode():
        #     # Определяем следующее подходящее имя файла.
        #     while find_name:
        #         number += 1
        #         # для нормального режима (Linux) нужны такие команды:
        #         self.measurement_file = os.getcwd() + '/Results/Measurements/Measurement' + ' - ' + self.get_today_date() + ' - ' + str(
        #             number) + '.result'
        #         find_name = os.path.isfile(self.measurement_file)
        #     self.result_file_reader.read(self.measurement_file, encoding = 'WINDOWS-1251')
        with open(self.measurement_file, "w") as fh:
            self.result_file_reader.write(fh)

    """Проверим наличие каталога, если его нет - создадим."""
    def check_result_dir(self):
        if not os.path.isdir(os.path.join(os.getcwd(), 'Results', 'Measurements')):
            os.makedirs(os.path.join(os.getcwd(), 'Results', 'Measurements'))
        # if self.is_test_mode():
        #     if not os.path.isdir(os.getcwd() + '\Results\Measurements'):
        #         os.makedirs(os.getcwd() + '\Results\Measurements')
        # if not self.is_test_mode():
        #     if not os.path.isdir(os.getcwd() + '/Results/Measurements'):
        #         os.makedirs(os.getcwd() + '/Results/Measurements')

    """Метод для сохранения измерений в файл"""
    def save_measurement_result(self):
        self.result_file_reader.read(self.measurement_file)
        self.update_measurement_file('GeneralInformation', 'operator', self.operator)
        self.update_measurement_file('GeneralInformation', 'organization', self.organization)
        self.update_measurement_file('GeneralInformation', 'sample', self.sample)
        self.update_measurement_file('GeneralInformation', 'batch_series', self.batch_series)
        self.update_measurement_file('SamplePreparation', 'sample_preparation', str(self.sample_preparation.value))
        self.update_measurement_file('SamplePreparation', 'sample_preparation_time', str(set_time_sec_to_min(self.sample_preparation_time)))
        self.update_measurement_file('Measurement', 'sample_mass', str(self.sample_mass))
        self.update_measurement_file('Measurement', 'cuvette', str(self.cuvette.value))
        self.update_measurement_file('Measurement', 'number_of_measurements', str(self.number_of_measurements))
        self.update_measurement_file('Measurement', 'take_the_last_measurements', str(self.take_the_last_measurements))
        for i in range(len(self.measurements)):
            self.update_measurement_file('Measurement-' + str(i), 'p0', str(self.measurements[i].p0))
            self.update_measurement_file('Measurement-' + str(i), 'p1', str(self.measurements[i].p1))
            self.update_measurement_file('Measurement-' + str(i), 'p2', str(self.measurements[i].p2))
            self.update_measurement_file('Measurement-' + str(i), 'volume', str(self.measurements[i].volume))
            self.update_measurement_file('Measurement-' + str(i), 'density', str(self.measurements[i].density))
            self.update_measurement_file('Measurement-' + str(i), 'deviation', str(self.measurements[i].deviation))
            self.update_measurement_file('Measurement-' + str(i), 'active', str(self.measurements[i].active))
        self.update_measurement_file('MeasurementResult', 'medium_volume', str(self.m_medium_volume))
        self.update_measurement_file('MeasurementResult', 'medium_density', str(self.m_medium_density))
        self.update_measurement_file('MeasurementResult', 'SD', str(self.m_SD))
        self.update_measurement_file('MeasurementResult', 'SD_per', str(self.m_SD_per))
        os.rename(self.measurement_file, self.measurement_file + "~")
        os.rename(self.measurement_file + ".new", self.measurement_file)
        os.remove(self.measurement_file + "~")

    """Метод обновления данных в файле"""
    def update_measurement_file(self, section, val, s):
        if not self.result_file_reader.has_section(section):
            self.result_file_reader.add_section(section)
        self.result_file_reader.set(section, val, s)
        with open(self.measurement_file + ".new", "w") as fh:
            self.result_file_reader.write(fh)


    """Метод для загрузки измерений из файла"""
    def load_measurement_result(self):
        self.result_file_reader.read(self.measurement_file)
        # if self.is_test_mode():
        #     # для тестового режима (Windows) нужны такие команды:
        #     self.result_file_reader.read(self.measurement_file)
        # if not self.is_test_mode():
        #     # для нормального режима (Linux) нужны такие команды:
        #     self.result_file_reader.read(self.measurement_file, encoding='utf-8')

        # [GeneralInformation]
        self.operator = self.try_load_string('GeneralInformation', 'operator')
        self.organization = self.try_load_string('GeneralInformation', 'organization')
        self.sample = self.try_load_string('GeneralInformation', 'sample')
        self.batch_series = self.try_load_string('GeneralInformation', 'batch_series')
        general_information = {
            'operator': self.operator,
            'organization': self.organization,
            'sample': self.sample,
            'batch_series': self.batch_series
        }

        # [SamplePreparation]
        sample_preparation_type = self.try_load_int('SamplePreparation', 'sample_preparation')
        if sample_preparation_type is None:
            self.sample_preparation = Sample_preparation.Vacuuming
        else:
            self.sample_preparation = Sample_preparation(sample_preparation_type)
        self.sample_preparation_time = self.try_load_int('SamplePreparation', 'sample_preparation_time')
        sample_preparation = {
            'sample_preparation': self.sample_preparation,
            'sample_preparation_time': self.sample_preparation_time
        }

        # [Measurement]
        self.sample_mass = self.try_load_float('Measurement', 'sample_mass')
        cuvette_type = self.try_load_int('Measurement', 'cuvette')
        if cuvette_type is None:
            self.cuvette = Сuvette.Large
        else:
            self.cuvette = Сuvette(cuvette_type)
        self.number_of_measurements = self.try_load_int('Measurement', 'number_of_measurements')
        self.take_the_last_measurements = self.try_load_int('Measurement', 'take_the_last_measurements')
        measurement = {
            'sample_mass': self.sample_mass,
            'cuvette': self.cuvette,
            'number_of_measurements': self.number_of_measurements,
            'take_the_last_measurements': self.take_the_last_measurements
        }
        measurements = []
        # [Measurement-0] - [Measurement-(number_of_measurements-1)]
        for i in range(self.number_of_measurements):
            p0 = self.try_load_float('Measurement-' + str(i), 'p0')
            p1 = self.try_load_float('Measurement-' + str(i), 'p1')
            p2 = self.try_load_float('Measurement-' + str(i), 'p2')
            volume = self.try_load_float('Measurement-' + str(i), 'volume')
            density = self.try_load_float('Measurement-' + str(i), 'density')
            deviation = self.try_load_float('Measurement-' + str(i), 'deviation')
            active = self.try_load_boolean('Measurement-' + str(i), 'active')
            measurements.append({
                'p0': p0,
                'p1': p1,
                'p2': p2,
                'volume': volume,
                'density': density,
                'deviation': deviation,
                'active': active
            })

        # [MeasurementResult]
        self.m_medium_volume = self.try_load_float('MeasurementResult', 'medium_volume')
        self.m_medium_density = self.try_load_float('MeasurementResult', 'medium_density')
        self.m_SD = self.try_load_float('MeasurementResult', 'sd')
        self.m_SD_per = self.try_load_float('MeasurementResult', 'sd_per')
        measurement_result = {
            'medium_volume': self.m_medium_volume,
            'medium_density': self.m_medium_density,
            'sd': self.m_SD,
            'sd_per': self.m_SD_per
        }
        result = [general_information, sample_preparation, measurement, measurements, measurement_result]
        return result

    def get_files_list(self):
        # проверим наличие каталога, если его нет - создадим.
        self.check_result_dir()
        dir = os.path.join(os.getcwd(), 'Results', 'Measurements')
        # if self.is_test_mode():
        #     dir = os.getcwd() + '\Results\Measurements\\'
        # if not self.is_test_mode():
        #     dir = os.getcwd() + '/Results/Measurements/'
        files = [f for f in os.listdir(dir) if f.endswith('.result')]
        ret_files = {}
        for f in files:
            file = os.path.join(dir, f)
            data_changed = time.gmtime(os.path.getmtime(file))
            ret_files.update({f: data_changed})
        return ret_files, dir

    def check_for_interruption(self):
        if self.is_abort_procedure():
            raise Exception(Abort_Type.Interrupted_by_user)

    """Метод для обработки ожидания. Для тестового режима программыожидание - опускается"""
    def time_sleep(self, t):
        if not self.is_test_mode():
            l = 0
            while l < t:
                self.check_for_interruption()
                l += 1
                time.sleep(1)
                self.main.progressbar_change.emit(1)

    def time_sleep_without_interruption(self, t):
        if not self.is_test_mode():
            time.sleep(t)

    def try_load_string(self, section, variable):
        result = ''
        try:
            result = self.result_file_reader.get(section, variable)
        except:
            result = None
        return result

    def try_load_int(self, section, variable):
        result = 0
        try:
            result = self.result_file_reader.getint(section, variable)
        except:
            result = None
        return result

    def try_load_float(self, section, variable):
        result = 0
        try:
            result = self.result_file_reader.getfloat(section, variable)
        except:
            result = None
        return result

    def try_load_boolean(self, section, variable):
        result = False
        try:
            result = self.result_file_reader.getboolean(section, variable)
        except:
            result = None
        return result


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
class Abort_Type(Enum):
    No_Abort = 0
    Pressure_below_required = 1
    Could_not_balance = 2
    Interrupted_by_user = 3
    Let_out_pressure_fail = 4


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
