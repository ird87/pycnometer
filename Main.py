#!/usr/bin/python
# coding=utf-8
# Главный модуль программы.
import inspect
import ntpath
import os
import shutil
import sys  # sys нужен для передачи argv в QApplication
import time
from sys import platform

import MainWindow  # Это наш конвертированный файл дизайна
import PyQt5

from Calibration import Calibration
from CalibrationProcedure import CalibrationProcedure
from Config import Configure, Pressure
from FileManager import UiFileManager
from Languages import Languages
from Logger import Logger
from Measurement import Measurement
from MeasurementProcedure import MeasurementProcedure, Сuvette, Sample_preparation
from PyQt5 import QtCore
from PyQt5.QtCore import QRegExp, QObject, QEvent, Qt
from PyQt5.QtGui import QIntValidator, QRegExpValidator, QPixmap
from PyQt5.QtWidgets import QMessageBox

from ModulWIFI import WIFI
from Progressbar import UiProgressbar
from TableCalibration import UiTableCalibration
from TableMeasurement import UiTableMeasurement
from Controller import Controller

"""Проверака и комментари: 23.01.2019"""
"""
"Главный класс. Работа с GUI, управление приложением, обработка ввода пользователя и работы процедур измерений и калибровки"
"""

"""Функция для отображенияtoFixed нужного количества знаков после '.'"""


def toFixed(numObj, digits=0):
    if numObj != None and numObj != '':
        if isfloat(numObj):
            retVal = '{0:.{1}f}'.format(numObj, digits)
            return retVal
        else:
            return 'Not float'
    else:
        return 'None'


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


