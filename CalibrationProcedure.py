#!/usr/bin/python
# coding=utf-8
import datetime
import inspect
import math
import os
import time
import configparser
import threading

from Calibration import Calibration
from MeasurementProcedure import Сuvette, Ports, Abort_Type

"""Проверка и комментари: 19.01.2019"""

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
        self.set_calibration_results - ссылка на СИГНАЛ, для вывода результатов калибровки на форму программы
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
        self.Vss - float, сюда записываются данные стандартного образца, введенные пользователем. Это происходит в Main.py 
        непосредственно в момент ввода данных, так как процедура пересчета вызывается и вне калибровки и в нее нельзя 
                                                                                    передавать переменные из калибровки.
        self.c_Vc - float, сюда записывается рассчитанное в результате калибровки значение объема кюветы.
        self.c_Vd - float, сюда записывается рассчитанное в результате калибровки значение дополнительного объема кюветы.
"""

"""Функция для перевода минут, вводимых пользователем, в секунды, используемые программой"""
def set_time_min_to_sec(min):
    sec = min * 60
    return sec


class CalibrationProcedure(object):
    """docstring"""

    """Конструктор класса. Поля класса"""
    def __init__(self, main):
        self.main = main
        self.table = self.main.t2_tableCalibration
        self.spi = self.main.spi
        self.gpio = self.main.gpio
        self.ports = self.main.ports
        self.block_other_tabs = self.main.block_other_tabs_signal
        self.block_userinterface = self.main.block_userinterface_calibration_signal
        self.unblock_userinterface = self.main.unblock_userinterface_calibration_signal
        self.unblock_other_tabs = self.main.unblock_other_tabs_signal
        self.message = self.main.message
        self.file = os.path.basename(__file__)
        self.debug_log = self.main.debug_log
        self.measurement_log = self.main.measurement_log
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
        self.is_test_mode = self.main.config.is_test_mode
        self.P = ''
        self.lock = True
        self.test_on = False
        self.fail_pressure_set = self.main.fail_pressure_set
        self.fail_get_balance = self.main.fail_get_balance
        self.fail_let_out_pressure = self.main.fail_let_out_pressure
        self.set_calibration_results = main.calibration_results_message
        self.Vss = 0
        self.c_Vc = 0.0
        self.c_Vd = 0.0
        self.calibration_file = ''
        self.result_file_reader = configparser.ConfigParser()
        self.abort_procedure = self.main.abort_procedure
        self.abort_procedure_on = False

    """Метод для проверки. Возвращает True, если калибровка запущена иначе False"""
    def is_test_on(self):
        result = False
        if self.test_on:
            result = True
        return result

    """Метод для установки состояния переключателя работы калибровки в положение True/False"""
    def set_test_on(self, state):
        self.test_on = state

    """Метод для установки состояния переключателя прерывающего процедуру"""
    def set_abort_procedure(self, s):
        self.abort_procedure_on = s

    """Метод для проверки. Возвращает True, если запущено прерывание процедуры"""
    def is_abort_procedure(self):
        result = False
        if self.abort_procedure_on:
            result = True
        return result

    """Метод для приостановки процедуры калибровки, чтобы пользователь мог положить образец в кювету"""
    def set_lock(self):
        self.lock = True

    """Метод для возобновления процедуры калибровки, после того как пользователь положил образец в кювету"""
    def set_unlock(self):
        self.lock = False

    """Загружаем выбранные на вкладке "Калибровка" установки."""
    def set_settings(self, _cuvette, _number_of_measurements, _sample_volume, _Pmeas):

        # self.test_on и abort_procedure_on должены быть False перед началом калибровки
        self.test_on = False
        self.abort_procedure_on = False
        self.cuvette = _cuvette
        self.number_of_measurements = _number_of_measurements
        self.sample_volume = _sample_volume
        self.Pmeas = _Pmeas

        # Откроем новый файл для записи результатов
        self.new_calibration_file()
        self.save_calibration_result()

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
        # Блокируем остальные вкладки для пользователя.
        self.block_other_tabs.emit()
        # Блокируем кнопки, поля и работу с таблицей на текущей вкладке.
        self.block_userinterface.emit()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Interface locked, Current tab = Calibration')
        self.P = 'P'
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measure P.....')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measure P.....')
        # Вызываем процедуру калибровки для P
        try:
            self.calibration_all_cuvette()
        except Exception as e:
            self.interrupt_procedure(e.args[0])
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
        try:
            self.calibration_all_cuvette()
        except Exception as e:
            self.interrupt_procedure(e.args[0])
            return
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Measure P\'..... Done.')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Measure P\'..... Done')
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation.....')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation.....')
        # Вызываем процедуру обсчета данных.
        try:
            self.calculation()
        except Exception as e:
            self.interrupt_procedure(e.args[0])
            return
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation..... Done.')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation..... Done.')
        # Разлокируем остальные вкладки для пользователя.
        self.unblock_other_tabs.emit()
        # Разблокируем кнопки, поля и работу с таблицей на текущей вкладке.
        self.unblock_userinterface.emit()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'Interface unlocked, Current tab = Calibration')
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calibration finished')

    """Метод обработки прерывания калибровки из-за низкого давления"""
    def interrupt_procedure(self, calibration):
        self.set_test_on(False)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calibration..... ' + calibration.name + '.')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calibration..... ' + calibration.name + '.')
        # выключаем все порты
        self.main.all_port_off()
        # Разлокируем остальные вкладки для пользователя.
        self.unblock_other_tabs.emit()
        # Разблокируем кнопки, поля и работу с таблицей на текущей вкладке.
        self.unblock_userinterface.emit()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'Interface unlocked, Current tab = Calibration')
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'Calibration interrupted')
        if calibration == Abort_Type.Pressure_below_required:
            self.fail_pressure_set.emit()
        if calibration == Abort_Type.Could_not_balance:
            self.fail_get_balance.emit()
        if calibration == Abort_Type.Interrupted_by_user:
            self.abort_procedure.emit()
        if calibration == Abort_Type.Let_out_pressure_fail:
            self.fail_let_out_pressure.emit()

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
        self.time_sleep(10)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(10))
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.check_for_interruption()
        self.time_sleep(5)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(5))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.check_for_interruption()
        self.time_sleep(5)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(5))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K3.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K3 = {0}'.format(self.ports[Ports.K3.value]))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K4.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K4 = {0}'.format(self.ports[Ports.K4.value]))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K2.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
        # Цикл по заданному количеству измерений
        self.check_for_interruption()
        for i in range(self.number_of_measurements):
            # Создаем пустой экземпляр для записей результатов калибровки как новый элемент списка калибровок
            self.calibrations.append(Calibration())
            # Запоминаем его индекс в списке
            l = len(self.calibrations) - 1
            # Сразу вносим информацию по тому какое давление мы измеряем P или P'
            self.calibrations[l].measurement = self.P
            self.check_for_interruption()
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(2))
            # Замеряем давление P0/P0', ('p0') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.check_for_interruption()
            self.calibrations[l].p0 = self.spi.get_pressure('p0')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured{0} {1} : p0 = {2}'.format(i, self.calibrations[l].measurement,
                                                                           self.calibrations[l].p0))
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
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(2))
            self.check_for_interruption()
            self.gpio.port_off(self.ports[Ports.K2.value])
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Close K2 = {0}'.format(self.ports[Ports.K2.value]))
            self.check_for_interruption()
            self.time_sleep(2)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Wait {0} sec'.format(2))
            # Замеряем давление P1/P1', ('p1') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.check_for_interruption()
            self.calibrations[l].p1 = self.spi.get_pressure('p1')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured{0} {1} : p1 = {2}'.format(i, self.calibrations[l].measurement,
                                                                        self.calibrations[l].p1))
            # только для большой и средней кюветы
            if not self.cuvette == Сuvette.Small:
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
                            'pressure stops changing - fail, balance = {0}/{1}, time has '
                            'passed: {2}'.format(balance, 0.01, duration))
                raise Exception(Abort_Type.Could_not_balance)
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                            'pressure stops changing - success, P = {0}/{1}, time has '
                            'passed: {2}'.format(balance, 0.01, duration))
            # только для большой и средней кюветы
            if not self.cuvette == Сuvette.Small:
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
            # Замеряем давление P2/P2', ('p2') - нужно только для тестового режима, чтобы имитировать похожее давление.
            self.check_for_interruption()
            self.calibrations[l].p2 = self.spi.get_pressure('p2')
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured{0} {1} : p2 = {2}'.format(i, self.calibrations[l].measurement,
                                                                           self.calibrations[l].p2))
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
            success, duration = self.let_out_pressure(self.calibrations[i].p0)
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
            P0 = self.calibrations[l].p0
            P1 = self.calibrations[l].p1
            P2 = self.calibrations[l].p2
            # Считаем отношение давлений.
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation ratio.....')
            try:
                ratio = (P1 - P0) / (P2 - P0)
            except ArithmeticError:
                self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                     'Division by zero when calculating ratio, '
                                     'denominator: (P2={0} - P0={1})={2}'.format(P2, P0, (P2-P0)))
                ratio = 0
            self.calibrations[l].ratio = ratio
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Measured{0} {1} : ratio = {2}'.format(i, self.calibrations[l].measurement,
                                                                           self.calibrations[l].ratio))
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation ratio.....Done')
            # deviation мы пока не можем посчитать, так что присваиваем ему None
            self.calibrations[l].deviation = None
            # Добавляем полученные калибровки в таблицу
            self.save_calibration_result()
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Add calibration data to the table.....')
            # Добавляем полученные измерения калибровки в таблицу
            self.table.add_calibration(self.calibrations[l])
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Add calibration data to the table.....')

    """Метод обсчета полученных данных. Так как все данные хранятся в таблице с динамическим пересчетом, 
                                                                                    мы просто вызываем этот пересчет"""
    def calculation(self):
        ratio_sum1 = 0
        ratio_sum2 = 0
        # нам нужно знать сколько в списке калибровок данных на P и P'. Причем нам надо явно получить int,
        # чтобы использовать в качестве счетчика
        num = int(len(self.calibrations) / 2)

        # --------------------------------------------------------------------------------------------------------------

        # заведем переменную для подсчета количества данных списка, включенных в рассчет
        counter1 = 0
        # Считаем среднее отношение для P0, P1 и P2
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation medium_ratio for P.....')
        for i in range(num):
            index = i
            if self.calibrations[index].active:
                # для включенных в рассчет данных суммируем значение отношений
                # и само количество данных включенных в рассчет
                ratio_sum1 += self.calibrations[index].ratio
                counter1 += 1
        try:
            # Рассчитываем среднее отношение для P0, P1 и P2
            medium_ratio1 = ratio_sum1 / counter1
        except ArithmeticError:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Division by zero when calculating medium_ratio1, '
                                 'denominator: counter1={0}'.format(counter1))
            medium_ratio1 = 0
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Measured {0} : Medium ratio = {1}'.format('P', medium_ratio1))
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation medium_ratio for P.....Done')

        # --------------------------------------------------------------------------------------------------------------

        # заведем переменную для подсчета количества данных списка, включенных в рассчет
        counter1 = 0
        # Считаем среднее отношение для P0', P1' и P2'
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation medium_ratio for P\'.....')
        for i in range(num):
            index = i + num
            if self.calibrations[index].active:
                # для включенных в рассчет данных суммируем значение отношений
                # и само количество данных включенных в рассчет
                ratio_sum2 += self.calibrations[index].ratio
                counter1 += 1
        try:
            # Рассчитываем среднее отношение для P0', P1' и P2'
            medium_ratio2 = ratio_sum2 / counter1
        except ArithmeticError:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Division by zero when calculating medium_ratio1, '
                                 'denominator: counter1={0}'.format(counter1))
            medium_ratio2 = 0
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Measured {0} : Medium ratio = {1}'.format('P\'', medium_ratio2))
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation medium_ratio for P\'.....Done')

        # --------------------------------------------------------------------------------------------------------------

        # заведем переменную для подсчета количества данных списка, включенных в рассчет
        counter2 = 0
        # Теперь считаем отклонения для каждой строки для P0, P1 и P2
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation for ALL P.....')
        for i in range(num):
            # Для P  index = i
            index = i
            if not self.calibrations[index].active is None:
                self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation '
                                                                                 'for P[{0}].....'.format(i))
                try:
                    # Рассчитываем отклонение для P
                    deviation1 = (medium_ratio1 - self.calibrations[index].ratio) / medium_ratio1 * 100
                except ArithmeticError:
                    self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                         'Division by zero when calculating deviation1, '
                                         'denominator: medium_ratio1={0}'.format(medium_ratio1))
                    deviation1 = 0
                if self.calibrations[index].active:
                    self.calibrations[index].deviation = deviation1
                    self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                               'Measured{0} {1} : deviation = {2}'.format('P', i, deviation1))
                if not self.calibrations[index].active:
                    self.calibrations[index].deviation = ''
                    self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                               'Measured{0} {1} : this calibration is not active'.format('P', i))
                self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation '
                                                                                 'for P[{0}].....Done'.format(i))
                # Добавляем в таблицу в столбец для отклонений
                self.table.add_item(self.calibrations[index].deviation, counter2, 5, self.calibrations[index].active)
                counter2 += 1
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation for ALL P.....Done')

        # --------------------------------------------------------------------------------------------------------------

        # Теперь считаем отклонения для каждой строки для P0', P1' и P2'
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation for ALL P\'.....')
        for i in range(num):
            # Для P'  index = i + num
            index = i + num
            if not self.calibrations[index].active is None:
                self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation '
                                                                                 'for P\'[{0}].....'.format(i))
                try:
                    # Рассчитываем отклонение для P'
                    deviation2 = (medium_ratio2 - self.calibrations[index].ratio) / medium_ratio2 * 100
                except ArithmeticError:
                    self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                         'Division by zero when calculating deviation2, '
                                         'denominator: medium_ratio2={0}'.format(medium_ratio2))
                    deviation2 = 0
                if self.calibrations[index].active:
                    self.calibrations[index].deviation = deviation2
                    self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                               'Measured{0} {1} : deviation = {2}'.format('P\'', i, deviation2))
                if not self.calibrations[index].active:
                    self.calibrations[index].deviation = ''
                    self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                               'Measured{0} {1} : this calibration is not active'.format('P\'', i))
                self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation '
                                                                                 'for P\'[{0}].....Done'.format(i))
                # Добавляем в таблицу в столбец для отклонений
                self.table.add_item(self.calibrations[index].deviation, counter2, 5, self.calibrations[index].active)
                counter2 += 1
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation for ALL P\'.....Done')

        # --------------------------------------------------------------------------------------------------------------
        # Инициализируем переменные, куда запишем итоги рассчетов
        Vc = 0
        Vd = 0
        # Нам надо рассчитать Vc и Vd, для всех Р со всеми Р’. Т.е. сначала первый набор Р со всеми по очереди Р’,
        # потом второе и так далее. В итоге количество вычислений равно количество измерений в квадрате.
        # В качестве итоговых результатов нам нужны средние значения.
        # Создадим списки для хранения расчетов по всем комбинациям.
        VcTest = []
        VdTest = []
        # переменная для учета количества комбинаций.
        divider = 0
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation Vc & Vd.....')
        for i in range(num):
            index1 = i
            if self.calibrations[index1].active:
                for j in range(num):
                    index2 = j + num
                    if self.calibrations[index2].active:
                        # P
                        P0 = self.calibrations[index1].p0
                        P1 = self.calibrations[index1].p1
                        P2 = self.calibrations[index1].p2
                        # P'
                        P0a = self.calibrations[index2].p0
                        P1a = self.calibrations[index2].p1
                        P2a = self.calibrations[index2].p2

                        # -----------------------------------------------------------------------------------------------------

                        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                             'Calculation Vc0 for P[{0}] & P\'[{1}].....'.format(index1, index2))
                        try:
                            # Рассчитываем Vc0 для текущей комбинации
                            Vc0 = ((P2a - P0a) * self.Vss) / (
                                    (P2a - P0a) * (P2 - P0) / (P1 - P2) + (P2a - P0a) - (P1a - P0a) * (P2 - P0) / (P1 - P2))
                        except ArithmeticError:
                            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                     'Division by zero when calculating Vc0 for P[{0}] & P\'[{1}], '
                                     'denominator: (P2\'={2} - P0\'={3}) * (P2={4} - P0={5}) / (P1={6} - P2={7}) + (P2\'={8} '
                                     '- P0\'={9}) - (P1\'={10} - P0\'={11}) * (P2={12} - P0={13}) / (P1={14} - P2={15}) '
                                     '& (P1={16} - P2={17})={18}'
                                     .format(index1, index2, P2a, P0a, P2, P0, P1, P2, P2a, P0a, P1a, P0a,
                                             P2, P0, P1, P2, P1, P2, (P1 - P2)))
                            Vc0 = 0
                        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                                   'Measured for P[{0}] & P\'[{1}]  : Vc0 = {2}'.format(index1, index2, Vc0))
                        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                             'Calculation Vc0 for P[{0}] & P\'[{1}].....Done'.format(index1, index2))

                        # -----------------------------------------------------------------------------------------------------

                        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                             'Calculation Vd0 for P[{0}] & P\'[{1}].....'.format(index1, index2))
                        try:
                            # Рассчитываем Vd0 для текущей комбинации
                            Vd0 = (P2 - P0) * Vc0 / (P1 - P2)
                        except ArithmeticError:
                            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                    'Division by zero when calculating Vd0 for P[{0}] & P\'[{1}], '
                                    'denominator: (P1={2} - P2={3})={4}'.format(index1, index2, P1, P2, (P1 - P2)))
                            Vd0 = 0
                        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                                   'Measured for P[{0}] & P\'[{1}]  : Vd0 = {2}'.format(index1, index2, Vd0))
                        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                             'Calculation Vd0 for P[{0}] & P\'[{1}].....Done'.format(index1, index2))

                        # -----------------------------------------------------------------------------------------------------

                        # Добавлем Vc0 и Vd0 в списки.
                        VcTest.append(Vc0)
                        VdTest.append(Vd0)
                        # считаем сумму всех Vc0 и Vd0, для посследующего рассчета средних значений.
                        Vc = Vc + Vc0
                        Vd = Vd + Vd0
                        # увеличиваем кол-во комбинаций.
                        divider += 1

        # --------------------------------------------------------------------------------------------------------------
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'Calculation c_Vc.....')
        try:
            # Рассчитываем объем кюветы
            self.c_Vc = Vc / divider
        except ArithmeticError:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Division by zero when calculating c_Vc, denominator: divider={0}'.format(divider))
            self.c_Vc = 0
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Measured : c_Vc = {0}'.format(self.c_Vc))
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'Calculation c_Vc.....Done')

        # -----------------------------------------------------------------------------------------------------

        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'Calculation c_Vd.....')
        try:
            # Рассчитываем доп. объем кюветы
            self.c_Vd = Vd / divider
        except ArithmeticError:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Division by zero when calculating c_Vd, denominator: divider={0}'.format(divider))
            self.c_Vd = 0
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Measured : c_Vd = {0}'.format(self.c_Vd))
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'Calculation c_Vd.....Done')

        # -----------------------------------------------------------------------------------------------------

        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation Vc & Vd.....Done')
        self.save_calibration_result()
        # Вызываем вывод результатов на форму.
        self.set_calibration_results.emit()

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
                                     'Division by zero when calculating balance, denominator: ((p_next = {0} - '
                                     'p_previous = {1}) / p_previous = {2}'.format(p_next, p_previous, p_previous))
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

    """Метод получения текущей дате в формате год-месяц-день, так нужно для удобства сортировки файлов в папке"""
    def get_today_date(self):
        logname = datetime.datetime.now().strftime("%Y-%m-%d")
        return logname

    """Метод устанавливает текущий файл калибровки. В него можно записать данные и из него можно загрузить их"""
    def set_calibration_file(self, file_name):
        self.calibration_file = file_name

    """Метод создает новый текущий файл калибровки. В него можно записать данные и из него можно загрузить их"""
    def new_calibration_file(self):
        # проверим наличие каталога, если его нет - создадим.
        self.check_result_dir()
        find_name = True
        number = 0

        # Определяем следующее подходящее имя файла.
        while find_name:
            number += 1
            # для нормального режима (Linux) нужны такие команды:
            self.calibration_file = os.path.join(os.getcwd(), 'Results', 'Calibrations', 'Calibration' + ' - ' + self.get_today_date() + ' - ' + str(
                number) + '.result')
            find_name = os.path.isfile(self.calibration_file)
        self.result_file_reader.read(self.calibration_file, encoding = 'WINDOWS-1251')

        # # Ветка для программы в тестовом режиме.
        # if self.is_test_mode():
        #     # Определяем следующее подходящее имя файла.
        #     while find_name:
        #         number += 1
        #         # для тестового режима (Windows) нужны такие команды:
        #         self.calibration_file = os.getcwd() + '\Results\Calibrations\Calibration' + ' - ' + self.get_today_date() + ' - ' + str(
        #             number) + '.result'
        #         find_name = os.path.isfile(self.calibration_file)
        #     self.result_file_reader.read(self.calibration_file)
        #
        # # Ветка для программы в нормальном режиме.
        # if not self.is_test_mode():
        #     # Определяем следующее подходящее имя файла.
        #     while find_name:
        #         number += 1
        #         # для нормального режима (Linux) нужны такие команды:
        #         self.calibration_file = os.getcwd() + '/Results/Calibrations/Calibration' + ' - ' + self.get_today_date() + ' - ' + str(
        #             number) + '.result'
        #         find_name = os.path.isfile(self.calibration_file)
        #     self.result_file_reader.read(self.calibration_file, encoding = 'WINDOWS-1251')
        with open(self.calibration_file, "w") as fh:
            self.result_file_reader.write(fh)

    """Проверим наличие каталога, если его нет - создадим."""
    def check_result_dir(self):
        if not os.path.isdir(os.path.join(os.getcwd(), 'Results', 'Calibrations')):
            os.makedirs(os.path.join(os.getcwd(), 'Results', 'Calibrations'))
        # if self.is_test_mode():
        #     if not os.path.isdir(os.getcwd() + '\Results\Calibrations'):
        #         os.makedirs(os.getcwd() + '\Results\Calibrations')
        # if not self.is_test_mode():
        #     if not os.path.isdir(os.getcwd() + '/Results/Calibrations'):
        #         os.makedirs(os.getcwd() + '/Results/Calibrations')

    """Метод для сохранения калибровки в файл"""
    def save_calibration_result(self):
        self.result_file_reader.read(self.calibration_file)
        self.update_calibration_file('SourceData', 'cuvette', str(self.cuvette.value))
        self.update_calibration_file('SourceData', 'number_of_measurements', str(self.number_of_measurements))
        self.update_calibration_file('SourceData', 'sample', str(self.sample_volume))
        for i in range(len(self.calibrations)):
            self.update_calibration_file('Calibration-' + str(i), 'P', self.calibrations[i].measurement)
            self.update_calibration_file('Calibration-' + str(i), 'p0', str(self.calibrations[i].p0))
            self.update_calibration_file('Calibration-' + str(i), 'p1', str(self.calibrations[i].p1))
            self.update_calibration_file('Calibration-' + str(i), 'p2', str(self.calibrations[i].p2))
            self.update_calibration_file('Calibration-' + str(i), 'ratio', str(self.calibrations[i].ratio))
            self.update_calibration_file('Calibration-' + str(i), 'deviation', str(self.calibrations[i].deviation))
            self.update_calibration_file('Calibration-' + str(i), 'active', str(self.calibrations[i].active))
        self.update_calibration_file('CalibrationResult', 'Vc', str(self.c_Vc))
        self.update_calibration_file('CalibrationResult', 'Vd', str(self.c_Vd))
        os.rename(self.calibration_file, self.calibration_file + "~")
        os.rename(self.calibration_file + ".new", self.calibration_file)
        os.remove(self.calibration_file + "~")

    def update_calibration_file(self, section, val, s):
        if not self.result_file_reader.has_section(section):
            self.result_file_reader.add_section(section)
        self.result_file_reader.set(section, val, str(s))
        with open(self.calibration_file + ".new", "w") as fh:
            self.result_file_reader.write(fh)

    """Метод для загрузки калибровки из файла"""
    def load_calibration_result(self):
        if self.is_test_mode():
            # для тестового режима (Windows) нужны такие команды:
            self.result_file_reader.read(self.calibration_file)
        if not self.is_test_mode():
            # для нормального режима (Linux) нужны такие команды:
            self.result_file_reader.read(self.calibration_file, encoding='utf-8')

        # [SourceData]
        cuvette_type = self.try_load_int('SourceData', 'cuvette')
        if cuvette_type is None:
            self.cuvette = Сuvette.Large
        else:
            self.cuvette = Сuvette(cuvette_type)
        self.number_of_measurements = self.try_load_int('SourceData', 'number_of_measurements')
        self.sample_volume = self.try_load_float('SourceData', 'sample')
        source_data = {
            'cuvette': self.cuvette,
            'number_of_measurements': self.number_of_measurements,
            'sample': self.sample_volume
        }

        calibrations = []
        # [Calibration-0] - [Calibration-(number_of_measurements-1)]
        for i in range(self.number_of_measurements*2):
            p = self.try_load_string('Calibration-' + str(i), 'p')
            p0 = self.try_load_float('Calibration-' + str(i), 'p0')
            p1 = self.try_load_float('Calibration-' + str(i), 'p1')
            p2 = self.try_load_float('Calibration-' + str(i), 'p2')
            ratio = self.try_load_float('Calibration-' + str(i), 'ratio')
            deviation = self.try_load_float('Calibration-' + str(i), 'deviation')
            active = self.try_load_boolean('Calibration-' + str(i), 'active')
            calibrations.append({
                'p': p,
                'p0': p0,
                'p1': p1,
                'p2': p2,
                'ratio': ratio,
                'deviation': deviation,
                'active': active
            })

        # [CalibrationResult]
            self.c_Vc = self.try_load_float('CalibrationResult', 'vc')
            self.c_Vd = self.try_load_float('CalibrationResult', 'vd')
        calibration_result = {
            'vc': self.c_Vc,
            'vd': self.c_Vd
        }
        result = [source_data, calibrations, calibration_result]
        return result

    def get_files_list(self):
        # проверим наличие каталога, если его нет - создадим.
        self.check_result_dir()
        dir = os.path.join(os.getcwd(), 'Results', 'Calibrations')
        # if self.is_test_mode():
        #     dir = os.getcwd() + '\Results\Calibrations\\'
        # if not self.is_test_mode():
        #     dir = os.getcwd() + '/Results/Calibrations/'
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

    """Метод для включения отдельного потока калибровки русского датчика прибора"""

    def start_russian_sensor_calibration(self):
        # Это команда присваивает отдельному потоку исполняемую процедуру измерения
        self.my_russian_sensor_calibration_thread = threading.Thread(target = self.russian_sensor_calibration)
        # Запускаем поток и процедуру калибровки
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Thread "sensor_calibration" started')
        self.my_russian_sensor_calibration_thread.start()

    """Метод для выключения отдельного потока калибровки русского датчика прибора"""
    def close_russian_sensor_calibration(self):
        # Вызываем выключение потока
        self.my_russian_sensor_calibration_thread.join()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Thread "sensor_calibration" finished')

    """поток калибровки русского датчика прибора"""
    def russian_sensor_calibration(self):
        # Вызываем процедуру обсчета данных.
        try:
            self.russian_sensor_calibration_procedure()
        except Exception as e:
            self.interrupt_russian_sensor_calibration_procedure(e.args[0])
            return

    """Метод обработки прерывания калибровки из-за низкого давления"""
    def interrupt_russian_sensor_calibration_procedure(self, error):
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'sensor_calibration..... ' + error.name + '.')
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'sensor_calibration..... ' + error.name + '.')
        # выключаем все порты
        self.main.all_port_off()
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'sensor_calibration interrupted')
        if error == Abort_Type.Pressure_below_required:
            self.fail_pressure_set.emit()
        if error == Abort_Type.Could_not_balance:
            self.fail_get_balance.emit()
        if error == Abort_Type.Interrupted_by_user:
            self.abort_procedure.emit()
        if error == Abort_Type.Let_out_pressure_fail:
            self.fail_let_out_pressure.emit()

    def russian_sensor_calibration_procedure(self):
        """
        При запуске программы:
        Закрыть К2, К3, К4
        Открыть К1
        Процедура набора давления Т1
        Закрыть К1
        Ждать 2 сек
        Открыть К2, К3, К4
        Процедура стабилизации давления Т2
        Ждать 2 секунды
        Закрыть К2, К3, К4
        Измерить Р
        Прибавить к полученному значению 0,167
        вычесть полученное давление при каждом измерении давления
        """
        self.main.progressbar_start.emit(self.main.languages.TitlesForProgressbar_SensorCalibration,
                                   self.main.languages.TitlesForProgressbar_SensorCalibration, 10)
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
        self.check_for_interruption()
        self.gpio.port_on(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Open K1 = {0}'.format(self.ports[Ports.K1.value]))
        self.check_for_interruption()
        p, success, duration = self.gain_Pmeas()
        if not success:
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'pressure set - fail, P = {0}/{1}, time has passed: {2}'.format(p, self.Pmeas,
                                                                                                       duration))
            raise Exception(Abort_Type.Pressure_below_required)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'pressure set - success, P = {0}/{1}, time has passed: {2}'.format(p, self.Pmeas,
                                                                                                      duration))
        self.check_for_interruption()
        self.gpio.port_off(self.ports[Ports.K1.value])
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Close K1 = {0}'.format(self.ports[Ports.K1.value]))
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
        self.check_for_interruption()
        balance, success, duration = self.get_balance()
        if not success:
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'pressure stops changing - fail, balance = {0}/{1}, time has '
                                       'passed: {2}'.format(balance, 0.01, duration))
            raise Exception(Abort_Type.Could_not_balance)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'pressure stops changing - success, P = {0}/{1}, time has '
                                   'passed: {2}'.format(balance, 0.01, duration))
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
        self.check_for_interruption()
        self.time_sleep(2)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Wait {0} sec'.format(2))
        self.check_for_interruption()
        # Замеряем дата с датчика
        self.check_for_interruption()
        data_correction = self.spi.read_channel() - 0.167
        self.spi.set_correct_data(data_correction)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'data_correction = {0}'.format(data_correction))
        self.check_for_interruption()
        self.main.progressbar_exit.emit()
        print("калибровка датчика закончена")

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
