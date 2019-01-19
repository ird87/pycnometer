#!/usr/bin/python
# coding=utf-8
import datetime
import inspect
import math
import os
import time
import threading
from Calibration import Calibration
from MeasurementProcedure import Сuvette, Ports, Pressure_Error

"""Проверка и комментари: 08.01.2019"""ХУЙ

"""
"Класс для обработки процедуры "Калибровка"
    1) Получает данные введенные пользователем в форме и указанные в файле config.ini 
    2) Проводит процедуру калибровки, соответсвующуюю указанным настройкам
    3) Формирует таблицу данных и вызывает расчет, основанный на этой таблице.
    
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
        self.message - ссылка на СИГНАЛ, для вывода ожидающего сообщения, о необходимости положить в кювету образец
        self.file - записываем название текущего файла 'CalibrationProcedure.py'
        self.debug_log - ссылка на модуль для записи логов программы
        self.measurement_log - ссылка на модуль для записи логов прибора
        self.cuvette - Enum, хранит информацию о используемой кювете. Информация берется из интерфеса 
                    вкладки "Калибровка" и может принимать три значения: Сuvette.Large; Сuvette.Medium; Сuvette.Small; 
        self.number_of_measurements - int, хранит информацию о количестве измерений. Информация берется из интерфеса 
                                                                                                    вкладки "Калибровка"
        self.sample_volume - float, объем стандартного образца. Информация берется из интерфеса вкладки "Калибровка"
        self.VcL - float, объем большой кюветы
        self.VcM - float, объем средней кюветы
        self.VcS - float, объем малой кюветы
        self.VdLM - float, дополнительный объем для большой и средней кюветы
        self.VdS - float, дополнительный объем для малой кюветы
        self.Pmeas - float, давление необходимое для измерений
        self.calibrations = [] - список экземляров класса "калибровка", куда будут сохранятся все данные для 
                                                                                                        вывода в таблицу
        self.is_test_mode - ссылка на метод, проверяющий работает программа в тестовом режиме или запущена 
                                                                                                в нормальном на rasberry
        self.P - принимает значения типа string, может быть либо P либо P'
        self.lock - bool, переключатель, используется для приостановки процедуры в ожидании, пока пользователь 
                                                                            подтвердит, что положил образец в кювету.
        self.test_on - bool, переключатель, показывает выполняется ли в данный момент калибровка или нет.
        self.fail_pressure_set - ссылка на СИГНАЛ, для вывода сообщения о неудачном наборе давления
        self.fail_get_balance - ссылка на СИГНАЛ, для вывода сообщения о неудачном ожидании баланса
"""

"""Функция для перевода минут, вводимых пользователем, в секунды, используемые программой"""
def set_time_min_to_sec(min):
    sec = min * 60
    return sec