class Main(PyQt5.QtWidgets.QMainWindow, MainWindow.Ui_MainWindow):  # название файла с дизайном и название класса в нем.

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
        super().__init__()
        self.setupUi(self)  # Это нужно для инициализации нашего дизайна
        self.setWindowState(Qt.WindowMaximized)
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.controller = Controller
        self.wifi = False
        # Загружаем модуль настройки
        self.config = Configure()
        self.config.set_measurement()
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

        self.wifi = WIFI()
        # очищаем поля для ввода данных.
        self.initial_field_clearing()

        # Включаем GPIO и SPI модули, в зависимости от активного/неактивного Тестового режима
        if self.config.is_test_mode():
            self.setWindowTitle('*** *** *** ТЕСТОВЫЙ РЕЖИМ *** *** ***')
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'The program works in TEST mode.')
        if not self.config.is_test_mode():
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'The program works in NORMAL mode.')
        if platform == "win32":
            from ModulGPIOtest import GPIO
            from ModulSPItest import SPI
            # Получаем данные о портах из Configure.ini
            self.ports = self.config.get_ports()
            self.gpio = GPIO(self.ports)
            self.all_port_off()
            self.spi = SPI(self)
        else:
            from ModulGPIO import GPIO
            if self.config.module_spi == "SPI2":
                from ModulSPI_2 import SPI
            else:
                from ModulSPI import SPI
            # Получаем данные о портах из Configure.ini
            self.ports = self.config.get_ports()
            self.gpio = GPIO(self.ports)
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
        self.t4_gRS_button3.clicked.connect(self.get_report_footer)  # Настройка.    добавить подвал в отчет.
        self.t4_gRS_button4.clicked.connect(self.clear_report_footer)  # Настройка.    удалить подвал из отчета.
        self.t4_gSR_button1.clicked.connect(self.wifi_connect)
        self.t4_gSR_button2.clicked.connect(self.wifi_disconnect)
        self.tabPycnometer.currentChanged.connect(self.tab_change)  # Переключение вкладок программы.
        self.actionmenu4_command1.triggered.connect(self.report_measurment)
        self.actionmenu1_command1.triggered.connect(self.closeEvent)
        self.menubar.setVisible(False)
        self.sensor_calibration = False
        # нам надо откалибровать датчик.
        if not self.config.is_test_mode():
            self.calibration_procedure.start_russian_sensor_calibration()

    def start_progressbar(self, title, name, time):
        if not self.config.is_test_mode():
            self.progressbar_form = UiProgressbar(self, title, name, time)
            self.progressbar_form.activate()

    def change_progressbar(self, t):
        if not self.config.is_test_mode():
            self.progressbar_form.add_progress(t)

    def exit_progressbar(self):
        if not self.config.is_test_mode():
            self.progressbar_form.exit()

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
        if self.t2_gID_cmd1.currentIndex() == Сuvette.Small.value:
            self.t2_gCR_Edit3.setText(str(self.config.VcS))
            self.t2_gCR_Edit4.setText(str(self.config.VdS))
        if self.t2_gID_cmd1.currentIndex() == Сuvette.Medium.value:
            self.t2_gCR_Edit3.setText(str(self.config.VcM))
            self.t2_gCR_Edit4.setText(str(self.config.VdLM))
        if self.t2_gID_cmd1.currentIndex() == Сuvette.Large.value:
            self.t2_gCR_Edit3.setText(str(self.config.VcL))
            self.t2_gCR_Edit4.setText(str(self.config.VdLM))

    # Применяем изменения в настройках программы.
    def option_appy(self):
        # Сначала мы записываем все изменения внутрь файла config.ini
        self.config.set_ini('Pycnometer', 'model', self.config.model)
        self.config.set_ini('Pycnometer', 'version', self.config.version)
        self.config.set_ini('Pycnometer', 'small_cuvette', str(self.config.small_cuvette))
        self.config.set_ini('Pycnometer', 'module_spi', self.config.module_spi)
        self.config.set_ini('Pycnometer', 'data_channel', str(self.config.data_channel))
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

        Pmeas_const = '[{0}, {1}, {2}]'.format(p_kPa, p_Bar, p_Psi)
        self.config.set_ini('Measurement', 'Pmeas', Pmeas_const)
        self.config.set_ini('Measurement', 'round', str(self.config.round))
        self.config.set_ini('ManualControl', 'periodicity_of_removal_of_sensor_reading', self.t4_gMC_Edit1.text())
        self.config.set_ini('ManualControl', 'leak_test_when_starting', str(self.t4_gMC_chb1.isChecked()))
        self.config.set_ini('ReportSetup', 'report_measurement_table', str(self.t4_gRS_chb1.isChecked()))
        self.save_header_and_footer()
        self.config.set_ini('ReportSetup', 'report_header', self.t4_gRS_Edit1.text())
        self.config.set_ini('ReportSetup', 'report_footer', self.t4_gRS_Edit2.text())
        self.config.set_ini('SavingResult', 'save_to_flash_drive', str(self.t4_gSR_chb1.isChecked()))
        self.config.set_ini('SavingResult', 'send_report_to_mail', str(self.t4_gSR_chb2.isChecked()))
        self.config.set_ini_hash('SavingResult', 'email_adress', self.t4_gSR_Edit1.text())
        self.config.set_ini_hash('SavingResult', 'wifi_name', self.t4_gSR_Edit2.text())
        self.config.set_ini_hash('SavingResult', 'wifi_pass', self.t4_gSR_Edit3.text())

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
        self.wifi.set_wifi(self.config.wifi_name, self.config.wifi_pass)
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
        self.setPressurePmeas()

        # Устанавливаем Частота съема показания датчика (0.1 - 1.0 сек)
        self.t4_gMC_Edit1.setText(str(self.config.periodicity_of_removal_of_sensor_reading))

        # Проводить ли тест на натекание при запуске прибора
        self.t4_gMC_chb1.setChecked(self.config.leak_test_when_starting)

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
        self.t4_gSR_Edit1.setText(self.config.email_adress)

        # Название сети wifi:
        self.t4_gSR_Edit2.setText(self.config.wifi_name)

        # Пароль от wifi:
        self.t4_gSR_Edit3.setText(self.config.wifi_pass)

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

        return operator, organization, sample, batch_series, cuvette, sample_preparation, sample_preparation_time_in_minute, sample_mass, \
               number_of_measurements, take_the_last_measurements

    # Передаем данные в класс проводящий измерения, и запускаем измерения.
    def measurement_procedure_start(self):
        self.measurement_clear()
        # Получаем данные введенные пользователем
        operator, organization, sample, batch_series, cuvette, sample_preparation, sample_preparation_time_in_minute, sample_mass, number_of_measurements, \
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
        self.measurement_procedure.set_settings(operator, organization, sample, batch_series, cuvette,
                                                sample_preparation, sample_preparation_time_in_minute,
                                                sample_mass, number_of_measurements, take_the_last_measurements,
                                                VcL, VcM, VcS, VdLM, VdS, Pmeas, pulse_length)

        # Явно выключаем все порты (на всякий случай, они и так должны быть выключены)
        self.all_port_off()
        # Запускаем измерения.
        self.measurement_procedure.start_measurements()
        # Делаем вывод отчета доступным.
        self.actionmenu4_command1.setEnabled(True)

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
        sample_volume = float(self.t2_gID_Edit2.text())

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
        self.t4_gSR_Edit3.setText('')

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
        self.t4_gSR_button1.setText(self.languages.t4_gSR_button1)
        self.t4_gSR_button2.setText(self.languages.t4_gSR_button2)
        if self.wifi.connect:
            # self.t4_gSR_lbl4.setStyleSheet("color: green")
            self.t4_gSR_lbl4.setText(self.languages.t4_wifi_true)
        else:
            # self.t4_gSR_lbl4.setStyleSheet("color: red")
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
        self.t3_lblPressure2.setText(toFixed(p, self.config.round))

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
        if isfloat(self.t2_gID_Edit2.text()):
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
        if a >= 0 and b >= 0 and b > a:
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
        Vc = self.calibration_procedure.c_Vc
        Vd = self.calibration_procedure.c_Vd
        cuv = self.t2_gID_cmd1.currentIndex()
        if self.t2_gID_cmd1.currentIndex() == Сuvette.Large.value:
            self.config.set_ini('Measurement', 'VcL', toFixed(Vc, self.config.round))
            self.config.set_ini('Measurement', 'VdLM', toFixed(Vd, self.config.round))
        if self.t2_gID_cmd1.currentIndex() == Сuvette.Medium.value:
            self.config.set_ini('Measurement', 'VcM', toFixed(Vc, self.config.round))
            self.config.set_ini('Measurement', 'VdLM', toFixed(Vd, self.config.round))
        if self.t2_gID_cmd1.currentIndex() == Сuvette.Small.value:
            self.config.set_ini('Measurement', 'VcS', toFixed(Vc, self.config.round))
            self.config.set_ini('Measurement', 'VdS', toFixed(Vd, self.config.round))
        self.setup()
        self.t2_gID_cmd1.setCurrentIndex(cuv)
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
        self.t1_gMR_Edit1.setText(toFixed(medium_volume, self.config.round))
        self.t1_gMR_Edit2.setText(toFixed(medium_density, self.config.round))
        self.t1_gMR_Edit3.setText(toFixed(SD, self.config.round))
        self.t1_gMR_Edit4.setText(toFixed(SD_per, self.config.round))

    # Вывод двнных Калибровки, вызывается через сигнал.
    def set_calibration_results(self):
        Vc = self.calibration_procedure.c_Vc
        Vd = self.calibration_procedure.c_Vd
        self.t2_gCR_Edit1.setText(toFixed(Vc, self.config.round))
        self.t2_gCR_Edit2.setText(toFixed(Vd, self.config.round))

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
            if measurement_load[1]['sample_preparation'] == Sample_preparation.Vacuuming:
                self.t1_gSP_gRB_rb1.setChecked(True)
            if measurement_load[1]['sample_preparation'] == Sample_preparation.Blow:
                self.t1_gSP_gRB_rb2.setChecked(True)
            if measurement_load[1]['sample_preparation'] == Sample_preparation.Impulsive_blowing:
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
        usblist = [os.path.join(os.getcwd(), 'attachment')]
        masks = [".png", ".jpg"]
        files = self.get_files_on_usblist(usblist, masks)
        self.file_manager = UiFileManager(self, "")
        self.file_manager.add_files(files)
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

    def get_report_footer(self):
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

    def get_files_on_usblist(self, usblist, masks):
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

    def wifi_connect(self):
        wifi_try = self.wifi.wifiscan()
        if wifi_try:
            self.wifi.wifi_connect()
        else:
            self.get_messagebox(self.message_headline1, self.message_txt6)

    def wifi_disconnect(self):
        wifi_try = self.wifi.wifiscan()
        if wifi_try:
            self.wifi.wifi_disconnect()
        else:
            self.get_messagebox(self.message_headline1, self.message_txt7)

def main():
    app = PyQt5.QtWidgets.QApplication(sys.argv)  # Новый экземпляр QApplication
    window = Main()  # Создаём объект класса Main
    window.show()  # Показываем окно
    app.exec_()  # и запускаем приложение


if __name__ == '__main__':  # Если мы запускаем файл напрямую, а не импортируем
    main()  # то запускаем функцию main()
