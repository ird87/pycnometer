#!/usr/bin/python
# coding=utf-8
# Главный модуль программы.
import inspect
import os
import sys  # sys нужен для передачи argv в QApplication
import MainWindow  # Это наш конвертированный файл дизайна
import PyQt5
from CalibrationProcedure import CalibrationProcedure
from Config import Configure, Pressure
from Languages import Languages
from Logger import Logger
from MeasurementProcedure import MeasurementProcedure, Сuvette, Sample_preparation
from PyQt5 import QtCore
from PyQt5.QtCore import QRegExp
from PyQt5.QtGui import QIntValidator, QRegExpValidator
from PyQt5.QtWidgets import QMessageBox
from TableCalibration import UiTableCalibration
from TableMeasurement import UiTableMeasurement
"""Проверака и комментари: 13.01.2019"""
"""
"Главный класс. Работа с GUI, управление приложением, обработка ввода пользователя и работы процедур измерений и калибровки"
"""

"""Функция для отображения нужного количества знаков после '.'"""
def toFixed(numObj, digits=0):
    return f"{numObj:.{digits}f}"

"""Функция проверки переменной на тип int"""
def isint(s):
    try:
        int(s)
        return True
    except ValueError:
        return False

"""Функция проверки переменной на тип float"""
def isfloat(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

class Main(PyQt5.QtWidgets.QMainWindow, MainWindow.Ui_MainWindow ):  # название файла с дизайном и название класса в нем.
    # Это сигналы, они получают команду из других модулей и вызывают методы модуля.
    # Вывод модального окна с просьбой положить в кювету образец
    message = PyQt5.QtCore.pyqtSignal()
    # Вывод на вкладку "Измерения" итогов измерений
    measurement_results_message = PyQt5.QtCore.pyqtSignal()
    # Вывод на вкладку "Калибровка" итогов калибровки
    calibration_results_message = PyQt5.QtCore.pyqtSignal()
    # Вывод на вкладку "Ручное управление" замера давления
    set_pressure_message = PyQt5.QtCore.pyqtSignal(list)
    # Вывод на вкладку "Измерение" или "Калибровка" сообщение о неудачном наборе газа
    fail_pressure_set = PyQt5.QtCore.pyqtSignal()
    # Вывод на вкладку "Измерение" или "Калибровка" сообщение о слишком долгом ожидание баланса
    fail_get_balance = PyQt5.QtCore.pyqtSignal()

    """Конструктор класса. Поля класса"""
    def __init__(self):

        # Это здесь нужно для доступа к переменным, методам
        # и т.д. в файле design.py
        super().__init__()
        self.setupUi(self)  # Это нужно для инициализации нашего дизайна

        # Загружаем модуль настройки
        self.config = Configure()

        # Это имя нашего модуля
        self.file = os.path.basename(__file__)

        # Загружаем модуль записи логов программы и сразу устанавливаем настройки
        self.debug_log = Logger('Debug', self.config)
        self.debug_log.setup()

        # Загружаем модуль записи логов прибора и сразу устанавливаем настройки
        self.measurement_log = Logger('Measurement', self.config)
        self.measurement_log.setup()

        # Загружаем таблицу для вкладки "Измерения"
        self.t1_tableMeasurement = UiTableMeasurement(self.measurement_results_message, self.debug_log, self.measurement_log)
        self.t1_tableMeasurement.setupUi(self)
        self.t1_tableMeasurement.retranslateUi(self)

        # Загружаем таблицу для вкладки "Калибровка"
        self.t2_tableCalibration = UiTableCalibration(self.calibration_results_message, self.debug_log, self.measurement_log)
        self.t2_tableCalibration.setupUi(self)
        self.t2_tableCalibration.retranslateUi(self)

        # Загружаем языковой модуль
        self.languages = Languages()

        # Включаем GPIO и SPI модули, в зависимости от активного/неактивного Тестового режима
        if self.config.is_test_mode():
            self.setWindowTitle('*** *** *** ТЕСТОВЫЙ РЕЖИМ *** *** ***')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'The program works in TEST mode.')
            from ModulGPIOtest import GPIO
            from ModulSPItest import SPI
            # Получаем данные о портах из Configure.ini
            self.ports = self.config.get_ports()
            self.gpio = GPIO(self.ports)
            self.gpio.all_port_off()
            self.spi = SPI(self.config, self.debug_log, self.measurement_log, self.set_pressure_message)
            # Это стартовое заполнение таблиц для тестового режима
            # for i in range(10):
            #     m = self.spi.generate_data(i)
            #     measurement = Measurement()
            #     measurement.set_measurement(m[0], m[1], m[2], m[3], m[4], m[5])
            #     self.t1_tableMeasurement.add_measurement(measurement)
            # for i in range(6):
            #     c = self.spi.generate_data(i)
            #     calibration = Calibration()
            #     calibration.set_calibration(c[0], c[1], c[2], c[3], c[4], c[5])
            #     self.t2_tableCalibration.add_calibration(calibration)
        if not self.config.is_test_mode():
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'The program works in NORMAL mode.')
            from ModulGPIO import GPIO
            from ModulSPI import SPI
            # Получаем данные о портах из Configure.ini
            self.ports = self.config.get_ports()
            self.gpio = GPIO(self.ports)
            self.gpio.all_port_off()
            self.spi = SPI(self.config, self.debug_log, self.measurement_log, self.set_pressure_message)
        # На будущее сохраним стандартный стиль поля для ввода, иногда нам нужно будет их выделять, но
        # потом нужно будет вернуться к стандартному стилю.
        self.ss = self.t1_gM_Edit1.styleSheet()
        # (ВАЖНО) Инициализируем все установки
        self.setup()

        # далее подключаем к нашим сигналам, вызываемые ими методами
        # Вывод модального окна с просьбой положить в кювету образец
        self.message.connect(self.on_message, PyQt5.QtCore.Qt.QueuedConnection)
        # Вывод на вкладку "Измерения" итогов измерений
        self.measurement_results_message.connect(self.set_measurement_results, PyQt5.QtCore.Qt.QueuedConnection)
        # Вывод на вкладку "Калибровка" итогов калибровки
        self.calibration_results_message.connect(self.set_calibration_results, PyQt5.QtCore.Qt.QueuedConnection)
        # Вывод на вкладку "Ручное управление" замера давления
        self.set_pressure_message.connect(self.set_pressure, PyQt5.QtCore.Qt.QueuedConnection)
        # Вывод на вкладку "Измерение" или "Калибровка" сообщение о неудачном наборе газа
        self.fail_pressure_set.connect(self.on_message_fail_pressure_set, PyQt5.QtCore.Qt.QueuedConnection)
        # Вывод на вкладку "Измерение" или "Калибровка" сообщение о слишком долгом ожидание баланса
        self.fail_get_balance.connect(self.on_message_fail_get_balance, PyQt5.QtCore.Qt.QueuedConnection)

        # создаем модуль Измерение и передаем туда ссылки на все модули, методы и сигналы с которыми он работает.
        self.measurement_procedure = MeasurementProcedure(self.t1_tableMeasurement, self.spi, self.gpio, self.ports,
                                                          self.block_other_tabs, self.block_userinterface_measurement,
                                                          self.unblock_userinterface_measurement,
                                                          self.unblock_other_tabs, self.debug_log, self.measurement_log,
                                                          self.config.is_test_mode, self.fail_pressure_set, self.fail_get_balance)

        # создаем модуль Измерение и передаем туда ссылки на все модули, методы и сигналы с которыми он работает.
        self.calibration_procedure = CalibrationProcedure(self.t2_tableCalibration, self.spi, self.gpio, self.ports,
                                                          self.block_other_tabs, self.block_userinterface_calibration,
                                                          self.unblock_userinterface_calibration,
                                                          self.unblock_other_tabs, self.message, self.debug_log,
                                                          self.measurement_log, self.config.is_test_mode,
                                                          self.fail_pressure_set, self.fail_get_balance)

        # Нам нужны два Validator'а для установки ограничений на ввод в поля форм.
        # Для int подойдет штатный QIntValidator
        self.onlyInt = QIntValidator()
                                # self.onlyFloat = QDoubleValidator()
                                # переключение на английскую локаль заменяет ',' вместо '.'
                                # local = QtCore.QLocale("en")
                                # self.onlyFloat.setLocale(local)
        # Для float штатный QDoubleValidator не годиться так как принимает ',' вместо '.' и проверяет еще ряд вещей
        # так что делаем свой через регулярные выражения
        rx = QRegExp(r'^[0-9][.]{0,1}[0-9]*$')
        self.onlyFloat = QRegExpValidator(rx, self)

        # Теперь устанавливаем ограничения на ввод
        self.t1_gSP_Edit1.setValidator(self.onlyInt)    # Измерения.    Время подготовки образца.
        self.t1_gM_Edit1.setValidator(self.onlyFloat)   # Измерения.    Масса образца.
        self.t1_gM_Edit2.setValidator(self.onlyInt)     # Измерения.    Количество измерений.
        self.t1_gM_Edit3.setValidator(self.onlyInt)     # Измерения.    Взять последних.
        self.t2_gID_Edit1.setValidator(self.onlyInt)    # Калибровка.   Количество измерений.
        self.t2_gID_Edit2.setValidator(self.onlyFloat)  # Калибровка.   Объем стандартного образца.
        self.t4_MS_Edit1.setValidator(self.onlyInt)     # Настройка.    Длинна импульса.

        # Подключаем к объектам интерфейса методы их обработки.
        self.t1_gM_button1.clicked.connect(self.measurement_procedure_start)    # Измерение.    Начало измерений.
        self.t1_gM_button2.clicked.connect(self.measurement_clear)              # Измерение.    Очистка измерений.
        self.t1_gSP_Edit1.textChanged.connect(self.t1_gSP_Edit1_text_changed)   # Измерение.    Ввод времени подготовки.
        self.t1_gM_Edit1.textChanged.connect(self.t1_gM_Edit1_text_changed)     # Измерение.    Ввод массы образца.
        self.t1_gM_Edit2.textChanged.connect(self.t1_gM_Edit2_text_changed)     # Измерение.    Ввод количество измер.
        self.t1_gM_Edit3.textChanged.connect(self.t1_gM_Edit3_text_changed)     # Измерение.    Ввод взять последних.
        self.t2_gID_button1.clicked.connect(self.calibration_procedure_start)   # Калибровка.   Начало Калибровки.
        self.t2_gID_button2.clicked.connect(self.calibration_clear)             # Калибровка.   Очистка калибровки.
        self.t2_gID_button3.clicked.connect(self.calibration_save)              # Калибровка.   Сохранить результат.
        self.t2_gID_Edit1.textChanged.connect(self.t2_gID_Edit1_text_changed)   # Калибровка.   Ввод количество измер.
        self.t2_gID_Edit2.textChanged.connect(self.t2_gID_Edit2_text_changed)   # Калибровка.   Ввод объема ст. образца.
        self.t3_checkValve1.stateChanged.connect(self.on_off_port1)             # Ручное упр.   Изменение состояние К1.
        self.t3_checkValve2.stateChanged.connect(self.on_off_port2)             # Ручное упр.   Изменение состояние К2.
        self.t3_checkValve3.stateChanged.connect(self.on_off_port3)             # Ручное упр.   Изменение состояние К3.
        self.t3_checkValve4.stateChanged.connect(self.on_off_port4)             # Ручное упр.   Изменение состояние К4.
        self.t3_checkValve5.stateChanged.connect(self.on_off_port5)             # Ручное упр.   Изменение состояние К5.
        self.t4_MS_Edit1.textChanged.connect(self.t4_MS_Edit1_text_changed)     # Настройка.    Длинна импульса.
        self.t4_MS_Edit2.textChanged.connect(self.t4_MS_Edit2_text_changed)     # Настройка.    Pизм.
        self.t4_button_1.clicked.connect(self.option_appy)                      # Настройка.    Применение настроек.
        self.t4_button_2.clicked.connect(self.show_current_settings)            # Настройка.    Отмена изменений.
        self.t4_gMS_cmd1.currentIndexChanged.connect(self.setPressurePmeas)     # Настройка.    изменение ед.изм. давл.
        self.tabPycnometer.currentChanged.connect(self.tab_change)              # Переключение вкладок программы.

    # Отслеживаем активацию окон приложения
    def tab_change(self):
        # Обработка открытия / закрытия вкладки "Ручное управление"
        def manual_control_check():
            # Если мы ушли с вкладки "Ручное управление"
            if not self.tabPycnometer.currentIndex() == 2:
                # Выключаем замер давления
                self.spi.close_test()
                # И выключаем все порты
                self.gpio.all_port_off()

            # Если мы открыли вкладку "Ручное управление"
            if self.tabPycnometer.currentIndex() == 2:
                # Явно выключаем все порты (на всякий случай, они и так должны быть выключены)
                self.gpio.all_port_off()
                # Включаем замер давления
                self.spi.start_test()

        # Обработка открытия вкладки "Настройка"
        def options_check():
            # Если мы перешли на вкладку измерений
            if self.tabPycnometer.currentIndex() == 3:
                # Загружаем текущие настройки в форму программы.
                self.show_current_settings()
        # Вызов внутренних функций метода, расписанных выше.
        manual_control_check()
        options_check()

    # Применяем изменения в настройках программы.
    def option_appy(self):
        # Сначала мы записываем все изменения внутрь файла config.ini
        # используемый язык
        self.config.set_ini('Language', 'language', self.t4_gIS_cmd1.currentText())
        # единица измерения давления
        self.config.set_ini('Measurement', 'pressure', str(self.t4_gMS_cmd1.currentIndex()))
        # количество измерений с датчика, для получения замера давления
        self.config.set_ini('Measurement', 'smq_now', self.t4_gMS_cmd2.currentText())
        # Длинна импульса для Импульсной продувки
        self.config.set_ini('Measurement', 'pulse_length', self.t4_MS_Edit1.text())
        # Давление, которое должен набрать прибор
        Pmeas_const = ''
        p_kPa = 0
        p_Bar = 0
        p_Psi = 0
        data = 0
        s = self.t4_MS_Edit2.text()
        # Если давление измеряется в кПа
        if self.t4_gMS_cmd1.currentIndex() == Pressure.kPa.value:
            p_kPa = toFixed(float(s), 0)
            data = self.spi.getDataFromkPa(float(p_kPa))
            p_Bar = toFixed(self.spi.getBar(data), 2)
            p_Psi = toFixed(self.spi.getPsi(data), 1)
        # Если давление измеряется в Бар
        if self.t4_gMS_cmd1.currentIndex() == Pressure.Bar.value:
            p_Bar = toFixed(float(s), 2)
            data = self.spi.getDataFromBar(float(p_Bar))
            p_kPa = toFixed(self.spi.getkPa(data), 0)
            p_Psi = toFixed(self.spi.getPsi(data), 1)
        # Если давление измеряется в psi
        if self.t4_gMS_cmd1.currentIndex() == Pressure.Psi.value:
            p_Psi = toFixed(float(s), 1)
            data = self.spi.getDataFromPsi(float(p_Psi))
            p_Bar = toFixed(self.spi.getBar(data), 2)
            p_kPa = toFixed(self.spi.getkPa(data), 0)

        Pmeas_const = f'[{p_kPa}, {p_Bar}, {p_Psi}]'
        self.config.set_ini('Measurement', 'Pmeas', Pmeas_const)
        # А потом вызываем метод, который загружает и применяет все настройки из файла config.ini
        self.setup()

    # Применение к программе настроек, хранящихся в config.ini
    def setup(self):
        # загружаем настройки измерений
        self.config.set_measurement()
        # применяем настройки изменений
        self.spi.set_option()
        # вызываем метод устанавливающий язык приложения
        self.config.set_language()
        # подключаем к языковому модулю файл языка соответсвующий установленному
        self.languages.setup(self.config)
        # Загружаем все данные для этого языка в языковой модуль программы
        self.languages.load(self.config)
        # Применяем данные языкового модуля
        self.set_languages()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'The program setup done.')

    # Этот метод загружает на вкладку настроек все данные с учетом текущих установок
    def show_current_settings(self):
        # обновляем список доступных языков:
        self.config.reload_languages_list()
        # очищаем combobox выбора языка на вкладке
        self.t4_gIS_cmd1.clear()
        # и загружаем в него обновленный список
        for s in self.config.languages:
            s = s.replace('.ini', '')
            self.t4_gIS_cmd1.addItem(s)
        # Устанавливаем в качестве текущего значения текущий язык
        self.t4_gIS_cmd1.setCurrentText(self.config.language)

        # очищаем combobox выбора ед. измерения давления на вкладке
        self.t4_gMS_cmd1.clear()
        # Заполняем его заново:
        for i in self.languages.pressure_setting:
            self.t4_gMS_cmd1.addItem(i)
        # Устанавливаем в качестве текущего значения используемое сейчас значение
        self.t4_gMS_cmd1.setCurrentText(self.languages.pressure_setting[self.config.pressure.value])

        # очищаем combobox выбора количества измерений датчика на вкладке
        self.t4_gMS_cmd2.clear()
        # Заполняем его заново:
        for i in self.config.smq_list:
            self.t4_gMS_cmd2.addItem(str(i))
        # Устанавливаем в качестве текущего значения используемое сейчас значение
        self.t4_gMS_cmd2.setCurrentText(str(self.config.smq_now))

        # Устанавливаем текущее значение длинны импульса (в секундах) в соответсвующее поле.
        self.t4_MS_Edit1.setText(str(self.config.pulse_length))

        # Устанавливаем текущее значение давления, которое должен набрать прибор
        self.setPressurePmeas()

    def setPressurePmeas(self):

        if self.t4_gMS_cmd1.currentIndex() == Pressure.kPa.value:
            # ограничение на ввод давления для кПа 90 - 110
            self.onlyInt = QIntValidator()
            self.t4_MS_Edit2.setValidator(self.onlyInt)
            self.t4_MS_Edit2.setText(toFixed(self.config.Pmeas[self.t4_gMS_cmd1.currentIndex()], 0))
        if self.t4_gMS_cmd1.currentIndex() == Pressure.Bar.value:
            # ограничение на ввод давления для Бар 0.90 - 1.10
            rx = QRegExp(r'^[0-9][.]{0,1}[0-9]*$')
            self.onlyFloat = QRegExpValidator(rx, self)
            self.t4_MS_Edit2.setValidator(self.onlyFloat)
            self.t4_MS_Edit2.setText(toFixed(self.config.Pmeas[self.t4_gMS_cmd1.currentIndex()], 2))
        if self.t4_gMS_cmd1.currentIndex() == Pressure.Psi.value:
            # ограничение на ввод давления для psi 13.0 - 16.0
            rx = QRegExp(r'^[0-9][.]{0,1}[0-9]*$')
            self.onlyFloat = QRegExpValidator(rx, self)
            self.t4_MS_Edit2.setValidator(self.onlyFloat)
            self.t4_MS_Edit2.setText(toFixed(self.config.Pmeas[self.t4_gMS_cmd1.currentIndex()], 1))
        self.t4_gMS_lbl4.setText(self.languages.t4_gMS_lbl4[self.t4_gMS_cmd1.currentIndex()])
        # Проверяем активна ли кнопка "Применить"
        self.set_t4_button_1_enabled()



    # Блок методов для включения/выключения портов
    # K1
    def on_off_port1(self):
        if self.t3_checkValve1.isChecked():
            self.gpio.port_on(self.ports[0])
        else:
            self.gpio.port_off(self.ports[0])

    # K2
    def on_off_port2(self):
        if self.t3_checkValve2.isChecked():
            self.gpio.port_on(self.ports[1])
        else:
            self.gpio.port_off(self.ports[1])

    # K3
    def on_off_port3(self):
        if self.t3_checkValve3.isChecked():
            self.gpio.port_on(self.ports[2])
        else:
            self.gpio.port_off(self.ports[2])

    # K4
    def on_off_port4(self):
        if self.t3_checkValve4.isChecked():
            self.gpio.port_on(self.ports[3])
        else:
            self.gpio.port_off(self.ports[3])

    # K5
    def on_off_port5(self):
        if self.t3_checkValve5.isChecked():
            self.gpio.port_on(self.ports[4])
        else:
            self.gpio.port_off(self.ports[4])

    # Здесь мы считываем и возвращаем все, что ввел пользователь для проведения Измерений.
    def measurement_procedure_get_setting(self):

        # Определяем выбранную Кювету
        if self.t1_gM_cmd1.currentIndex() == Сuvette.Large.value:
            cuvette = Сuvette.Large
        if self.t1_gM_cmd1.currentIndex() == Сuvette.Medium.value:
            cuvette = Сuvette.Medium
        if self.t1_gM_cmd1.currentIndex() == Сuvette.Small.value:
            cuvette = Сuvette.Small

        # Определяем выбранный тип подготовки образца
        if self.t1_gSP_gRB_rb1.isChecked():
            sample_preparation = Sample_preparation.Vacuuming
        if self.t1_gSP_gRB_rb2.isChecked():
            sample_preparation = Sample_preparation.Blow
        if self.t1_gSP_gRB_rb3.isChecked():
            sample_preparation = Sample_preparation.Impulsive_blowing

        # Получаем значение времени, введенное пользователем в минутах
        sample_preparation_time_in_minute = int(self.t1_gSP_Edit1.text())

        # Получаем значение массы, введенное пользователем в граммах
        sample_mass = float(self.t1_gM_Edit1.text())

        # Получаем количество измерений, введенное пользователем
        number_of_measurements = int(self.t1_gM_Edit2.text())

        # Получаем сколько последних измерений надо будет учесть в рассчете (вводиться пользователем)
        take_the_last_measurements = int(self.t1_gM_Edit3.text())

        return cuvette, sample_preparation, sample_preparation_time_in_minute, sample_mass, \
               number_of_measurements, take_the_last_measurements

    # Передаем данные в класс проводящий измерения, и запускаем измерения.
    def measurement_procedure_start(self):
        self.measurement_clear()
        # Получаем данные введенные пользователем
        cuvette, sample_preparation, sample_preparation_time_in_minute, sample_mass, number_of_measurements, \
        take_the_last_measurements = self.measurement_procedure_get_setting()

        # Данные о кювете получаем из файла конфигурации
        VcL = self.config.VcL
        VcM = self.config.VcM
        VcS = self.config.VcS
        VdLM = self.config.VdLM
        VdS = self.config.VdS
        Pmeas = self.config.Pmeas_now
        pulse_length = self.config.pulse_length

        # Устанавливаем настройки Измерений
        self.measurement_procedure.set_settings(cuvette, sample_preparation, sample_preparation_time_in_minute,
                                                sample_mass, number_of_measurements, take_the_last_measurements,
                                                VcL, VcM, VcS, VdLM, VdS, Pmeas, pulse_length)

        # Явно выключаем все порты (на всякий случай, они и так должны быть выключены)
        self.gpio.all_port_off()
        # Запускаем измерения.
        self.measurement_procedure.start_measurements()

    # Здесь мы считываем и возвращаем все, что ввел пользователь для проведения Калибровки.
    def calibration_procedure_get_setting(self):

        # Определяем выбранную Кювету
        if self.t2_gID_cmd1.currentIndex() == Сuvette.Large.value:
            cuvette = Сuvette.Large
        if self.t2_gID_cmd1.currentIndex() == Сuvette.Medium.value:
            cuvette = Сuvette.Medium
        if self.t2_gID_cmd1.currentIndex() == Сuvette.Small.value:
            cuvette = Сuvette.Small

        # Получаем количество измерений, введенное пользователем
        number_of_measurements = int(self.t2_gID_Edit1.text())

        # Получаем значение объема стандартного образца, введенное пользователем
        sample_volume = float(self.t2_gID_Edit1.text())

        return cuvette, number_of_measurements, sample_volume

    # Передаем данные в класс проводящий калибровку, и запускаем калибровку.
    def calibration_procedure_start(self):
        self.calibration_clear()
        # Получаем данные введенные пользователем
        cuvette, number_of_measurements, sample_volume = self.calibration_procedure_get_setting()

        Pmeas = self.config.Pmeas_now

        # Устанавливаем настройки Измерений
        self.calibration_procedure.set_settings(cuvette, number_of_measurements, sample_volume, Pmeas)

        # Явно выключаем все порты (на всякий случай, они и так должны быть выключены)
        self.gpio.all_port_off()
        # Запускаем измерения.
        self.calibration_procedure.start_calibrations()

    # Блокируем кнопки на вкладке измерений
    def block_userinterface_measurement(self):
        self.t1_gSP_Edit1.setEnabled(False)
        self.t1_gM_Edit1.setEnabled(False)
        self.t1_gM_Edit2.setEnabled(False)
        self.t1_gM_Edit3.setEnabled(False)
        self.t1_gSP_gRB_rb1.setEnabled(False)
        self.t1_gSP_gRB_rb2.setEnabled(False)
        self.t1_gSP_gRB_rb3.setEnabled(False)
        self.t1_gM_cmd1.setEnabled(False)
        self.t1_gM_button1.setEnabled(False)
        self.t1_gM_button2.setEnabled(False)
        self.t1_gMI_Edit1.setEnabled(False)
        self.t1_gMI_Edit2.setEnabled(False)
        self.t1_gMI_Edit3.setEnabled(False)
        self.t1_gMI_Edit4.setEnabled(False)
        self.t1_tableMeasurement.popup_menu_enable=False


    # Разблокируем кнопки на вкладке измерений
    def unblock_userinterface_measurement(self):
        self.t1_gSP_Edit1.setEnabled(True)
        self.t1_gM_Edit1.setEnabled(True)
        self.t1_gM_Edit2.setEnabled(True)
        self.t1_gM_Edit3.setEnabled(True)
        self.t1_gSP_gRB_rb1.setEnabled(True)
        self.t1_gSP_gRB_rb2.setEnabled(True)
        self.t1_gSP_gRB_rb3.setEnabled(True)
        self.t1_gM_cmd1.setEnabled(True)
        self.t1_gM_button1.setEnabled(True)
        self.t1_gM_button2.setEnabled(True)
        self.t1_gMI_Edit1.setEnabled(True)
        self.t1_gMI_Edit2.setEnabled(True)
        self.t1_gMI_Edit3.setEnabled(True)
        self.t1_gMI_Edit4.setEnabled(True)
        self.t1_tableMeasurement.popup_menu_enable = True

    # Блокируем кнопки на вкладке измерений
    def block_userinterface_calibration(self):
        self.t2_gID_cmd1.setEnabled(False)
        self.t2_gID_Edit1.setEnabled(False)
        self.t2_gID_Edit2.setEnabled(False)
        self.t2_gID_button1.setEnabled(False)
        self.t2_gID_button2.setEnabled(False)
        self.t2_tableCalibration.popup_menu_enable = False

    def unblock_userinterface_calibration(self):
        self.t2_gID_cmd1.setEnabled(True)
        self.t2_gID_Edit1.setEnabled(True)
        self.t2_gID_Edit2.setEnabled(True)
        self.t2_gID_button1.setEnabled(True)
        self.t2_gID_button2.setEnabled(True)
        self.t2_gID_button3.setEnabled(True)
        self.t2_tableCalibration.popup_menu_enable = True

    # Блокируем остальные вкладки
    def block_other_tabs(self):
        cur_i = self.tabPycnometer.currentIndex()
        for i in range(self.tabPycnometer.count()):
            if not i == cur_i:
                self.tabPycnometer.setTabEnabled(i, False)

    # Разблокируем остальные вкладки
    def unblock_other_tabs(self):
        cur_i = self.tabPycnometer.currentIndex()
        for i in range(self.tabPycnometer.count()):
            if not i == cur_i:
                self.tabPycnometer.setTabEnabled(i, True)

    # Перехватываем закрытие программы и явно выключаем все связанные с RaspberryPi модули и измерения.
    def closeEvent(self, event):
        # Выключаем все порты
        self.gpio.all_port_off()
        # Сбрасываем установки GPIO
        self.gpio.clean_up()
        # Выключаем измерение давления для Ручного управления
        self.spi.close_test()
        # Выключаем процедуру измерений
        self.measurement_procedure.close_measurements()
        # Выключаем процедуру калибровки
        self.calibration_procedure.close_calibrations()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'The program has completed\n'+'-'*75)

    # Применяем данные языкового модуля, для удобства указанны разделы.
    def set_languages(self):
        # [MAIN]
        self.setWindowTitle(self.languages.mainWindow)
        if self.config.is_test_mode():
            # Если работаем в тестовом режиме, указываем это в качестве главного заголовка программы.
            self.setWindowTitle('*** *** *** ТЕСТОВЫЙ РЕЖИМ *** *** ***')
        self.tabPycnometer.setTabText(self.tabPycnometer.indexOf(self.t1), self.languages.t1)
        self.tabPycnometer.setTabText(self.tabPycnometer.indexOf(self.t2), self.languages.t2)
        self.tabPycnometer.setTabText(self.tabPycnometer.indexOf(self.t3), self.languages.t3)
        self.tabPycnometer.setTabText(self.tabPycnometer.indexOf(self.t4), self.languages.t4)

        # [InputMeasurement]
        input_measurement_header = []
        for i in self.languages.Edit_InputMeasurement:
            input_measurement_header.append(i)
        input_measurement_header.append(self.languages.Button_InputMeasurement_OK)
        input_measurement_header.append(self.languages.Button_InputMeasurement_Cancel)
        self.t1_tableMeasurement.LanguagesForInputMeasurement(input_measurement_header)

        # [TAB1]
        table_measurement_header = []
        for i in self.languages.t1_tableMeasurement_Column:
            table_measurement_header.append(i)
        self.t1_tableMeasurement.Languages(table_measurement_header, self.languages.t1_tableMeasurement_popup_Exclude,
                                           self.languages.t1_tableMeasurement_popup_Include,
                                           self.languages.t1_tableMeasurement_popup_Add, self.languages.t1_tableMeasurement_popup_Recount)

        self.t1_groupGeneralInformation.setTitle(self.languages.t1_groupGeneralInformation)
        self.t1_gMI_lbl1.setText(self.languages.t1_gMI_lbl1)
        self.t1_gMI_lbl2.setText(self.languages.t1_gMI_lbl2)
        self.t1_gMI_lbl3.setText(self.languages.t1_gMI_lbl3)
        self.t1_gMI_lbl4.setText(self.languages.t1_gMI_lbl4)

        self.t1_gMI_Edit1.setText('')
        self.t1_gMI_Edit2.setText('')
        self.t1_gMI_Edit3.setText('')
        self.t1_gMI_Edit4.setText('')

        self.t1_groupSamplePreparation.setTitle(self.languages.t1_groupSamplePreparation)
        self.t1_gSP_gRB_rb1.setText(self.languages.t1_gSP_gRB_rb1)
        self.t1_gSP_gRB_rb2.setText(self.languages.t1_gSP_gRB_rb2)
        self.t1_gSP_gRB_rb3.setText(self.languages.t1_gSP_gRB_rb3)
        self.t1_gSP_lbl1.setText(self.languages.t1_gSP_lbl1)

        self.t1_gSP_Edit1.setText('')

        self.t1_groupMeasurementResults.setTitle(self.languages.t1_groupMeasurementResults)
        self.t1_gMR_lbl1.setText(self.languages.t1_gMR_lbl1)
        self.t1_gMR_lbl2.setText(self.languages.t1_gMR_lbl2)
        self.t1_gMR_lbl3.setText(self.languages.t1_gMR_lbl3)
        self.t1_gMR_lbl4.setText(self.languages.t1_gMR_lbl4)

        self.t1_gMR_Edit1.setText('')
        self.t1_gMR_Edit2.setText('')
        self.t1_gMR_Edit3.setText('')
        self.t1_gMR_Edit4.setText('')

        self.t1_groupMeasurement.setTitle(self.languages.t1_groupMeasurement)
        self.t1_gM_lbl1.setText(self.languages.t1_gM_lbl1)
        self.t1_gM_lbl2.setText(self.languages.t1_gM_lbl2)
        self.t1_gM_lbl3.setText(self.languages.t1_gM_lbl3)
        self.t1_gM_lbl4.setText(self.languages.t1_gM_lbl4)

        self.t1_gM_Edit1.setText('')
        self.t1_gM_Edit2.setText('')
        self.t1_gM_Edit3.setText('')

        self.t1_gM_cmd1.clear()
        self.t1_gM_cmd1.addItems(
            [self.languages.t1_gM_cmd1_1, self.languages.t1_gM_cmd1_2, self.languages.t1_gM_cmd1_3])

        self.t1_gM_button1.setText(self.languages.t1_gM_button1)
        self.t1_gM_button2.setText(self.languages.t1_gM_button2)

        # [InputCalibration]
        input_calibration_header = []
        for i in self.languages.Edit_InputCalibration:
            input_calibration_header.append(i)
        input_calibration_header.append(self.languages.Button_InputCalibration_OK)
        input_calibration_header.append(self.languages.Button_InputCalibration_Cancel)
        self.t2_tableCalibration.LanguagesForInputCalibration(input_calibration_header)

        # [TAB2]
        table_calibration_header = []
        for i in self.languages.t2_tableCalibration_Column:
            table_calibration_header.append(i)
        self.t2_tableCalibration.Languages(table_calibration_header, self.languages.t2_tableCalibration_popup_Exclude,
                                           self.languages.t2_tableCalibration_popup_Include,
                                           self.languages.t2_tableCalibration_popup_Add, self.languages.t2_tableCalibration_popup_Recount)

        self.t2_groupCalibratonResult.setTitle(self.languages.t2_groupCalibratonResult)
        self.t2_gCR_lbl1.setText(self.languages.t2_gCR_lbl1)
        self.t2_gCR_lbl2.setText(self.languages.t2_gCR_lbl2)

        self.t2_gCR_Edit1.setText('')
        self.t2_gCR_Edit2.setText('')

        self.t2_groupInitialData.setTitle(self.languages.t2_groupInitialData)
        self.t2_gID_lbl1.setText(self.languages.t2_gID_lbl1)
        self.t2_gID_lbl2.setText(self.languages.t2_gID_lbl2)
        self.t2_gID_lbl3.setText(self.languages.t2_gID_lbl3)

        self.t2_gID_Edit1.setText('')
        self.t2_gID_Edit2.setText('')

        self.t2_gID_cmd1.clear()
        self.t2_gID_cmd1.addItems(
            [self.languages.t2_gID_cmd1_1, self.languages.t2_gID_cmd1_2, self.languages.t2_gID_cmd1_3])

        self.t2_gID_button1.setText(self.languages.t2_gID_button1)
        self.t2_gID_button2.setText(self.languages.t2_gID_button2)
        self.t2_gID_button3.setText(self.languages.t2_gID_button3)

        # [TAB3]
        self.t3_lblPressure1.setText(self.languages.t3_lblPressure1)
        self.t3_lblValve1.setText(self.languages.t3_lblValve1)
        self.t3_lblValve2.setText(self.languages.t3_lblValve2)
        self.t3_lblValve3.setText(self.languages.t3_lblValve3)
        self.t3_lblValve4.setText(self.languages.t3_lblValve4)
        self.t3_lblValve5.setText(self.languages.t3_lblValve5)
        self.t3_lbl_Helium.setText(self.languages.t3_lbl_Helium)
        self.t3_lbl_Atmosphere.setText(self.languages.t3_lbl_Atmosphere)
        self.t3_lbl_Vacuum.setText(self.languages.t3_lbl_Vacuum)

        # [TAB4]
        self.t4_groupInterfaceSettings.setTitle(self.languages.t4_groupInterfaceSettings)
        self.t4_gIS_lbl1.setText(self.languages.t4_gIS_lbl1)
        self.t4_button_1.setText(self.languages.t4_button_1)
        self.t4_button_2.setText(self.languages.t4_button_2)
        self.t4_groupMeasurementSettings.setTitle(self.languages.t4_groupMeasurementSettings)
        self.t4_gMS_lbl1.setText(self.languages.t4_gMS_lbl1)
        self.t4_gMS_lbl2.setText(self.languages.t4_gMS_lbl2)
        self.t4_gMS_lbl3.setText(self.languages.t4_gMS_lbl3)
        self.t4_gMS_lbl4.setText(self.languages.t4_gMS_lbl4[self.config.pressure.value])

        self.show_current_settings()

        # [Menu]
        self.menumenu1.setTitle(self.languages.menu1)
        self.actionmenu1_command1.setText(self.languages.menu1_command1)
        self.menumenu2.setTitle(self.languages.menu2)
        self.menumenu3.setTitle(self.languages.menu3)
        self.menumenu4.setTitle(self.languages.menu4)

        # [Message]
        self.message_headline1 = self.languages.message_headline1
        self.message_txt1 = self.languages.message_txt1
        self.message_txt2 = self.languages.message_txt2
        self.message_txt3 = self.languages.message_txt3

    # Вывод двнных теста давления, вызывается через сигнал.
    def set_pressure(self, s):
        self.t3_lblPressure2.setText(str(s[self.config.pressure.value]))

    # При любом вводе данных на форму Измерения или форму Калибровки мы проверяем можно ли сделать кнопки для начала
    # процедур активными (для этого должны быть заполнены все поля и заполненны корректно)
    def t1_gSP_Edit1_text_changed(self):
        self.set_t1_gM_button1_enabled()

    def t1_gM_Edit1_text_changed(self):
        self.set_t1_gM_button1_enabled()

    def t1_gM_Edit2_text_changed(self):
        self.set_t1_gM_button1_enabled()

    def t1_gM_Edit3_text_changed(self):
        self.set_t1_gM_button1_enabled()

    def t2_gID_Edit1_text_changed(self):
        self.set_t2_gID_button1_enabled()

    # Тут мы сразу должны передать в таблицу калибровки данные. Так надо;)
    def t2_gID_Edit2_text_changed(self):
        self.set_t2_gID_button1_enabled()
        self.t2_tableCalibration.Vss = float(self.t2_gID_Edit2.text())

    def t4_MS_Edit1_text_changed(self):
        self.set_t4_button_1_enabled()

    def t4_MS_Edit2_text_changed(self):
        self.set_t4_button_1_enabled()

    # Проверяем должна ли быть кнопка "Применить" вкладки настройки активна или нет. Устанавливаем нужный статус.
    def set_t4_button_1_enabled(self):
        # заведем логическую переменную, которая передаст кнопке свое состояние в качестве статуса, мы объявим ее True,
        # но если нам хоть что-то не понравится изменим на False/
        enabled = True
        # Заведем переменные для ограничений значений Pизм
        p_min = 0
        p_max = 0
        # Eсли текстовое поле "Длинна импульса" пустое ->
        if len(self.t4_MS_Edit1.text()) < 0:
            # -> кнопка выключена
            enabled = False
            # -> поле выделяем красным
            self.t4_MS_Edit1.setStyleSheet("border: 1px solid red;")
        # Если текстовое поле "Длинна импульса" непустое и введенные данные можно привести к типу int...
        if len(self.t4_MS_Edit1.text()) > 0 and isint(self.t4_MS_Edit1.text()):
            # ...но при этом значение будет меньше 0 ->
            if int(self.t4_MS_Edit1.text()) < 0:
                # -> кнопка выключена
                enabled = False
                # -> поле выделяем красным
                self.t4_MS_Edit1.setStyleSheet("border: 1px solid red;")
            else:
                # ...и при этом значение больше или равно 0 -> данные поля корректны, сбрасываем выделение поля.
                self.t4_MS_Edit1.setStyleSheet(self.ss)
        # Если давление измеряется в кПа
        if self.t4_gMS_cmd1.currentIndex() == Pressure.kPa.value:
            p_min = self.config.pmeas_kPa_min
            p_max = self.config.pmeas_kPa_max
        # Если давление измеряется в Бар
        if self.t4_gMS_cmd1.currentIndex() == Pressure.Bar.value:
            p_min = self.config.pmeas_Bar_min
            p_max = self.config.pmeas_Bar_max
        # Если давление измеряется в psi
        if self.t4_gMS_cmd1.currentIndex() == Pressure.Psi.value:
            p_min = self.config.pmeas_Psi_min
            p_max = self.config.pmeas_Psi_max
        # Eсли текстовое поле "Pизм" пустое ->
        if len(self.t4_MS_Edit2.text()) <= 0:
            # -> кнопка выключена
            enabled = False
            # -> поле выделяем красным
            self.t4_MS_Edit2.setStyleSheet("border: 1px solid red;")
        # Eсли текстовое поле "Pизм" непустое...
        if len(self.t4_MS_Edit2.text()) > 0:
            # ...и введенные данные можно привести к типу float...
            if isfloat(self.t4_MS_Edit2.text()):
                # ...и значение находится в нужных пределах ->
                if p_min <= float(self.t4_MS_Edit2.text()) <= p_max:
                    # -> данные поля корректны, сбрасываем выделение поля.
                    self.t4_MS_Edit2.setStyleSheet(self.ss)
                # ...но значение не находится в нужных пределах ->
                else:
                    # -> кнопка выключена
                    enabled = False
                    # -> поле выделяем красным
                    self.t4_MS_Edit2.setStyleSheet("border: 1px solid red;")
        self.t4_button_1.setEnabled(enabled)

    # Проверяем должна ли быть кнопка "Выполнить" вкладки измерения активна или нет. Устанавливаем нужный статус.
    def set_t1_gM_button1_enabled(self):
        # заведем логическую переменную, которая передаст кнопке свое состояние в качестве статуса, мы объявим ее True,
        # но если нам хоть что-то не понравится изменим на False/
        enabled = True
        # Нам важно чтобы "количество измерений" было не меньше чем "взять последних",
        # для этого нам понадобятся эти переменные.
        a = 0
        b = 0

        # Итак если текстовое поле "Время подготовки обр" пустое ->
        if len(self.t1_gSP_Edit1.text()) <= 0:
            # -> кнопка выключена
            enabled = False
        # Если текстовое поле "Время подготовки обр" непустое и введенные данные можно привести к типу int...
        if len(self.t1_gSP_Edit1.text()) > 0 and isint(self.t1_gSP_Edit1.text()):
            # ...но при этом значение будет меньше 0 ->
            if int(self.t1_gSP_Edit1.text()) < 0:
                # -> кнопка выключена
                enabled = False
                # -> поле выделяем красным
                self.t1_gSP_Edit1.setStyleSheet("border: 1px solid red;")
            else:
                # ...и при этом значение больше или равно 0 -> данные поля корректны, сбрасываем выделение поля.
                self.t1_gSP_Edit1.setStyleSheet(self.ss)

        # Если текстовое поле "Масса образца" пустое ->
        if len(self.t1_gM_Edit1.text()) <= 0:
            # -> кнопка выключена
            enabled = False
        # Если текстовое поле "Масса образца" непустое...
        if len(self.t1_gM_Edit1.text()) > 0:
            # ...и введенные данные можно привести к типу float...
            if isfloat(self.t1_gM_Edit1.text()):
                # ...но при этом значение будет меньше или равно 0 ->
                if float(self.t1_gM_Edit1.text()) <= 0:
                    # -> кнопка выключена
                    enabled = False
                    # -> поле выделяем красным
                    self.t1_gM_Edit1.setStyleSheet("border: 1px solid red;")
                # ...и при этом значение больше 0 -> данные поля корректны, сбрасываем выделение поля.
                else:
                    self.t1_gM_Edit1.setStyleSheet(self.ss)
            # ...но введенные данные нельзя привести к типу float...
            else:
                # -> кнопка выключена
                enabled = False
                # -> поле выделяем красным
                self.t1_gM_Edit1.setStyleSheet("border: 1px solid red;")

        # Если текстовое поле "Количество измерений" пустое ->
        if len(self.t1_gM_Edit2.text()) <= 0:
            # -> кнопка выключена
            enabled = False
        # Если текстовое поле "Количество измерений" непустое...
        else:
            # ...и введенные данные можно привести к типу int...
            if isint(self.t1_gM_Edit2.text()):
                # ...записываем введенное значение
                a = int(self.t1_gM_Edit2.text())
        # Если текстовое поле "Взять последних" пустое ->
        if len(self.t1_gM_Edit3.text()) <= 0:
            # -> кнопка выключена
            enabled = False
        # Если текстовое поле "Взять последних" непустое...
        else:
            # ...и введенные данные можно привести к типу int...
            if isint(self.t1_gM_Edit3.text()):
                # ...записываем введенное значение
                b = int(self.t1_gM_Edit3.text())
        # Если значение текстового поля "Взять последних" больше знаяения текстового поля "Количество измерений",
        # и при этом каждое больше или равно 0 ->
        if a>=0 and b>=0 and b > a:
            # -> кнопка выключена
            enabled = False
            # -> оба поля выделяем красным
            self.t1_gM_Edit2.setStyleSheet("border: 1px solid red;")
            self.t1_gM_Edit3.setStyleSheet("border: 1px solid red;")
        # Рассмотрим другие случаи.
        else:
            # для начала сбрасываем выделение полей...
            self.t1_gM_Edit2.setStyleSheet(self.ss)
            self.t1_gM_Edit3.setStyleSheet(self.ss)
            # ...Если текстовое поле "Количество измерений" непустое и введенные данные можно привести к типу int...
            if len(self.t1_gM_Edit2.text()) > 0 and isint(self.t1_gM_Edit2.text()):
                    # ...но его значение меньше или равно 0 ->
                    if a <= 0:
                        # -> кнопка выключена
                        enabled = False
                        # -> поле выделяем красным
                        self.t1_gM_Edit2.setStyleSheet("border: 1px solid red;")
                    # ...и при этом значение больше 0 -> данные поля корректны, сбрасываем выделение поля.
                    else:
                        self.t1_gM_Edit2.setStyleSheet(self.ss)
            # ...Если текстовое поле "Взять последних" непустое и введенные данные можно привести к типу int...
            if len(self.t1_gM_Edit3.text()) > 0 and isint(self.t1_gM_Edit3.text()):
                    # ...но его значение меньше или равно 0 ->
                    if b <= 0:
                        # -> кнопка выключена
                        enabled = False
                        # -> поле выделяем красным
                        self.t1_gM_Edit3.setStyleSheet("border: 1px solid red;")
                    # ...и при этом значение больше 0 -> данные поля корректны, сбрасываем выделение поля.
                    else:
                        self.t1_gM_Edit3.setStyleSheet(self.ss)

        # Педаем кнопке логическое значение в качестве статуса
        self.t1_gM_button1.setEnabled(enabled)
        # И его же передаем таблице "Измерения" для переключателя определяющего активно ли контекстное меню.
        self.t1_tableMeasurement.popup_menu_enable = enabled

    # Проверяем должна ли быть кнопка "Выполнить" вкладки калибровка активна или нет. Устанавливаем нужный статус.
    def set_t2_gID_button1_enabled(self):
        # заведем логическую переменную, которая передаст кнопке свое состояние в качестве статуса, мы объявим ее True,
        # но если нам хоть что-то не понравится изменим на False/
        enabled = True

        # Итак если текстовое поле "Количество измерений" пустое ->
        if len(self.t2_gID_Edit1.text()) <= 0:
            # -> кнопка выключена
            enabled = False
        # Если текстовое поле "Количество измерений" непустое и введенные данные можно привести к типу int...
        if len(self.t2_gID_Edit1.text()) > 0 and isint(self.t2_gID_Edit1.text()):
            # ...но при этом значение будет меньше или равно 0 ->
            if int(self.t2_gID_Edit1.text()) <= 0:
                # -> кнопка выключена
                enabled = False
                # -> поле выделяем красным
                self.t2_gID_Edit1.setStyleSheet("border: 1px solid red;")
            # ...и при этом значение больше 0 -> данные поля корректны, сбрасываем выделение поля.
            else:
                self.t2_gID_Edit1.setStyleSheet(self.ss)

        # Итак если текстовое поле "Объем стандартного образца" пустое ->
        if len(self.t2_gID_Edit2.text()) <= 0:
            # -> кнопка выключена
            enabled = False
        # Если текстовое поле "Масса образца" непустое...
        if len(self.t2_gID_Edit2.text()) > 0:
            # ...и введенные данные можно привести к типу float...
            if isfloat(self.t2_gID_Edit2.text()):
                # ...но при этом значение будет меньше или равно 0 ->
                if float(self.t2_gID_Edit2.text()) <= 0:
                    # -> кнопка выключена
                    enabled = False
                    # -> поле выделяем красным
                    self.t2_gID_Edit2.setStyleSheet("border: 1px solid red;")
                # ...и при этом значение больше 0 -> данные поля корректны, сбрасываем выделение поля.
                else:
                    self.t2_gID_Edit2.setStyleSheet(self.ss)
            # ...но введенные данные нельзя привести к типу float...
            else:
                # -> кнопка выключена
                enabled = False
                # -> поле выделяем красным
                self.t2_gID_Edit2.setStyleSheet("border: 1px solid red;")

        # Педаем кнопке логическое значение в качестве статуса
        self.t2_gID_button1.setEnabled(enabled)
        # И его же передаем таблице "Калибровка" для переключателя определяющего активно ли контекстное меню.
        self.t2_tableCalibration.popup_menu_enable2 = enabled

    # очищаем таблицу и базу данных измерений
    def measurement_clear(self):
        self.t1_tableMeasurement.measurements.clear()
        self.t1_tableMeasurement.clear_table()

    # очищаем таблицу и базу данных калибровки
    def calibration_clear(self):
        self.t2_gID_button3.setEnabled(False)
        self.t2_tableCalibration.calibrations.clear()
        self.t2_tableCalibration.clear_table()

    # Тут происходит сохранение в config.ini результатов калибровки
    def calibration_save(self):
        Vc = self.t2_tableCalibration.c_Vc
        Vd = self.t2_tableCalibration.c_Vd
        if self.t2_gID_cmd1.currentIndex() == Сuvette.Large.value:
            self.config.set_ini('Measurement', 'VcL', str(Vc))
            self.config.set_ini('Measurement', 'VdLM', str(Vd))
        if self.t2_gID_cmd1.currentIndex() == Сuvette.Medium.value:
            self.config.set_ini('Measurement', 'VcM', str(Vc))
            self.config.set_ini('Measurement', 'VdLM', str(Vd))
        if self.t2_gID_cmd1.currentIndex() == Сuvette.Small.value:
            self.config.set_ini('Measurement', 'VcS', str(Vc))
            self.config.set_ini('Measurement', 'VdS', str(Vd))


    # Вывод двнных Измерений, вызывается через сигнал.
    def set_measurement_results(self):
        # получаем средний объем
        medium_volume = self.t1_tableMeasurement.m_medium_volume
        # получаем среднюю плотность
        medium_density = self.t1_tableMeasurement.m_medium_density
        # получаем СКО
        SD = self.t1_tableMeasurement.m_SD
        # получаем СКО %
        SD_per = self.t1_tableMeasurement.m_SD_per
        # выводим в текстовые поля формы "Измерение"
        self.t1_gMR_Edit1.setText(str(medium_volume))
        self.t1_gMR_Edit2.setText(str(medium_density))
        self.t1_gMR_Edit3.setText(str(SD))
        self.t1_gMR_Edit4.setText(str(SD_per))

    # Вывод двнных Калибровки, вызывается через сигнал.
    def set_calibration_results(self):
        Vc = self.t2_tableCalibration.c_Vc
        Vd = self.t2_tableCalibration.c_Vd
        self.t2_gCR_Edit1.setText(str(Vc))
        self.t2_gCR_Edit2.setText(str(Vd))

    # метод дя создания модального окна для подтверждения пользователя
    def get_messagebox(self, title, message):
        self.my_message = QMessageBox()
        self.my_message.about(self, title, message)

    # Запрос пользователю положить в кювету опытный образец для продолжения калибровки, вызывается через сигнал.
    def on_message(self):
        self.get_messagebox(self.message_headline1, self.message_txt1)
        # возобновляем процесс калибровки
        self.calibration_procedure.set_unlock()

    # Сообщение пользователю о прерывание процедуры из-за неудачи набора давления.
    def on_message_fail_pressure_set(self):
        self.get_messagebox(self.message_headline1, self.message_txt2)

    # Сообщение пользователю о прерывание процедуры из-за слишком долгого ожидания пока давление перестанет меняться.
    def on_message_fail_get_balance(self):
        self.get_messagebox(self.message_headline1, self.message_txt3)


def main():
    app = PyQt5.QtWidgets.QApplication(sys.argv)  # Новый экземпляр QApplication
    window = Main()  # Создаём объект класса Main
    window.show()  # Показываем окно
    app.exec_()  # и запускаем приложение


if __name__ == '__main__':  # Если мы запускаем файл напрямую, а не импортируем
    main()  # то запускаем функцию main()