#!/usr/bin/python
# coding=utf-8
# Главный модуль программы.
import inspect
import ntpath
import os
import shutil
import helper
import sys  # sys нужен для передачи argv в QApplication
import time
from subprocess import Popen, PIPE
from sys import platform
from urllib.request import urlopen
import PyQt5

import Converter
from Calibration import Calibration
from CalibrationProcedure import CalibrationProcedure
from Config import Configure, Pressure
from FileManager import UiFileManager
from Languages import Languages
from Logger import Logger
from Measurement import Measurement
from MeasurementProcedure import MeasurementProcedure, Cuvette, SamplePreparation
from PyQt5 import QtCore, uic
from PyQt5.QtCore import QRegExp, QObject, QEvent, Qt
from PyQt5.QtGui import QIntValidator, QRegExpValidator, QPixmap
from PyQt5.QtWidgets import QMessageBox

import ModulWIFI
from Progressbar import UiProgressbar
from TableCalibration import UiTableCalibration
from TableMeasurement import UiTableMeasurement
from Controller import Controller

"""Проверака и комментари: 23.01.2019"""
"""
"Главный класс. Работа с GUI, управление приложением, обработка ввода пользователя и работы процедур измерений и калибровки"
"""


def clickable(widget):
    class Filter(QObject):
        clicked = PyQt5.QtCore.pyqtSignal()

        def eventFilter(self, obj, event):
            if obj == widget:
                if event.type() == QEvent.MouseButtonDblClick:
                    if obj.rect().contains(event.pos()):
                        self.clicked.emit()
                        # The developer can opt for .emit(obj) to get the object within the slot.
                        return True
            return False

    filter = Filter(widget)
    widget.installEventFilter(filter)
    return filter.clicked