class CalibrationProcedure(object):
    """docstring"""

    """Конструктор класса. Поля класса"""
    def __init__(self, table, spi, gpio, ports, block_other_tabs, block_userinterface,
                 unblock_userinterface, unblock_other_tabs, message, debug_log, measurement_log, is_test_mode,
                 fail_pressure_set, fail_get_balance):
        self.table = table
        self.spi = spi
        self.gpio = gpio
        self.ports = ports
        self.block_other_tabs = block_other_tabs
        self.block_userinterface = block_userinterface
        self.unblock_userinterface = unblock_userinterface
        self.unblock_other_tabs = unblock_other_tabs
        self.message = message
        self.file = os.path.basename(__file__)
        self.debug_log = debug_log
        self.measurement_log = measurement_log
        self.cuvette = Сuvette.Large
        self.number_of_measurements = 0
        self.sample_volume = 0
        self.VcL = 0
        self.VcM = 0
        self.VcS = 0
        self.VdLM = 0
        self.VdS = 0
        self.Pmeas = 0
        self.calibrations = []
        self.is_test_mode = is_test_mode
        self.P = ''
        self.lock = True
        self.test_on = False
        self.fail_pressure_set = fail_pressure_set
        self.fail_get_balance = fail_get_balance

    """Метод для проверки. Возвращает True, если калибровка запущена иначе False"""
    def is_test_on(self):
        result = False
        if self.test_on:
            result = True
        return result

    """Метод для установки состояния переключателя работы калибровки в положение True/False"""
    def set_test_on(self, state):
        self.test_on = state

    """Метод для приостановки процедуры калибровки, чтобы пользователь мог положить образец в кювету"""
    def set_lock(self):
        self.lock = True

    """Метод для возобновления процедуры калибровки, после того как пользователь положил образец в кювету"""
    def set_unlock(self):
        self.lock = False

    """Загружаем выбранные на вкладке "Калибровка" установки."""
    def set_settings(self, _cuvette, _number_of_measurements, _sample_volume, _Pmeas):

        # self.test_on должен быть False перед началом калибровки
        self.test_on = False
        self.cuvette = _cuvette
        self.number_of_measurements = _number_of_measurements
        self.sample_volume = _sample_volume
        self.Pmeas = _Pmeas
        # self.calibrations должен быть очищен перед началом новых калибровок
        self.calibrations.clear()
        txt = 'The following calibration settings are set:\nCuvette = ' + str(self.cuvette) + '\nNumber of measurements = ' + \
              str(self.number_of_measurements) + '\nSample volume = ' + str(self.sample_volume) + '\nVcL = ' + \
              str(self.VcL) + '\nVcM = ' + str(self.VcM) + '\nVcS = ' + str(self.VcS) + '\nVdLM = ' + str(self.VdLM) + \
              '\nVdS = ' + str(self.VdS) + '\nPmeas = ' + str(self.Pmeas)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, txt)

    """Метод для запуска отдельного потока калибровки прибора"""
    def start_calibrations(self):
        # Проверяем, что калибровка еще не запущена
        if not self.is_test_on():
            # Устанавливаем состояние калиброски в режим "запущена"
            self.set_test_on(True)
            # Это команда присваивает отдельному потоку исполняемую процедуру калибровки
            self.my_thread = threading.Thread(target = self.calibrations_procedure)
            # Запускаем поток и процедуру калибровки
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Thread "Calibration" started')
            self.my_thread.start()

    """Метод для выключения отдельного потока калибровки прибора"""
    def close_calibrations(self):
        # Проверяем, что калибровка запущена
        if self.is_test_on():
            # Устанавливаем состояние калиброски в режим "не запущена"
            self.set_test_on(False)
            # Вызываем выключение потока
            self.my_thread.join()
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Thread "Calibration" finished')

    """Метод, где расположена процедура обработки калибровки в отдельном потоке"""
    def calibrations_procedure(self):
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calibration started')
        # Этот код юольше не нужен, мы выводим в лог работы прибора настройки перед началом калибровки.
        # if self.cuvette == Сuvette.Small:
        #     print('Малая кювета')
        # if self.cuvette == Сuvette.Medium:
        #     print('Средняя кювета')
        # if self.cuvette == Сuvette.Large:
        #     print('Большая кювета')
        # Блокируем остальные вкладки для пользователя.
        self.block_other_tabs()
        # Блокируем кнопки, поля и работу с таблицей на текущей вкладке.
        self.block_userinterface()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Interface locked, Current tab = Calibration')
        self.P = 'P'
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measure P.....')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measure P.....')
        # Вызываем процедуру калибровки для P
        calibration = self.calibration_all_cuvette()
        # обрабатываем проблему набора давления
        if not calibration == Pressure_Error.No_Error:
            self.calibration_fail(calibration)
            return
        # отправляем сообщение о том, что пользователь должен положить образец в кювету.
        self.message.emit()
        # приостанавливаем работу калибровки
        self.set_lock()
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measure P finished. Waiting for user '
                                                                               'to put object in cuvette...')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measure P finished. Waiting for user to put '
                                                                         'object in cuvette...')
        # это цикл ожидание, он прервется как только пользователь подтвердит, что положил образец в кювету.
        while self.lock:
            time.sleep(0)
        self.P = 'P\''
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Done. \nMeasure P\'.....')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Done. Measure \nP\'.....')
        # Вызываем процедуру калибровки для P'
        calibration = self.calibration_all_cuvette()
        # обрабатываем проблему набора давления
        if not calibration == Pressure_Error.No_Error:
            self.calibration_fail(calibration)
            return
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measure P\'..... Done.')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measure P\'..... Done')
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation.....')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation.....')
        # Вызываем процедуру обсчета данных.
        self.calculation()
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation..... Done.')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation..... Done.')
        # Разлокируем остальные вкладки для пользователя.
        self.unblock_other_tabs()
        # Разблокируем кнопки, поля и работу с таблицей на текущей вкладке.
        self.unblock_userinterface()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'Interface unlocked, Current tab = Calibration')
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calibration finished')

    """Метод обработки прерывания калибровки из-за низкого давления"""
    def calibration_fail(self, calibration):
        self.set_test_on(False)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calibration..... Fail.')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calibration..... Fail.')
        # выключаем все порты
        self.gpio.all_port_off()
        # Разлокируем остальные вкладки для пользователя.
        self.unblock_other_tabs()
        # Разблокируем кнопки, поля и работу с таблицей на текущей вкладке.
        self.unblock_userinterface()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'Interface unlocked, Current tab = Calibration')
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calibration interrupted')
        if calibration == Pressure_Error.Pressure_Set:
            self.fail_pressure_set.emit()
        if calibration == Pressure_Error.Get_Balance:
            self.fail_get_balance.emit()

    """Метод калибровки для кюветы любого размера"""
    def calibration_all_cuvette(self):
        """Калибровка Большой/Средней/Малой кюветы

        -Открыть К1, К2, К3
        -Ждать 10 сек
        - Открыть К4
        -Ждать 5 сек
        - Закрыть К1
        -Ждать 5 сек
        - Закрыть К3, К4, К2

        For i = 1 to количество измерений
        - Ждать 2 сек
        - Измерить Р0
        - Открыть К1, К2
        -Ждать Т1
        - Закрыть К1
        -Ждать 2 сек
        -Закрыть К2
        -Ждать 2 сек
        -Измерить Р1
        Для больших и средних:          Открыть К2
        - Открыть К3
        - Ждать Т2
        Для больших и средних:          Закрыть К2
        - Закрыть К3
        - Ждать 2 сек
        -Измерить Р2
        - Открыть К2, К3, К4
        -Ждать Т4
        -Закрыть К2, К3, К4
        Next i
            """
        self.gpio.port_on(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K1 = {0}'.format(str(self.ports[Ports.K1.value])))
        self.gpio.port_on(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K2 = {0}'.format(str(self.ports[Ports.K2.value])))
        self.gpio.port_on(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K3 = {0}'.format(str(self.ports[Ports.K3.value])))
        self.time_sleep(10)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(str(10)))
        self.gpio.port_on(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K4 = {0}'.format(str(self.ports[Ports.K4.value])))
        self.time_sleep(5)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(str(5)))
        self.gpio.port_off(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K1 = {0}'.format(str(self.ports[Ports.K1.value])))
        self.time_sleep(5)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(str(5)))
        self.gpio.port_off(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K3 = {0}'.format(str(self.ports[Ports.K3.value])))
        self.gpio.port_off(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K4 = {0}'.format(str(self.ports[Ports.K4.value])))
        self.gpio.port_off(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K2 = {0}'.format(str(self.ports[Ports.K2.value])))
        # Цикл по заданному количеству измерений
        for i in range(self.number_of_measurements):
            # Создаем пустой экземпляр для записей результатов калибровки как новый элемент списка калибровок
            self.calibrations.append(Calibration())
            # Запоминаем его индекс в списке
            l = len(self.calibrations) - 1
            # Сразу вносим информацию по тому какое давление мы измеряем P или P'
            self.calibrations[l].measurement = self.P
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(str(2)))
            # Замеряем давление P0/P0', ('p0') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.calibrations[l].p0 = self.spi.get_pressure('p0')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured{0} {1} : p0 = {2}'.format(str(i), self.calibrations[l].measurement,
                                                                           str(self.calibrations[l].p0)))
            self.gpio.port_on(self.ports[Ports.K1.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K1 = {0}'.format(str(self.ports[Ports.K1.value])))
            self.gpio.port_on(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K2 = {0}'.format(str(self.ports[Ports.K2.value])))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We expect a set of pressure')
            p, success, duration = self.gain_Pmeas()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                           f'pressure set - fail, P = {str(p)}/{str(self.Pmeas)}, '
                                           f'time has passed: {str(duration)}')
                return Pressure_Error.Pressure_Set
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       f'pressure set - success, P = {str(p)}/{str(self.Pmeas)}, '
                                       f'time has passed: {str(duration)}')
            self.gpio.port_off(self.ports[Ports.K1.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K1 = {0}'.format(str(self.ports[Ports.K1.value])))
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(str(2)))
            self.gpio.port_off(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K2 = {0}'.format(str(self.ports[Ports.K2.value])))
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(str(2)))
            # Замеряем давление P1/P1', ('p1') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.calibrations[l].p1 = self.spi.get_pressure('p1')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured{0} {1} : p1 = {2}'.format(str(i), self.calibrations[l].measurement,
                                                                        str(self.calibrations[l].p1)))
            # только для большой и средней кюветы
            if not self.cuvette == Сuvette.Small:
                self.gpio.port_on(self.ports[Ports.K2.value])
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                           'Open K2 = {0}'.format(str(self.ports[Ports.K2.value])))
            self.gpio.port_on(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K3 = {0}'.format(str(self.ports[Ports.K3.value])))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            balance, success, duration = self.get_balance()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                           f'pressure stops changing - fail, balance = {str(balance)}/{str(0.01)}, '
                                           f'time has passed: {str(duration)}')
                return Pressure_Error.Get_Balance
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       f'pressure stops changing - success, P = {str(balance)}/{str(0.01)}, '
                                       f'time has passed: {str(duration)}')
            # только для большой и средней кюветы
            if not self.cuvette == Сuvette.Small:
                self.gpio.port_off(self.ports[Ports.K2.value])
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                           'Close K2 = {0}'.format(str(self.ports[Ports.K2.value])))
            self.gpio.port_off(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K3 = {0}'.format(str(self.ports[Ports.K3.value])))
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(str(2)))
            # Замеряем давление P2/P2', ('p2') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.calibrations[l].p2 = self.spi.get_pressure('p2')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured{0} {1} : p2 = {2}'.format(str(i), self.calibrations[l].measurement,
                                                                           str(self.calibrations[l].p2)))
            self.gpio.port_on(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K2 = {0}'.format(str(self.ports[Ports.K2.value])))
            self.gpio.port_on(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K3 = {0}'.format(str(self.ports[Ports.K3.value])))
            self.gpio.port_on(self.ports[Ports.K4.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Open K4 = {0}'.format(str(self.ports[Ports.K4.value])))
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'We wait until the pressure stops changing.')
            balance, success, duration = self.get_balance()
            if not success:
                self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                           f'pressure stops changing - fail, balance = {str(balance)}/{str(0.01)}, '
                                           f'time has passed: {str(duration)}')
                return Pressure_Error.Get_Balance
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       f'pressure stops changing - success, P = {str(balance)}/{str(0.01)}, '
                                       f'time has passed: {str(duration)}')
            self.gpio.port_off(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K2 = {0}'.format(str(self.ports[Ports.K2.value])))
            self.gpio.port_off(self.ports[Ports.K3.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K3 = {0}'.format(str(self.ports[Ports.K3.value])))
            self.gpio.port_off(self.ports[Ports.K4.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K4 = {0}'.format(str(self.ports[Ports.K4.value])))
            P0 = self.calibrations[l].p0
            P1 = self.calibrations[l].p1
            P2 = self.calibrations[l].p2
            # Считаем отношение давлений.
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation ratio.....')
            try:
                ratio = round((P1 - P0) / (P2 - P0), 3)
            except ArithmeticError:
                self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                     'Division by zero when calculating ratio, '
                                     'denominator: (P2={0} - P0={1})={2}'.format(str(P2), str(P0), str(P2-P0)))
                ratio = 0
            self.calibrations[l].ratio = ratio
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured{0} {1} : ratio = {2}'.format(str(i), self.calibrations[l].measurement,
                                                                           str(self.calibrations[l].ratio)))
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation ratio.....Done')
            # deviation мы пока не можем посчитать, так что присваиваем ему None
            self.calibrations[l].deviation = None
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Add calibration data to the table.....')
            # Добавляем полученные измерения калибровки в таблицу
            self.table.add_calibration(self.calibrations[l])
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Add calibration data to the table.....'
                                                                             'Done')
        return Pressure_Error.No_Error

    """Метод для обработки ожидания. Для тестового режима программыожидание - опускается"""
    def time_sleep(self, t):
        if not self.is_test_mode():
            time.sleep(t)

    """Метод обсчета полученных данных. Так как все данные хранятся в таблице с динамическим пересчетом, 
                                                                                    мы просто вызываем этот пересчет"""
    def calculation(self):
        self.table.recalculation_results()

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
                                     f'Division by zero when calculating balance, denominator: ((p_next = {p_next} - '
                                     f'p_previous = {p_previous}) / p_previous = {p_previous}')
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