class Main(PyQt5.QtWidgets.QMainWindow):  # название файла с дизайном и название класса в нем.

    # Это сигналы, они получают команду из других модулей и вызывают методы модуля.
    # Вывод модального окна с просьбой положить в кювету образец
    message = PyQt5.QtCore.pyqtSignal()
    # Вывод на вкладку "Измерения" итогов измерений
    measurement_results_message = PyQt5.QtCore.pyqtSignal()
    # Вывод на вкладку "Калибровка" итогов калибровки
    calibration_results_message = PyQt5.QtCore.pyqtSignal()
    # Вывод на вкладку "Ручное управление" замера давления
    set_pressure_message = PyQt5.QtCore.pyqtSignal(float)
    # Вывод на вкладку "Измерение" или "Калибровка" сообщение о неудачном наборе газа
    fail_pressure_set = PyQt5.QtCore.pyqtSignal()
    # Вывод на вкладку "Измерение" или "Калибровка" сообщение о слишком долгом ожидание баланса
    fail_get_balance = PyQt5.QtCore.pyqtSignal()
    # Вывод на вкладку "Измерение" или "Калибровка" сообщение о прерывании процедуры пользователем
    abort_procedure = PyQt5.QtCore.pyqtSignal()
    # Вывод на вкладку "Измерение" или "Калибровка" сообщение о прерывании процедуры из-за проблем со спуском давления.
    fail_let_out_pressure = PyQt5.QtCore.pyqtSignal()
    # Вывод прогрессбара для подготовки образца.
    progressbar_start = PyQt5.QtCore.pyqtSignal(str, str, int)
    progressbar_change = PyQt5.QtCore.pyqtSignal(int)
    progressbar_exit = PyQt5.QtCore.pyqtSignal()
    block_other_tabs_signal = PyQt5.QtCore.pyqtSignal()
    unblock_other_tabs_signal = PyQt5.QtCore.pyqtSignal()
    block_userinterface_measurement_signal = PyQt5.QtCore.pyqtSignal()
    unblock_userinterface_measurement_signal = PyQt5.QtCore.pyqtSignal()
    block_userinterface_calibration_signal = PyQt5.QtCore.pyqtSignal()
    unblock_userinterface_calibration_signal = PyQt5.QtCore.pyqtSignal()
    unblock_t1_gM_button4_signal = PyQt5.QtCore.pyqtSignal()

    """Конструктор класса. Поля класса"""

    def __init__(self):

        # Это здесь нужно для доступа к переменным, методам
        # и т.д. в файле design.py
        super(Main, self).__init__()
        uic.loadUi('ui/MainWindow.ui', self)
        self.setWindowState(Qt.WindowMaximized)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.controller = Controller
        self.wifi = False
        # Загружаем модуль настройки
        self.config = Configure()
        # загружаем настройки программы
        self.config.load_application_config()
        # Это имя нашего модуля
        self.file = os.path.basename(__file__)

        # Загружаем модуль записиt1_gM_cmd1 логов программы и сразу устанавливаем настройки
        self.debug_log = Logger('Debug', self.config)
        self.debug_log.setup()

        # Загружаем модуль записи логов прибора и сразу устанавливаем настройки
        self.measurement_log = Logger('Measurement', self.config)
        self.measurement_log.setup()

        # Загружаем таблицу для вкладки "Измерения"
        self.t1_tableMeasurement = UiTableMeasurement(self)
        self.t1_tableMeasurement.setupUi(self)
        self.t1_tableMeasurement.retranslateUi(self)

        # Загружаем таблицу для вкладки "Калибровка"
        self.t2_tableCalibration = UiTableCalibration(self)
        self.t2_tableCalibration.setupUi(self)
        self.t2_tableCalibration.retranslateUi(self)

        # Загружаем языковой модуль
        self.languages = Languages()

        # очищаем поля для ввода данных.
        self.initial_field_clearing()

        # Включаем GPIO и SPI модули, в зависимости от активного/неактивного Тестового режима
        if self.config.is_test_mode():
            print('*** *** *** ТЕСТОВЫЙ РЕЖИМ *** *** ***')
            self.setWindowTitle('*** *** *** ТЕСТОВЫЙ РЕЖИМ *** *** ***')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'The program works in TEST mode.')
        if not self.config.is_test_mode():
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'The program works in NORMAL mode.')

        try:
            from ModulGPIO import GPIO
            if self.config.module_spi == "SPI2":
                from ModulSPI_2 import SPI
            elif self.config.module_spi == "SPI2025":
                from ModulSPI_2025 import SPI
            else:
                from ModulSPI import SPI
            # Получаем данные о портах из Configure.ini
            self.valves = self.config.get_valves()
            self.gpio = GPIO(self.config.wait_before_hold, self.valves)
            self.all_port_off()
            self.spi = SPI(self)
        except (ImportError, RuntimeError):
            from ModulGPIOtest import GPIO
            from ModulSPItest import SPI
            # Получаем данные о портах из Configure.ini
            self.valves = self.config.get_valves()
            self.gpio = GPIO(self.config.wait_before_hold, self.valves)
            self.all_port_off()
            self.spi = SPI(self)        
            
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
        # Вывод на вкладку "Измерение" или "Калибровка" сообщение о прерывании процедуры пользователем
        self.abort_procedure.connect(self.on_message_abort_procedure, PyQt5.QtCore.Qt.QueuedConnection)
        # Вывод на вкладку "Измерение" или "Калибровка" сообщение о прерывании процедуры из-за проблем со спуском давления.
        self.fail_let_out_pressure.connect(self.on_message_fail_let_out_pressure, PyQt5.QtCore.Qt.QueuedConnection)
        # Вывод прогрессбара.
        self.progressbar_start.connect(self.start_progressbar, PyQt5.QtCore.Qt.QueuedConnection)
        self.progressbar_change.connect(self.change_progressbar, PyQt5.QtCore.Qt.QueuedConnection)
        self.progressbar_exit.connect(self.exit_progressbar, PyQt5.QtCore.Qt.QueuedConnection)
        self.block_other_tabs_signal.connect(self.block_other_tabs, PyQt5.QtCore.Qt.QueuedConnection)
        self.unblock_other_tabs_signal.connect(self.unblock_other_tabs, PyQt5.QtCore.Qt.QueuedConnection)
        self.block_userinterface_measurement_signal.connect(self.block_userinterface_measurement,
                                                            PyQt5.QtCore.Qt.QueuedConnection)
        self.unblock_userinterface_measurement_signal.connect(self.unblock_userinterface_measurement,
                                                              PyQt5.QtCore.Qt.QueuedConnection)
        self.block_userinterface_calibration_signal.connect(self.block_userinterface_calibration,
                                                            PyQt5.QtCore.Qt.QueuedConnection)
        self.unblock_userinterface_calibration_signal.connect(self.unblock_userinterface_calibration,
                                                              PyQt5.QtCore.Qt.QueuedConnection)
        self.unblock_t1_gM_button4_signal.connect(self.unblock_t1_gM_button4, PyQt5.QtCore.Qt.QueuedConnection)

        # создаем модуль Измерение и передаем туда ссылку на main.
        self.measurement_procedure = MeasurementProcedure(self)

        # создаем модуль Калибровка и передаем туда ссылку на main.
        self.calibration_procedure = CalibrationProcedure(self)

        # Нам нужны два Validator'а для установки ограничений на ввод в поля форм.
        # Для int подойдет штатный QIntValidator
        self.onlyInt = QIntValidator()
        # self.onlyFloat = QDoubleValidator()
        # переключение на английскую локаль заменяет ',' вместо '.'
        # local = QtCore.QLocale("en")
        # self.onlyFloat.setLocale(local)
        # Для float штатный QDoubleValidator не годиться так как принимает ',' вместо '.' и проверяет еще ряд вещей
        # так что делаем свой через регулярные выражения
        rx = QRegExp(r'^[0-9]*[.]{0,1}[0-9]*$')
        self.onlyFloat = QRegExpValidator(rx, self)

        # Теперь устанавливаем ограничения на ввод
        self.t1_gSP_Edit1.setValidator(self.onlyInt)  # Измерения.    Время подготовки образца.
        self.t1_gM_Edit1.setValidator(self.onlyFloat)  # Измерения.    Масса образца.
        self.t1_gM_Edit2.setValidator(self.onlyInt)  # Измерения.    Количество измерений.
        self.t1_gM_Edit3.setValidator(self.onlyInt)  # Измерения.    Взять последних.
        self.t2_gID_Edit1.setValidator(self.onlyInt)  # Калибровка.   Количество измерений.
        self.t2_gID_Edit2.setValidator(self.onlyFloat)  # Калибровка.   Объем стандартного образца.
        self.t4_MS_Edit1.setValidator(self.onlyInt)  # Настройка.    Длинна импульса.

        # Подключаем к объектам интерфейса методы их обработки.
        self.t1_gM_button1.clicked.connect(self.measurement_procedure_start)  # Измерение.    Начало измерений.
        self.t1_gM_button2.clicked.connect(self.measurement_clear)  # Измерение.    Очистка измерений.
        self.t1_gM_button3.clicked.connect(self.measurement_file_manager_open)  # Измерение.    Окно загрузки файлов.
        self.t1_gM_button4.clicked.connect(self.measurement_stop)  # Измерение.   Прервать измерение.
        self.t1_gMI_Edit1.textChanged.connect(self.t1_gMI_Edit1_text_changed)  # Измерение.    Ввод Оператор.
        self.t1_gMI_Edit2.textChanged.connect(self.t1_gMI_Edit2_text_changed)  # Измерение.    Ввод Организация.
        self.t1_gMI_Edit3.textChanged.connect(self.t1_gMI_Edit3_text_changed)  # Измерение.    Ввод Образец.
        self.t1_gMI_Edit4.textChanged.connect(self.t1_gMI_Edit4_text_changed)  # Измерение.    Ввод Партия/Серия.
        # ------------------------------------------------------------------------------------------------------------
        # Хочу по двойному клику автозаполнение
        clickable(self.t1_gMI_Edit1).connect(self.t1_gMI_Edit1_clicked)  # Измерение.    Ввод Оператор.
        clickable(self.t1_gMI_Edit2).connect(self.t1_gMI_Edit2_clicked)  # Измерение.    Ввод Организация.
        clickable(self.t1_gMI_Edit3).connect(self.t1_gMI_Edit3_clicked)  # Измерение.    Ввод Образец.
        clickable(self.t1_gMI_Edit4).connect(self.t1_gMI_Edit4_clicked)  # Измерение.    Ввод Партия/Серия.
        # ------------------------------------------------------------------------------------------------------------
        self.t2_gCR_button1.clicked.connect(self.calibration_save)  # Калибровка.   Сохранить результат.
        self.t1_gSP_Edit1.textChanged.connect(self.t1_gSP_Edit1_text_changed)  # Измерение.    Ввод времени подготовки.
        self.t1_gM_Edit1.textChanged.connect(self.t1_gM_Edit1_text_changed)  # Измерение.    Ввод массы образца.
        self.t1_gM_Edit2.textChanged.connect(self.t1_gM_Edit2_text_changed)  # Измерение.    Ввод количество измер.
        self.t1_gM_Edit3.textChanged.connect(self.t1_gM_Edit3_text_changed)  # Измерение.    Ввод взять последних.
        self.t2_gID_cmd1.currentIndexChanged.connect(self.t2_gID_cmd1_changed)  # Калибровка.   Выбор кюветы.
        self.t2_gID_button1.clicked.connect(self.calibration_procedure_start)  # Калибровка.   Начало Калибровки.
        self.t2_gID_button2.clicked.connect(self.calibration_clear)  # Калибровка.   Очистка калибровки.
        self.t2_gID_button3.clicked.connect(self.calibration_file_manager_open)  # Калибровка.   Окно загрузки файлов.
        self.t2_gID_button4.clicked.connect(self.calibration_stop)  # Калибровка.   Прервать калибровку.
        self.t2_gID_Edit1.textChanged.connect(self.t2_gID_Edit1_text_changed)  # Калибровка.   Ввод количество измер.
        self.t2_gID_Edit2.textChanged.connect(self.t2_gID_Edit2_text_changed)  # Калибровка.   Ввод объема ст. образца.
        self.t3_checkValve1.stateChanged.connect(self.on_off_port1)  # Ручное упр.   Изменение состояние К1.
        self.t3_checkValve2.stateChanged.connect(self.on_off_port2)  # Ручное упр.   Изменение состояние К2.
        self.t3_checkValve3.stateChanged.connect(self.on_off_port3)  # Ручное упр.   Изменение состояние К3.
        self.t3_checkValve4.stateChanged.connect(self.on_off_port4)  # Ручное упр.   Изменение состояние К4.
        self.t3_checkValve5.stateChanged.connect(self.on_off_port5)  # Ручное упр.   Изменение состояние К5.
        self.t4_gIS_cmd1.currentIndexChanged.connect(self.changed_languare)  # Настройка.    Выбор языка.
        self.t4_MS_Edit1.textChanged.connect(self.t4_MS_Edit1_text_changed)  # Настройка.    Длинна импульса.
        self.t4_MS_Edit2.textChanged.connect(self.t4_MS_Edit2_text_changed)  # Настройка.    Pизм.
        self.t4_button_1.clicked.connect(self.option_appy)  # Настройка.    Применение настроек.
        self.t4_button_2.clicked.connect(self.show_current_settings)  # Настройка.    Отмена изменений.
        self.t4_gMS_cmd1.currentIndexChanged.connect(self.setPressurePmeas)  # Настройка.    изменение ед.изм. давл.
        self.t4_gRS_button1.clicked.connect(self.set_report_header)  # Настройка.    добавить шапку в отчет.
        self.t4_gRS_button2.clicked.connect(self.clear_report_header)  # Настройка.    удалить шапку из отчета.
        self.t4_gRS_button3.clicked.connect(self.set_report_footer)  # Настройка.    добавить подвал в отчет.
        self.t4_gRS_button4.clicked.connect(self.clear_report_footer)  # Настройка.    удалить подвал из отчета.
        self.tabPycnometer.currentChanged.connect(self.tab_change)  # Переключение вкладок программы.
        self.actionmenu4_command1.triggered.connect(self.report_measurment)
        self.actionmenu1_command1.triggered.connect(self.closeEvent)
        self.menubar.setVisible(False)
        self.sensor_calibration = False
        self.progressbar_form = None
        # нам надо откалибровать датчик.
        if not self.config.is_test_mode() and self.config.calibrate_sensor_when_starting:
            self.calibration_procedure.start_russian_sensor_calibration()
        else:
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno, 'data_correction = {0}'.format(self.config.correct_data))

    def start_progressbar(self, title, name, time):
        if not self.config.is_test_mode():
            self.progressbar_form = UiProgressbar(self, title, name, time)
            self.progressbar_form.activate()

    def change_progressbar(self, t):
        if not self.config.is_test_mode() and not self.progressbar_form is None:
            self.progressbar_form.add_progress(t)

    def exit_progressbar(self):
        if not self.config.is_test_mode() and not self.progressbar_form is None:
            self.progressbar_form.exit()
            self.progressbar_form = None

    def changed_languare(self):
        name = self.t4_gIS_cmd1.currentText()
        img = os.path.join(os.getcwd() + "/attachment/" + name + ".png")
        if os.path.isfile(img):
            self.t4_gIS_flag.setPixmap(QPixmap(img))

    # Отслеживаем активацию окон приложения
    def tab_change(self):
        # Обработка открытия / закрытия вкладки "Ручное управление"
        def manual_control_check():
            # Если мы ушли с вкладки "Ручное управление"
            if not self.tabPycnometer.currentIndex() == 2:
                # Выключаем замер давления
                self.spi.close_test()
                # И выключаем все порты
                self.all_port_off()

            # Если мы открыли вкладку "Ручное управление"
            if self.tabPycnometer.currentIndex() == 2:
                # Явно выключаем все порты (на всякий случай, они и так должны быть выключены)
                self.all_port_off()
                # Включаем замер давления
                self.spi.start_test()

        # Обработка открытия вкладки "Настройка"
        def options_check():
            # Если мы перешли на вкладку настроек
            if self.tabPycnometer.currentIndex() == 3:
                # Загружаем текущие настройки в форму программы.
                self.show_current_settings()

        # Обработка открытия вкладки "Калибровка"
        def calibration_check():
            # Если мы открыли вкладку Калибровка
            if self.tabPycnometer.currentIndex() == 1:
                self.VcVd_download_and_display()

        def exit_check():
            # Если мы открыли вкладку Калибровка
            if self.tabPycnometer.currentIndex() == 4:
                self.closeEvent(None)

        # Вызов внутренних функций метода, расписанных выше.
        manual_control_check()
        options_check()
        calibration_check()
        exit_check()

    # Загрузить и отобразить Vc и Vd из конфига.
    def VcVd_download_and_display(self):
        if self.t2_gID_cmd1.currentIndex() == Cuvette.Small.value:
            self.t2_gCR_Edit3.setText(str(self.config.vc_small))
            self.t2_gCR_Edit4.setText(str(self.config.vd_small))
        if self.t2_gID_cmd1.currentIndex() == Cuvette.Medium.value:
            self.t2_gCR_Edit3.setText(str(self.config.vc_medium))
            self.t2_gCR_Edit4.setText(str(self.config.vd_large_and_medium))
        if self.t2_gID_cmd1.currentIndex() == Cuvette.Large.value:
            self.t2_gCR_Edit3.setText(str(self.config.vc_large))
            self.t2_gCR_Edit4.setText(str(self.config.vd_large_and_medium))

    # Применяем изменения в настройках программы.
    def option_appy(self):
        # Сначала мы записываем все изменения в config
        # [Language]
        self.config.language = self.t4_gIS_cmd1.currentText()
        # [Measurement]
        self.config.pressure = Pressure(self.t4_gMS_cmd1.currentIndex())
        self.config.periodicity_of_removal_of_sensor_reading = Converter.str_to_float(self.t4_gMC_Edit1.text())
        self.config.smq_now = self.t4_gMS_cmd2.currentIndex()
        self.config.pulse_length = Converter.str_to_int(self.t4_MS_Edit1.text())
        pressure = Converter.str_to_float(self.t4_MS_Edit2.text())
        unit = self.t4_gMS_cmd1.currentIndex()
        p_kpa = 0
        p_bar = 0
        p_psi = 0
        data = 0
        # If pressure is measured in kPa
        if unit == Pressure.kPa.value:
            p_kpa = helper.to_fixed(pressure, 0)
            data = self.spi.getDataFromkPa(float(p_kpa))
            p_bar = helper.to_fixed(self.spi.getBar(data), 2)
            p_psi = helper.to_fixed(self.spi.getPsi(data), 1)
        # If pressure is measured in Bar
        if unit == Pressure.Bar.value:
            p_bar = helper.to_fixed(pressure, 2)
            data = self.spi.getDataFromBar(float(p_bar))
            p_kpa = helper.to_fixed(self.spi.getkPa(data), 0)
            p_psi = helper.to_fixed(self.spi.getPsi(data), 1)
        # If pressure is measured in psi
        if unit == Pressure.Psi.value:
            p_psi = helper.to_fixed(pressure, 1)
            data = self.spi.getDataFromPsi(float(p_psi))
            p_bar = helper.to_fixed(self.spi.getBar(data), 2)
            p_kpa = helper.to_fixed(self.spi.getkPa(data), 0)
        self.config.set_pmeas(p_kpa, p_bar, p_psi)
        # ManualControl
        self.config.leak_test_when_starting = self.t4_gMC_chb1.isChecked()
        self.config.calibrate_sensor_when_starting = self.t4_gMC_chb2.isChecked()
        # ReportSetup
        self.config.report_measurement_table = self.t4_gRS_chb1.isChecked()
        self.save_header_and_footer()
        self.config.report_header = self.t4_gRS_Edit1.text()
        self.config.report_footer = self.t4_gRS_Edit2.text()
        # SavingResult
        self.config.save_to_flash_drive = self.t4_gSR_chb1.isChecked()
        self.config.send_report_to_mail = self.t4_gSR_chb2.isChecked()
        self.config.email_address = self.t4_gSR_Edit1.text()
        if not (platform == "win32" or "linux") and not self.config.wifi_name == "":
            ssid = ModulWIFI.SearchSSID(self.config.wifi_name)
            ModulWIFI.deleteSSID(ssid, self.config.wifi_pass)
            # os.system('wpa_cli -i wlan0 REMOVE_NETWORK 1')
            ssid = ModulWIFI.SearchSSID(self.t4_gSR_cmd1.currentText())
            ModulWIFI.addSSID(ssid, self.t4_gSR_Edit2.text())
        self.config.wifi_name = self.t4_gSR_cmd1.currentText()
        self.config.wifi_pass = self.t4_gSR_Edit2.text()
        self.config.save_application_config()
        # А потом вызываем метод, который применяет все настройки из файла config.ini
        self.setup()

    # Применение к программе настроек, хранящихся в config.ini
    def setup(self):
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
        if not platform == "win32" and not self.config.wifi_name == "":
            os.system('wpa_cli -p /var/run/wpa_supplicant -i wlan0 ADD_NETWORK 1')
            os.system("wpa_cli -p /var/run/wpa_supplicant -i wlan0 SET_NETWORK 1 ssid '\"{0}\"'".format(self.config.wifi_name))
            os.system("wpa_cli -p /var/run/wpa_supplicant -i wlan0 SET_NETWORK 1 psk  '\"{0}\"'".format(self.config.wifi_pass))
            os.system("wpa_cli -p /var/run/wpa_supplicant -i wlan0 ENABLE_NETWORK 1")
            # os.system("wpa_cli -p /var/run/wpa_supplicant -i wlan0 RECONNECT")
            os.system('wpa_cli -p /var/run/wpa_supplicant -i wlan0 SELECT_NETWORK 1')

            # interface = 'wlan0'
            # name = self.config.wifi_name
            # password = self.config.wifi_pass
            # os.system('iwconfig ' + interface + ' essid ' + name + ' key ' + password)
        #     if not self.config.wifi_name == "":
        #         if self.config.wifi_name in ModulWIFI.SearchNames():
        #             try:
        #                 ModulWIFI.Connect(self.config.wifi_name, self.config.wifi_pass)
        #             except Exception:
        #                 self.get_messagebox(self.message_headline1, self.message_txt6)
        #         else:
        #             self.get_messagebox(self.message_headline1, self.message_txt7)

        self.header_path = ""
        self.footer_path = ""
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
        # self.setPressurePmeas()

        # Устанавливаем Частота съема показания датчика (0.1 - 1.0 сек)
        self.t4_gMC_Edit1.setText(str(self.config.periodicity_of_removal_of_sensor_reading))

        # Проводить ли тест на натекание при запуске прибора
        self.t4_gMC_chb1.setChecked(self.config.leak_test_when_starting)

        # Проводить ли калибровку датчика при запуске прибора
        self.t4_gMC_chb2.setChecked(self.config.calibrate_sensor_when_starting)

        # Выводить ли таблицу с измерениями
        self.t4_gRS_chb1.setChecked(self.config.report_measurement_table)

        # Добавить шапку отчета
        self.t4_gRS_Edit1.setText(self.config.report_header)

        # Добавить подвал отчета
        self.t4_gRS_Edit2.setText(self.config.report_footer)

        # сохранять ли на флешку.
        self.t4_gSR_chb1.setChecked(self.config.save_to_flash_drive)

        # отправлять ли отчет на почту.
        self.t4_gSR_chb2.setChecked(self.config.send_report_to_mail)

        # Адрес почты:
        self.t4_gSR_Edit1.setText(self.config.email_address)
        if not platform == "win32":
            try:
                # Название сети wifi:
                wifi_networks = ModulWIFI.SearchNames()
                self.t4_gSR_cmd1.clear()
                self.t4_gSR_cmd1.addItem("")
                for wifi_network in wifi_networks:
                    self.t4_gSR_cmd1.addItem(wifi_network)
            except:
                pass
            self.t4_gSR_cmd1.setCurrentText(self.config.wifi_name)
            # Пароль от wifi:
            self.t4_gSR_Edit2.setText(self.config.wifi_pass)

    def setPressurePmeas(self):
        if self.t4_gMS_cmd1.currentIndex() == -1: return
        if self.t4_gMS_cmd1.currentIndex() == Pressure.kPa.value:
            # ограничение на ввод давления для кПа 90 - 110
            self.onlyInt = QIntValidator()
            self.t4_MS_Edit2.setValidator(self.onlyInt)

            self.t4_MS_Edit2.setText(str(self.config.pmeas[self.t4_gMS_cmd1.currentIndex()]))
            self.t4_gMS_lbl4.setText("{0} ({1}-{2})".format(self.languages.t4_gMS_lbl4, self.config.pmeas_kpa_min,
                                                            self.config.pmeas_kpa_max))
        if self.t4_gMS_cmd1.currentIndex() == Pressure.Bar.value:
            # ограничение на ввод давления для Бар 0.90 - 1.10
            rx = QRegExp(r'^[0-9][.]{0,1}[0-9]*$')
            self.onlyFloat = QRegExpValidator(rx, self)
            self.t4_MS_Edit2.setValidator(self.onlyFloat)
            self.t4_MS_Edit2.setText(helper.to_fixed(self.config.pmeas[self.t4_gMS_cmd1.currentIndex()], 2))
            self.t4_gMS_lbl4.setText("{0} ({1}-{2})".format(self.languages.t4_gMS_lbl4, self.config.pmeas_bar_min,
                                                            self.config.pmeas_bar_max))
        if self.t4_gMS_cmd1.currentIndex() == Pressure.Psi.value:
            # ограничение на ввод давления для psi 13.0 - 16.0
            rx = QRegExp(r'^[0-9][.]{0,1}[0-9]*$')
            self.onlyFloat = QRegExpValidator(rx, self)
            self.t4_MS_Edit2.setValidator(self.onlyFloat)
            self.t4_MS_Edit2.setText(helper.to_fixed(self.config.pmeas[self.t4_gMS_cmd1.currentIndex()], 1))
            self.t4_gMS_lbl4.setText("{0} ({1}-{2})".format(self.languages.t4_gMS_lbl4, self.config.pmeas_psi_min,
                                                            self.config.pmeas_psi_max))

        # Проверяем активна ли кнопка "Применить"
        self.set_t4_button_1_enabled()

    # Блок методов для включения/выключения портов
    # K1
    def on_off_port1(self):
        if self.t3_checkValve1.isChecked():
            self.gpio.port_on(self.valves[0])
        else:
            self.gpio.port_off(self.valves[0])

    # K2
    def on_off_port2(self):
        if self.t3_checkValve2.isChecked():
            self.gpio.port_on(self.valves[1])
        else:
            self.gpio.port_off(self.valves[1])

    # K3
    def on_off_port3(self):
        if self.t3_checkValve3.isChecked():
            self.gpio.port_on(self.valves[2])
        else:
            self.gpio.port_off(self.valves[2])

    # K4
    def on_off_port4(self):
        if self.t3_checkValve4.isChecked():
            self.gpio.port_on(self.valves[3])
        else:
            self.gpio.port_off(self.valves[3])

    # K5
    def on_off_port5(self):
        if self.t3_checkValve5.isChecked():
            self.gpio.port_on(self.valves[4])
        else:
            self.gpio.port_off(self.valves[4])

    def all_port_off(self):
        self.t3_checkValve1.setChecked(False)
        self.t3_checkValve2.setChecked(False)
        self.t3_checkValve3.setChecked(False)
        self.t3_checkValve4.setChecked(False)
        self.t3_checkValve5.setChecked(False)
        self.gpio.all_port_off()

    # Здесь мы считываем и возвращаем все, что ввел пользователь для проведения Измерений.
    def measurement_procedure_get_setting(self):

        operator = self.t1_gMI_Edit1.text()
        organization = self.t1_gMI_Edit2.text()
        sample = self.t1_gMI_Edit3.text()
        batch_series = self.t1_gMI_Edit4.text()
        cuvette = None
        sample_preparation = None

        # Определяем выбранную Кювету
        if self.t1_gM_cmd1.currentIndex() == Cuvette.Large.value:
            cuvette = Cuvette.Large
        if self.t1_gM_cmd1.currentIndex() == Cuvette.Medium.value:
            cuvette = Cuvette.Medium
        if self.t1_gM_cmd1.currentIndex() == Cuvette.Small.value:
            cuvette = Cuvette.Small

        # Определяем выбранный тип подготовки образца
        if self.t1_gSP_gRB_rb1.isChecked():
            sample_preparation = SamplePreparation.Vacuuming
        if self.t1_gSP_gRB_rb2.isChecked():
            sample_preparation = SamplePreparation.Blow
        if self.t1_gSP_gRB_rb3.isChecked():
            sample_preparation = SamplePreparation.Impulsive_blowing

        # Получаем значение времени, введенное пользователем в минутах
        sample_preparation_time_in_minute = int(self.t1_gSP_Edit1.text())

        # Получаем значение массы, введенное пользователем в граммах
        sample_mass = float(self.t1_gM_Edit1.text())

        # Получаем количество измерений, введенное пользователем
        number_of_measurements = int(self.t1_gM_Edit2.text())

        # Получаем сколько последних измерений надо будет учесть в рассчете (вводиться пользователем)
        take_the_last_measurements = int(self.t1_gM_Edit3.text())

        return operator, organization, sample, batch_series, cuvette, sample_preparation, sample_preparation_time_in_minute, sample_mass, \
               number_of_measurements, take_the_last_measurements

    # Передаем данные в класс проводящий измерения, и запускаем измерения.
    def measurement_procedure_start(self):
        self.measurement_clear()
        # Получаем данные введенные пользователем
        operator, organization, sample, batch_series, cuvette, sample_preparation, sample_preparation_time_in_minute, sample_mass, number_of_measurements, \
        take_the_last_measurements = self.measurement_procedure_get_setting()

        # Данные о кювете получаем из файла конфигурации
        vc_large = self.config.vc_large
        vc_medium = self.config.vc_medium
        vc_small = self.config.vc_small
        vd_large_and_medium = self.config.vd_large_and_medium
        vd_small = self.config.vd_small
        pmeas = self.config.pmeas[self.config.pressure.value]
        pulse_length = self.config.pulse_length

        # Устанавливаем настройки Измерений
        self.measurement_procedure.set_settings(operator, organization, sample, batch_series, cuvette,
                                                sample_preparation, sample_preparation_time_in_minute,
                                                sample_mass, number_of_measurements, take_the_last_measurements,
                                                vc_large, vc_medium, vc_small, vd_large_and_medium, vd_small, pmeas, pulse_length)

        # Явно выключаем все порты (на всякий случай, они и так должны быть выключены)
        self.all_port_off()
        # Запускаем измерения.
        self.measurement_procedure.start_measurements()
        # Делаем вывод отчета доступным.
        self.actionmenu4_command1.setEnabled(True)

    # Здесь мы считываем и возвращаем все, что ввел пользователь для проведения Калибровки.
    def calibration_procedure_get_setting(self):
        cuvette = None
        # Определяем выбранную Кювету
        if self.t2_gID_cmd1.currentIndex() == Cuvette.Large.value:
            cuvette = Cuvette.Large
        if self.t2_gID_cmd1.currentIndex() == Cuvette.Medium.value:
            cuvette = Cuvette.Medium
        if self.t2_gID_cmd1.currentIndex() == Cuvette.Small.value:
            cuvette = Cuvette.Small

        # Получаем количество измерений, введенное пользователем
        number_of_measurements = int(self.t2_gID_Edit1.text())

        # Получаем значение объема стандартного образца, введенное пользователем
        sample_volume = float(self.t2_gID_Edit2.text())

        return cuvette, number_of_measurements, sample_volume

    # Передаем данные в класс проводящий калибровку, и запускаем калибровку.
    def calibration_procedure_start(self):
        self.calibration_clear()
        # Получаем данные введенные пользователем
        cuvette, number_of_measurements, sample_volume = self.calibration_procedure_get_setting()

        pmeas = self.config.pmeas

        # Устанавливаем настройки Измерений
        self.calibration_procedure.set_settings(cuvette, number_of_measurements, sample_volume, pmeas)

        # Явно выключаем все порты (на всякий случай, они и так должны быть выключены)
        self.all_port_off()
        # Запускаем измерения.
        self.calibration_procedure.start_calibrations()

    def block_t1_gM_button4(self):
        self.t1_gM_button4.setEnabled(False)

    def unblock_t1_gM_button4(self):
        self.t1_gM_button4.setEnabled(True)

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
        self.t1_gM_button3.setEnabled(False)
        self.t1_gMI_Edit1.setEnabled(False)
        self.t1_gMI_Edit2.setEnabled(False)
        self.t1_gMI_Edit3.setEnabled(False)
        self.t1_gMI_Edit4.setEnabled(False)
        self.actionmenu4_command1.setEnabled(False)
        self.actionmenu1_command1.setEnabled(False)
        self.tabPycnometer.setTabEnabled(4, False)
        self.t1_tableMeasurement.popup_menu_enable = False

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
        self.t1_gM_button3.setEnabled(True)
        self.block_t1_gM_button4()
        self.t1_gMI_Edit1.setEnabled(True)
        self.t1_gMI_Edit2.setEnabled(True)
        self.t1_gMI_Edit3.setEnabled(True)
        self.t1_gMI_Edit4.setEnabled(True)
        self.actionmenu4_command1.setEnabled(True)
        self.actionmenu1_command1.setEnabled(True)
        self.tabPycnometer.setTabEnabled(4, True)
        self.t1_tableMeasurement.popup_menu_enable = True

    # Блокируем кнопки на вкладке измерений
    def block_userinterface_calibration(self):
        self.t2_gCR_button1.setEnabled(False)
        self.t2_gID_cmd1.setEnabled(False)
        self.t2_gID_Edit1.setEnabled(False)
        self.t2_gID_Edit2.setEnabled(False)
        self.t2_gID_button1.setEnabled(False)
        self.t2_gID_button2.setEnabled(False)
        self.t2_gID_button3.setEnabled(False)
        self.t2_gID_button4.setEnabled(True)
        self.actionmenu1_command1.setEnabled(False)
        self.tabPycnometer.setTabEnabled(4, False)
        self.t2_tableCalibration.popup_menu_enable = False

    def unblock_userinterface_calibration(self):
        self.t2_gCR_button1.setEnabled(True)
        self.t2_gID_cmd1.setEnabled(True)
        self.t2_gID_Edit1.setEnabled(True)
        self.t2_gID_Edit2.setEnabled(True)
        self.t2_gID_button1.setEnabled(True)
        self.t2_gID_button2.setEnabled(True)
        self.t2_gID_button3.setEnabled(True)
        self.t2_gID_button4.setEnabled(False)
        self.actionmenu1_command1.setEnabled(True)
        self.tabPycnometer.setTabEnabled(4, True)
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
        self.all_port_off()
        # Сбрасываем установки GPIO
        self.gpio.clean_up()
        # Выключаем измерение давления для Ручного управления
        self.spi.close_test()
        # Выключаем процедуру измерений
        self.measurement_procedure.close_measurements()
        # Выключаем процедуру калибровки
        self.calibration_procedure.close_calibrations()
        # "Усыпляем" чип датчика перед освобождением пинов
        if hasattr(self, 'spi') and hasattr(self.spi, 'ads'):
            self.spi.ads.cleanup()
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'The program has completed\n' + '-' * 75)
        sys.exit()

    # Поля для ввода данных очищаем только при запуске программы.
    def initial_field_clearing(self):

        # [TAB1]
        self.t1_gMI_Edit1.setText('')
        self.t1_gMI_Edit2.setText('')
        self.t1_gMI_Edit3.setText('')
        self.t1_gMI_Edit4.setText('')
        self.t1_gSP_Edit1.setText('')
        self.t1_gMR_Edit1.setText('')
        self.t1_gMR_Edit2.setText('')
        self.t1_gMR_Edit3.setText('')
        self.t1_gMR_Edit4.setText('')
        self.t1_gM_Edit1.setText('')
        self.t1_gM_Edit2.setText('')
        self.t1_gM_Edit3.setText('')

        # [TAB2]
        self.t2_gCR_Edit1.setText('')
        self.t2_gCR_Edit2.setText('')
        self.t2_gCR_Edit3.setText('')
        self.t2_gCR_Edit4.setText('')
        self.t2_gID_Edit1.setText('')
        self.t2_gID_Edit2.setText('')

        # [TAB4]
        self.t4_gMC_Edit1.setText('')
        self.t4_gRS_Edit1.setText('')
        self.t4_gRS_Edit2.setText('')
        self.t4_gSR_Edit1.setText('')
        self.t4_gSR_Edit2.setText('')

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
        self.tabPycnometer.setTabText(self.tabPycnometer.indexOf(self.t5), self.languages.t5)

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
                                           self.languages.t1_tableMeasurement_popup_Add,
                                           self.languages.t1_tableMeasurement_popup_Recount)

        self.t1_groupGeneralInformation.setTitle(self.languages.t1_groupGeneralInformation)
        self.t1_gMI_lbl1.setText(self.languages.t1_gMI_lbl1)
        self.t1_gMI_lbl2.setText(self.languages.t1_gMI_lbl2)
        self.t1_gMI_lbl3.setText(self.languages.t1_gMI_lbl3)
        self.t1_gMI_lbl4.setText(self.languages.t1_gMI_lbl4)

        self.t1_groupSamplePreparation.setTitle(self.languages.t1_groupSamplePreparation)
        self.t1_gSP_gRB_rb1.setText(self.languages.t1_gSP_gRB_rb1)
        self.t1_gSP_gRB_rb2.setText(self.languages.t1_gSP_gRB_rb2)
        self.t1_gSP_gRB_rb3.setText(self.languages.t1_gSP_gRB_rb3)
        self.t1_gSP_lbl1.setText(self.languages.t1_gSP_lbl1)

        self.t1_groupMeasurementResults.setTitle(self.languages.t1_groupMeasurementResults)
        self.t1_gMR_lbl1.setText(self.languages.t1_gMR_lbl1)
        self.t1_gMR_lbl2.setText(self.languages.t1_gMR_lbl2)
        self.t1_gMR_lbl3.setText(self.languages.t1_gMR_lbl3)
        self.t1_gMR_lbl4.setText(self.languages.t1_gMR_lbl4)

        self.t1_groupMeasurement.setTitle(self.languages.t1_groupMeasurement)
        self.t1_gM_lbl1.setText(self.languages.t1_gM_lbl1)
        self.t1_gM_lbl2.setText(self.languages.t1_gM_lbl2)
        self.t1_gM_lbl3.setText(self.languages.t1_gM_lbl3)
        self.t1_gM_lbl4.setText(self.languages.t1_gM_lbl4)

        self.t1_gM_cmd1.clear()
        self.t1_gM_cmd1.addItems(
            [self.languages.t1_gM_cmd1_1, self.languages.t1_gM_cmd1_2])
        if self.config.small_cuvette:
            self.t1_gM_cmd1.addItem(self.languages.t1_gM_cmd1_3)

        self.t1_gM_button1.setText(self.languages.t1_gM_button1)
        self.t1_gM_button2.setText(self.languages.t1_gM_button2)
        self.t1_gM_button3.setText(self.languages.t1_gM_button3)
        self.t1_gM_button4.setText(self.languages.t1_gM_button4)

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
                                           self.languages.t2_tableCalibration_popup_Add,
                                           self.languages.t2_tableCalibration_popup_Recount)

        self.t2_groupCalibratonResult.setTitle(self.languages.t2_groupCalibratonResult)
        self.t2_gCR_button1.setText(self.languages.t2_gCR_button1)
        self.t2_gCR_lbl1.setText(self.languages.t2_gCR_lbl1)
        self.t2_gCR_lbl2.setText(self.languages.t2_gCR_lbl2)
        self.t2_gCR_lbl3.setText(self.languages.t2_gCR_lbl3)
        self.t2_gCR_lbl4.setText(self.languages.t2_gCR_lbl4)
        self.t2_gCR_lbl5.setText(self.languages.t2_gCR_lbl5)

        self.t2_groupInitialData.setTitle(self.languages.t2_groupInitialData)
        self.t2_gID_lbl1.setText(self.languages.t2_gID_lbl1)
        self.t2_gID_lbl2.setText(self.languages.t2_gID_lbl2)
        self.t2_gID_lbl3.setText(self.languages.t2_gID_lbl3)

        self.t2_gID_cmd1.clear()
        self.t2_gID_cmd1.addItems(
            [self.languages.t2_gID_cmd1_1, self.languages.t2_gID_cmd1_2])
        if self.config.small_cuvette:
            self.t2_gID_cmd1.addItem(self.languages.t2_gID_cmd1_3)
            self.no_small.setVisible(False)
        else:
            self.t3_checkValve2.setEnabled(False)
            self.t3_lblValve2.setEnabled(False)

        self.t2_gID_button1.setText(self.languages.t2_gID_button1)
        self.t2_gID_button2.setText(self.languages.t2_gID_button2)
        self.t2_gID_button3.setText(self.languages.t2_gID_button3)
        self.t2_gID_button4.setText(self.languages.t2_gID_button4)

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
        self.t4_groupManualControl.setTitle((self.languages.t4_groupManualControl))
        self.t4_gMC_lbl1.setText(self.languages.t4_gMC_lbl1)
        self.t4_gMC_chb1.setText(self.languages.t4_gMC_chb1)
        self.t4_gMC_chb2.setText(self.languages.t4_gMC_chb2)
        self.t4_groupReportSetup.setTitle((self.languages.t4_groupReportSetup))
        self.t4_gRS_chb1.setText(self.languages.t4_gRS_chb1)
        self.t4_gRS_lbl1.setText(self.languages.t4_gRS_lbl1)
        self.t4_gRS_lbl2.setText(self.languages.t4_gRS_lbl2)
        self.t4_groupSavingResult.setTitle((self.languages.t4_groupSavingResult))
        self.t4_gSR_chb1.setText(self.languages.t4_gSR_chb1)
        self.t4_gSR_chb2.setText(self.languages.t4_gSR_chb2)
        self.t4_gSR_lbl1.setText(self.languages.t4_gSR_lbl1)
        self.t4_gSR_lbl2.setText(self.languages.t4_gSR_lbl2)
        self.t4_gSR_lbl3.setText(self.languages.t4_gSR_lbl3)
        try:
            url = "https://mail.ru/"
            urlopen(url)
            self.t4_gSR_lbl4.setText(self.languages.t4_wifi_true)
        except:
            self.t4_gSR_lbl4.setText(self.languages.t4_wifi_false)
        self.show_current_settings()

        # [Menu]
        self.menumenu1.setTitle(self.languages.menu1)
        self.actionmenu1_command1.setText(self.languages.menu1_command1)
        self.menumenu2.setTitle(self.languages.menu2)
        self.menumenu3.setTitle(self.languages.menu3)
        self.menumenu4.setTitle(self.languages.menu4)
        self.actionmenu4_command1.setText(self.languages.menu4_command1)

        # [Message]
        self.message_headline1 = self.languages.message_headline1
        self.message_txt1 = self.languages.message_txt1
        self.message_txt2 = self.languages.message_txt2
        self.message_txt3 = self.languages.message_txt3
        self.message_txt4 = self.languages.message_txt4
        self.message_txt5 = self.languages.message_txt5
        self.message_txt6 = self.languages.message_txt6
        self.message_txt7 = self.languages.message_txt7

        # [MeasurementReport]
        self.measurement_report = self.languages.measurement_report

    # Вывод двнных теста давления, вызывается через сигнал.
    def set_pressure(self, p):
        if p < 0:
            p = 0
        self.t3_lblPressure2.setText(helper.to_fixed(p, self.config.round))

    # При любом вводе данных на форму Измерения или форму Калибровки мы проверяем можно ли сделать кнопки для начала
    # процедур активными (для этого должны быть заполнены все поля и заполненны корректно)

    def t1_gMI_Edit1_text_changed(self):
        self.set_t1_gM_button1_enabled()

    def t1_gMI_Edit2_text_changed(self):
        self.set_t1_gM_button1_enabled()

    def t1_gMI_Edit3_text_changed(self):
        self.set_t1_gM_button1_enabled()

    def t1_gMI_Edit4_text_changed(self):
        self.set_t1_gM_button1_enabled()

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
        if helper.is_float(self.t2_gID_Edit2.text()):
            self.calibration_procedure.Vss = float(self.t2_gID_Edit2.text())

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
        if len(self.t4_MS_Edit1.text()) > 0 and helper.is_float(self.t4_MS_Edit1.text()):
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
            p_min = self.config.pmeas_kpa_min
            p_max = self.config.pmeas_kpa_max
        # Если давление измеряется в Бар
        if self.t4_gMS_cmd1.currentIndex() == Pressure.Bar.value:
            p_min = self.config.pmeas_bar_min
            p_max = self.config.pmeas_bar_max
        # Если давление измеряется в psi
        if self.t4_gMS_cmd1.currentIndex() == Pressure.Psi.value:
            p_min = self.config.pmeas_psi_min
            p_max = self.config.pmeas_psi_max
        # Eсли текстовое поле "Pизм" пустое ->
        if len(self.t4_MS_Edit2.text()) <= 0:
            # -> кнопка выключена
            enabled = False
            # -> поле выделяем красным
            self.t4_MS_Edit2.setStyleSheet("border: 1px solid red;")
        # Eсли текстовое поле "Pизм" непустое...
        if len(self.t4_MS_Edit2.text()) > 0:
            # ...и введенные данные можно привести к типу float...
            if helper.is_float(self.t4_MS_Edit2.text()):
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
        if len(self.t1_gSP_Edit1.text()) > 0 and helper.is_int(self.t1_gSP_Edit1.text()):
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
            if helper.is_float(self.t1_gM_Edit1.text()):
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
            if helper.is_int(self.t1_gM_Edit2.text()):
                # ...записываем введенное значение
                a = int(self.t1_gM_Edit2.text())
        # Если текстовое поле "Взять последних" пустое ->
        if len(self.t1_gM_Edit3.text()) <= 0:
            # -> кнопка выключена
            enabled = False
        # Если текстовое поле "Взять последних" непустое...
        else:
            # ...и введенные данные можно привести к типу int...
            if helper.is_int(self.t1_gM_Edit3.text()):
                # ...записываем введенное значение
                b = int(self.t1_gM_Edit3.text())
        # Если значение текстового поля "Взять последних" больше знаяения текстового поля "Количество измерений",
        # и при этом каждое больше или равно 0 ->
        if 0 <= a < b and b >= 0:
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
            if len(self.t1_gM_Edit2.text()) > 0 and helper.is_int(self.t1_gM_Edit2.text()):
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
            if len(self.t1_gM_Edit3.text()) > 0 and helper.is_int(self.t1_gM_Edit3.text()):
                # ...но его значение меньше или равно 0 ->
                if b <= 0:
                    # -> кнопка выключена
                    enabled = False
                    # -> поле выделяем красным
                    self.t1_gM_Edit3.setStyleSheet("border: 1px solid red;")
                # ...и при этом значение больше 0 -> данные поля корректны, сбрасываем выделение поля.
                else:
                    self.t1_gM_Edit3.setStyleSheet(self.ss)

        # Если все, что касается измерений заполнено, давайте проверим поля "Общей информации"
        if enabled:
            # Итак если текстовое поле "Оператор :" пустое ->
            if len(self.t1_gMI_Edit1.text()) <= 0:
                # -> кнопка выключена
                enabled = False
                # -> поле выделяем красным
                self.t1_gMI_Edit1.setStyleSheet("border: 1px solid red;")
            # иначе ->
            else:
                self.t1_gMI_Edit1.setStyleSheet(self.ss)
            # Если текстовое поле "Организация :" пустое ->
            if len(self.t1_gMI_Edit2.text()) <= 0:
                # -> кнопка выключена
                enabled = False
                # -> поле выделяем красным
                self.t1_gMI_Edit2.setStyleSheet("border: 1px solid red;")
                # иначе ->
            else:
                self.t1_gMI_Edit2.setStyleSheet(self.ss)
            # Если текстовое поле "Образец :" пустое ->
            if len(self.t1_gMI_Edit3.text()) <= 0:
                # -> кнопка выключена
                enabled = False
                # -> поле выделяем красным
                self.t1_gMI_Edit3.setStyleSheet("border: 1px solid red;")
                # иначе ->
            else:
                self.t1_gMI_Edit3.setStyleSheet(self.ss)
            # Если текстовое поле "Партия/Серия :" пустое ->
            if len(self.t1_gMI_Edit4.text()) <= 0:
                # -> кнопка выключена
                enabled = False
                # -> поле выделяем красным
                self.t1_gMI_Edit4.setStyleSheet("border: 1px solid red;")
                # иначе ->
            else:
                self.t1_gMI_Edit4.setStyleSheet(self.ss)

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
        if len(self.t2_gID_Edit1.text()) > 0 and helper.is_int(self.t2_gID_Edit1.text()):
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
            if helper.is_float(self.t2_gID_Edit2.text()):
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
        self.measurement_procedure.measurements.clear()
        self.t1_tableMeasurement.clear_table()
        self.actionmenu4_command1.setEnabled(False)

    # очищаем таблицу и базу данных калибровки
    def calibration_clear(self):
        self.t2_gCR_button1.setEnabled(False)
        self.calibration_procedure.calibrations.clear()
        self.t2_tableCalibration.clear_table()

    # Тут происходит сохранение в config.ini результатов калибровки
    def calibration_save(self):
        vc = self.calibration_procedure.c_vc
        vd = self.calibration_procedure.c_vd
        cuv = self.t2_gID_cmd1.currentIndex()
        self.config.calibration_save(cuv, vc, vd)
        self.VcVd_download_and_display()

    # Вывод данных Измерений, вызывается через сигнал.
    def set_measurement_results(self):
        # получаем средний объем
        medium_volume = self.measurement_procedure.m_medium_volume
        # получаем среднюю плотность
        medium_density = self.measurement_procedure.m_medium_density
        # получаем СКО
        SD = self.measurement_procedure.m_SD
        # получаем СКО %
        SD_per = self.measurement_procedure.m_SD_per
        # выводим в текстовые поля формы "Измерение"
        self.t1_gMR_Edit1.setText(helper.to_fixed(medium_volume, self.config.round))
        self.t1_gMR_Edit2.setText(helper.to_fixed(medium_density, self.config.round))
        self.t1_gMR_Edit3.setText(helper.to_fixed(SD, self.config.round))
        self.t1_gMR_Edit4.setText(helper.to_fixed(SD_per, self.config.round))

        # Вывод двнных Калибровки, вызывается через сигнал.

    def set_calibration_results(self):
        vc = self.calibration_procedure.c_vc
        vd = self.calibration_procedure.c_vd
        self.t2_gCR_Edit1.setText(helper.to_fixed(vc, self.config.round))
        self.t2_gCR_Edit2.setText(helper.to_fixed(vd, self.config.round))

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

    def on_message_abort_procedure(self):
        self.get_messagebox(self.message_headline1, self.message_txt4)

    def on_message_fail_let_out_pressure(self):
        self.get_messagebox(self.message_headline1, self.message_txt5)

    # Просто по клику заполняем поля
    def t1_gMI_Edit1_clicked(self):
        self.t1_gMI_Edit1.setText("default")

    def t1_gMI_Edit2_clicked(self):
        self.t1_gMI_Edit2.setText("default")

    def t1_gMI_Edit3_clicked(self):
        self.t1_gMI_Edit3.setText("default")

    def t1_gMI_Edit4_clicked(self):
        self.t1_gMI_Edit4.setText("default")

    # Создаем отчет по измерению
    def report_measurment(self):
        self.measurement_procedure.create_report()

    # Метод для получения измерений
    def get_measurements(self):
        return self.measurement_procedure.measurements

    # Метод для получения калибровки
    def get_calibrations(self):
        return self.calibration_procedure.calibrations

    # Выбор кюветы на вкладке измерений
    def t2_gID_cmd1_changed(self):
        self.VcVd_download_and_display()

    # Открываем файловый менеджер для загрузки измерения
    def measurement_file_manager_open(self):
        files, dir = self.measurement_procedure.get_files_list()
        self.file_manager = UiFileManager(self, dir)
        self.file_manager.add_files(files)
        self.file_manager.activate()
        if self.file_manager.exec_():
            self.measurement_clear()
            self.measurement_procedure.set_measurement_file(self.file_manager.get_file())
            measurement_load = self.measurement_procedure.load_measurement_result()

            # [GeneralInformation]
            self.t1_gMI_Edit1.setText(measurement_load[0]['operator'])
            self.t1_gMI_Edit2.setText(measurement_load[0]['organization'])
            self.t1_gMI_Edit3.setText(measurement_load[0]['sample'])
            self.t1_gMI_Edit4.setText(measurement_load[0]['batch_series'])

            # [SamplePreparation]
            if measurement_load[1]['sample_preparation'] == SamplePreparation.Vacuuming:
                self.t1_gSP_gRB_rb1.setChecked(True)
            if measurement_load[1]['sample_preparation'] == SamplePreparation.Blow:
                self.t1_gSP_gRB_rb2.setChecked(True)
            if measurement_load[1]['sample_preparation'] == SamplePreparation.Impulsive_blowing:
                self.t1_gSP_gRB_rb3.setChecked(True)
            self.t1_gSP_Edit1.setText(str(measurement_load[1]['sample_preparation_time']))

            # [Measurement]
            self.t1_gM_Edit1.setText(str(measurement_load[2]['sample_mass']))
            self.t1_gM_cmd1.setCurrentIndex(measurement_load[2]['cuvette'].value)
            self.t1_gM_Edit2.setText(str(measurement_load[2]['number_of_measurements']))
            self.t1_gM_Edit3.setText(str(measurement_load[2]['take_the_last_measurements']))

            # [Measurement-0] - [Measurement-(number_of_measurements-1)]
            for i in range(measurement_load[2]['number_of_measurements']):
                m = Measurement()
                m.set_measurement(
                    measurement_load[3][i]['p0'],
                    measurement_load[3][i]['p1'],
                    measurement_load[3][i]['p2'],
                    measurement_load[3][i]['volume'],
                    measurement_load[3][i]['density'],
                    measurement_load[3][i]['deviation']
                )
                if measurement_load[3][i]['active'] is None:
                    m.active = None
                elif not measurement_load[3][i]['active']:
                    m.set_active_off()
                self.measurement_procedure.measurements.append(m)
                self.t1_tableMeasurement.add_measurement(m)

            # [MeasurementResult]
            self.measurement_results_message.emit()
            self.actionmenu4_command1.setEnabled(True)

    # Открываем файловый менеджер для загрузки калибровки
    def calibration_file_manager_open(self):
        files, dir = self.calibration_procedure.get_files_list()
        self.file_manager = UiFileManager(self, dir)
        self.file_manager.add_files(files)
        self.file_manager.activate()
        if self.file_manager.exec_():
            self.calibration_clear()
            self.calibration_procedure.set_calibration_file(self.file_manager.get_file())
            calibration_load = self.calibration_procedure.load_calibration_result()

            # [SourceData]
            self.t2_gID_cmd1.setCurrentIndex(calibration_load[0]['cuvette'].value)
            self.t2_gID_Edit1.setText(str(calibration_load[0]['number_of_measurements']))
            self.t2_gID_Edit2.setText(str(calibration_load[0]['sample']))

            # [Calibration-0] - [Calibration-(number_of_measurements-1)]
            for i in range(calibration_load[0]['number_of_measurements'] * 2):
                c = Calibration()
                c.set_calibration(
                    calibration_load[1][i]['p'],
                    calibration_load[1][i]['p0'],
                    calibration_load[1][i]['p1'],
                    calibration_load[1][i]['p2'],
                    calibration_load[1][i]['ratio'],
                    calibration_load[1][i]['deviation']
                )
                if calibration_load[1][i]['active'] is None:
                    c.active = None
                elif not calibration_load[1][i]['active']:
                    c.set_active_off()
                self.calibration_procedure.calibrations.append(c)
                self.t2_tableCalibration.add_calibration(c)

            # [CalibrationResult]
            self.calibration_results_message.emit()
            self.t2_gCR_button1.setEnabled(True)

    # Прерываем процедуру измерения
    def measurement_stop(self):
        self.measurement_procedure.set_abort_procedure(True)

    # Прерываем процедуру калибровки
    def calibration_stop(self):
        self.calibration_procedure.set_abort_procedure(True)

    def change_file_for_header_or_footer(self):
        result = None

        # Найдем в папке прибора, отвечающей за шапки и подвалы, имеющиеся файлы ".png", ".jpg"
        app_list = [os.path.join(os.getcwd(), 'attachment', 'header & footer')]
        app_masks = [".png", ".jpg"]
        app_files = self.get_files_on_datalist(app_list, app_masks)
        if len(app_files) == 0:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'not find app_files')
        else:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'find app_files: {0}'.format(app_files))

        # найдем папку пикнометр на usb
        data_dir_list = ["/media/pi"]
        data_dir_masks = ["pycnometer"]
        data_dir = self.get_dir_on_datalist(data_dir_list, data_dir_masks)
        if len(data_dir) == 0:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'not find data_dir')
        else:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'find data_dir: {0}'.format(data_dir))

        # Найдем папку header & footer на usb
        hf_dir_list = list(data_dir.keys())
        hf_dir_masks = ["header & footer"]
        hf_dir = self.get_dir_on_datalist(hf_dir_list, hf_dir_masks)
        if len(hf_dir) == 0:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'not find hf_dir')
        else:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'find hf_dir: {0}'.format(hf_dir))

        # Найдем файлы ".png", ".jpg" в папке 'header & footer' на usb
        usb_list = list(hf_dir.keys())
        usb_masks = [".png", ".jpg"]
        usb_files = self.get_files_on_datalist(usb_list, usb_masks)
        if len(usb_files) == 0:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'not find usb_files')
        else:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'find usb_files: {0}'.format(usb_files))

        self.file_manager = UiFileManager(self, "")
        # Добавим найденные файлы.
        self.file_manager.add_files(app_files)
        self.file_manager.add_files(usb_files)
        self.file_manager.activate()
        if self.file_manager.exec_():
            result = self.file_manager.get_file()
        return result

    def save_header_and_footer(self):
        # Запишем путь к папке, где будем хранить файлы для шапки и подвала.
        path = os.path.join(os.getcwd(), 'attachment', 'header & footer')
        # Нам надо создать каталог, если его еще нет.
        if not os.path.isdir(os.path.join(path)):
            os.makedirs(os.path.join(path))

        if not self.header_path == "":
            file_header_path = os.path.join(path, ntpath.basename(self.header_path))
            # А теперь сохраним наши файлы под его названием в директории программы:
            shutil.copy2(r'{0}'.format(self.header_path), r'{0}'.format(file_header_path))

        if not self.footer_path == "":
            file_footer_path = os.path.join(path, ntpath.basename(self.footer_path))
            # А теперь сохраним наши файлы под его названием в директории программы:
            shutil.copy2(r'{0}'.format(self.footer_path), r'{0}'.format(file_footer_path))

    def set_report_header(self):
        # получим путь к файлу, выбранному пользователем из списка подходящих файлов на usb устройствах.
        file = self.change_file_for_header_or_footer()
        if not file is None:
            # Узнаем имя этого файла
            file_name = ntpath.basename(file)
            # Запишем его в соответсвующее поле и запомним полный путь
            self.t4_gRS_Edit1.setText(file_name)
            self.header_path = file

    def clear_report_header(self):
        self.t4_gRS_Edit1.clear()
        self.header_path = ""

    def set_report_footer(self):
        # получим путь к файлу, выбранному пользователем из списка подходящих файлов на usb устройствах.
        file = self.change_file_for_header_or_footer()
        if not file is None:
            # Узнаем имя этого файла
            file_name = ntpath.basename(file)
            # Запишем его в соответсвующее поле и запомним полный путь
            self.t4_gRS_Edit2.setText(file_name)
            self.footer_path = file

    def clear_report_footer(self):
        self.t4_gRS_Edit2.clear()
        self.footer_path = ""

    def get_usblist(self):
        usblist = []
        if platform == "win32":
            pass
        else:
            import re
            import subprocess
            device_re = re.compile("Bus\s+(?P<bus>\d+)\s+Device\s+(?P<device>\d+).+ID\s(?P<id>\w+:\w+)\s(?P<tag>.+)$", re.I)
            df = subprocess.check_output("lsusb")
            for i in df.split('\n'):
                if i:
                    info = device_re.match(i)
                    if info:
                        dinfo = info.groupdict()
                        dinfo['device'] = '/dev/bus/usb/%s/%s' % (dinfo.pop('bus'), dinfo.pop('device'))
                        usblist.append(dinfo)
            print(usblist)
        # Мы должны получить список подключенных usb - устройств.
        # TODO получить список usb
        # И вернуть его
        return usblist

    def get_files_on_datalist(self, usblist, masks):
        # Мы должны составить список файлов на usblist удовлетворяющих masks,
        # мы должны использовать полные имена файлов и соответсвующую им дату изменений.
        ret_files = {}
        for usbdevice in usblist:
            for top, dirs, files in os.walk(usbdevice):
                for nm in files:
                    for mask in masks:
                        if nm.endswith(mask):
                            f = os.path.join(top, nm)
                            data_changed = time.gmtime(os.path.getmtime(f))
                            ret_files.update({f: data_changed})
        return ret_files

    def get_dir_on_datalist(self, usblist, masks):
        # Мы должны составить список файлов на usblist удовлетворяющих masks,
        # мы должны использовать полные имена файлов и соответсвующую им дату изменений.
        ret_files = {}
        for usbdevice in usblist:
            for top, dirs, files in os.walk(usbdevice):
                for dir in dirs:
                    for mask in masks:
                        if mask in dir:
                            f = os.path.join(top, dir)
                            data_changed = time.gmtime(os.path.getmtime(f))
                            ret_files.update({f: data_changed})
        return ret_files

    # def wifi_connect(self):
    #
    #     wifi_try = self.wifi.wifiscan()
    #     if wifi_try:
    #         self.wifi.wifi_connect()
    #     else:
    #         self.get_messagebox(self.message_headline1, self.message_txt6)

    # def wifi_disconnect(self):
    #     wifi_try = self.wifi.wifiscan()
    #     if wifi_try:
    #         self.wifi.wifi_disconnect()
    #     else:
    #         self.get_messagebox(self.message_headline1, self.message_txt7)


def main():
    app = PyQt5.QtWidgets.QApplication(sys.argv)  # Новый экземпляр QApplication
    window = Main()  # Создаём объект класса Main
    window.show()  # Показываем окно
    app.exec_()  # и запускаем приложение


if __name__ == '__main__':  # Если мы запускаем файл напрямую, а не импортируем
    main()  # то запускаем функцию main()
