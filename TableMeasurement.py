#!/usr/bin/python
# Модуль для создания и работы с таблицей "Измерения".
import inspect
import math
import os

from PyQt5 import QtWidgets
from PyQt5.QtGui import QCursor, QFont
from PyQt5.QtWidgets import QHeaderView, QMenu
from PyQt5 import QtGui, QtCore
from PyQt5.QtCore import Qt

from Config import Pressure


"""Проверака и комментари: 19.01.2019"""

"""
"Класс реализует интерфейс и работу таблицы "Измерения"
    1) Хранение, вывод и обработка данных типа "измерения"
    2) контекстное меню для работы с таблицей
    3) Ui таблицы
    self.c_Vc - float, сюда записывается рассчитанное в результате калибровки значение объема кюветы.
    self.c_Vd - float, сюда записывается рассчитанное в результате калибровки значение дополнительного объема кюветы.    
    
    
    self.set_measurement_results - ссылка на СИГНАЛ, для вывода результатов измерений на форму программы
    self.file - записываем название текущего файла 'TableMeasurement.py'
    self.debug_log - ссылка на модуль для записи логов программы
    self.measurement_log - ссылка на модуль для записи логов прибора
    self.measurements - список экземляров класса "калибровка", куда будут сохранятся все данные для 
                                                                                                        вывода в таблицу
    для приминения языковых настроек из ini файла, все названия элементов контекстного меню вынесены в переменные:      
    self.popup_exclude - string, контекстное меню, исключить из рассчетов
    self.popup_include - string, контекстное меню, включить в рассчеты
    self.popup_add - string, контекстное меню, вызвать форму для ручного ввода даннх |Будет выключено|
    self.popup_recount - string, контекстное меню, пересчитать  |Будет выключено|
    
    self.popup_menu_enable -  bool, переключатель для отключения контексного меню таблицы во время рассчетов и пока 
                                                                        все поля вкладки не будут корректно заполенны.
    self.m_medium_volume - float, сюда записывается рассчитанное в результате калибровки среднее значение объема.
    self.m_medium_density - float, сюда записывается рассчитанное в результате калибровки среднее значение плотности.
    self.m_SD - float, сюда записывается рассчитанное в результате калибровки значение СКО, г/см3.
    self.m_SD_per - float, сюда записывается рассчитанное в результате калибровки значение СКО, %.
"""

class UiTableMeasurement(object):

    """Конструктор класса. Поля класса"""
    def __init__(self, config, measurement_results_message, debug_log, measurement_log):

        self.config = config
        self.round = self.config.round
        self.set_measurement_results = measurement_results_message
        self.file = os.path.basename(__file__)
        self.debug_log = debug_log
        self.measurement_log = measurement_log
        # массив данных по измерениям
        self.measurements = []
        self.popup_exclude = ''
        self.popup_include = ''
        self.popup_add = ''
        self.popup_recount = ''
        self.popup_menu_enable = False

        self.m_medium_volume = 0.0
        self.m_medium_density = 0.0
        self.m_SD = 0.0
        self.m_SD_per = 0.0

        """Метод добавляет новые значения в массив данных и вносит их в таблицу."""
    def add_measurement(self, _measurements):
        # сначала записываем входящие данные калибровки в наш список
        self.measurements.append(_measurements)
        # определяем сколько у нас строк в таблице, а значит и индекс для новой строки.
        rowPosition = self.t1_tableMeasurement.rowCount()
        # добавляем новую строку
        self.t1_tableMeasurement.insertRow(rowPosition)
        # для размещения данных в ячейке таблицы, надо убедиться, что они string и разместить их в QTableWidgetItem
        from Main import toFixed
        item1 = QtWidgets.QTableWidgetItem(toFixed(self.measurements[rowPosition].p0, self.round))
        # Указать им ориентацию по центру
        item1.setTextAlignment(QtCore.Qt.AlignCenter)
        # Указать, что ячейку нельзя редактировать
        item1.setFlags(QtCore.Qt.ItemIsEnabled)
        # и, наконец, разместить в нужной ячейке по координатом строки и столбца
        self.t1_tableMeasurement.setItem(rowPosition, 0, item1)
        # повторить для каждой ячейки, куда надо внести данные.
        item2 = QtWidgets.QTableWidgetItem(toFixed(self.measurements[rowPosition].p1, self.round))
        item2.setTextAlignment(QtCore.Qt.AlignCenter)
        item2.setFlags(QtCore.Qt.ItemIsEnabled)
        self.t1_tableMeasurement.setItem(rowPosition, 1, item2)
        item3 = QtWidgets.QTableWidgetItem(toFixed(self.measurements[rowPosition].p2, self.round))
        item3.setTextAlignment(QtCore.Qt.AlignCenter)
        item3.setFlags(QtCore.Qt.ItemIsEnabled)
        self.t1_tableMeasurement.setItem(rowPosition, 2, item3)
        item4 = QtWidgets.QTableWidgetItem(toFixed(self.measurements[rowPosition].volume, self.round))
        item4.setTextAlignment(QtCore.Qt.AlignCenter)
        item4.setFlags(QtCore.Qt.ItemIsEnabled)
        self.t1_tableMeasurement.setItem(rowPosition, 3, item4)
        item5 = QtWidgets.QTableWidgetItem(toFixed(self.measurements[rowPosition].density, self.round))
        item5.setTextAlignment(QtCore.Qt.AlignCenter)
        item5.setFlags(QtCore.Qt.ItemIsEnabled)
        self.t1_tableMeasurement.setItem(rowPosition, 4, item5)
        item6 = QtWidgets.QTableWidgetItem(toFixed(self.measurements[rowPosition].deviation, self.round))
        item6.setTextAlignment(QtCore.Qt.AlignCenter)
        item6.setFlags(QtCore.Qt.ItemIsEnabled)
        self.t1_tableMeasurement.setItem(rowPosition, 5, item6)
        # Устанавливаем ориентацию по центру по вертикали.
        header = self.t1_tableMeasurement.verticalHeader()
        header.setDefaultAlignment(Qt.AlignHCenter)

    """Метод добавляет контекстное меню"""
    def popup(self):
        # Контекстное меню не будет работать если идет измерение или не все поля ввода данных заполнены
        if self.popup_menu_enable:
            # перебираем выделенные ячейки
            for i in self.t1_tableMeasurement.selectionModel().selection().indexes():
                # Создаем контекстное меню
                menu = QMenu()
                # Добавляем пункт меню "Пересчет", он будет доступен при нажатии на любую строку
                recalculation_action = menu.addAction(self.popup_recount)
                # Проверяем для данных выбранной строки включены ли они в рассчеты
                if self.measurements[i.row()].active:
                    # Проверяем можно ли еще исключать строки или больше нельзя.
                    if self.can_exclude_more():
                        # Если можно, то добавляем пункт меню "Исключить"
                        exclude_action = menu.addAction(self.popup_exclude)
                        # Отображаем меню для пользователя
                        action = menu.exec_(QCursor.pos())
                        # Обработка выбора пунктов меню пользователем.
                        if action == exclude_action:
                            self.exclude_items(i.row())
                        if action == recalculation_action:
                            self.recalculation_results()
                    # выходим из метода, чтобы избежать добавления в меню вариантов, предназначенных для клика
                    # по пустой зоне таблицы
                    return
                else:
                    # Если исключены, то добавляем пункт меню "Включить"
                    include_action = menu.addAction(self.popup_include)
                    # Отображаем меню для пользователя
                    action = menu.exec_(QCursor.pos())
                    # Обработка выбора пунктов меню пользователем.
                    if action == include_action:
                        self.include_items(i.row())
                    if action == recalculation_action:
                        self.recalculation_results()
                    # выходим из метода, чтобы избежать добавления в меню вариантов, предназначенных для клика
                    # по пустой зоне таблицы
                    return
            # Сюда мы попадаем только если пользователь кликнул по таблице, но не по строкам.
            # Создаем контекстное меню
            menu = QMenu()
            # Добавляем пункт меню "Добавить"
            add_action = menu.addAction(self.popup_add)
            # Отображаем меню для пользователя
            action = menu.exec_(QCursor.pos())
            # Обработка выбора пунктов меню пользователем.
            if action == add_action:
                self.add_items()

    """Метод добавления строки с вводом данных через вспомогательное окно |Будет отключена|"""
    def add_items(self):
        # Импортируем модуль с формой для ввода данных
        import InputMeasurement
        # инициализируем ее как дочернюю форму
        self.inputMeasurement = InputMeasurement.UiInputMeasurement(self)
        # Устанавливаем заголовок
        self.inputMeasurement.setWindowTitle('InputMeasurement')
        # Устанавливаем размеры
        self.inputMeasurement.setGeometry(300, 300, 400, 260)
        # Загружаем языковые настройки
        self.inputMeasurement.languages(self.inputMeasurementHeader)
        # Отображаем форму
        self.inputMeasurement.show()
        # Размещаем по центру
        base_pos_x= self.window.pos().x()
        base_pos_y= self.window.pos().y()
        width_parent = self.window.frameGeometry().width()
        height_parent = self.window.frameGeometry().height()
        width_child = self.inputMeasurement.frameGeometry().width()
        height_child = self.inputMeasurement.frameGeometry().height()
        a = base_pos_x + width_parent/2 - width_child/2
        b = base_pos_y + height_parent/2 - height_child/2
        self.inputMeasurement.move(a, b)

    """Метод для исключения из рассчета выбранной строки таблицы"""
    def exclude_items(self, row):
        # вызываем метод класа Measurement.py, который устанавливает статус переключателя включен в рассчеты на False
        self.measurements[row].set_active_off()
        # вызываем метод, который изменяет цвет данной строки на серый.
        self.set_color_to_row(row, Qt.gray)
        # пересчитываем результаты
        self.recalculation_results()

    """Метод для проверки можно ли исключить из рассчета строку таблицы"""
    def can_exclude_more(self):
        val = 0
        result = True
        # Считаем сколько у нас активных строк
        for i in self.measurements:
            if i.active:
                val += 1
        # Если меньше или равно одному, то нельзя. Иначе можно
        if val <= 1:
            result = False
        return result

    """Метод для включения в рассчет выбранной строки таблицы"""
    def include_items(self, row):
        # вызываем метод класа Measurement.py, который устанавливает статус переключателя включен в рассчеты на True
        self.measurements[row].set_active_on()
        # вызываем метод, который изменяет цвет данной строки на белый (по-умолчанию).
        self.set_color_to_row(row, Qt.white)
        # пересчитываем результаты
        self.recalculation_results()

    """Метод для изменения цвета строки"""
    def set_color_to_row(self, row_index, color):
        # Мы знаем индекс строки, но нам надо пробежаться по каждой колонки для нее и установить нужный увет
        for j in range(self.t1_tableMeasurement.columnCount()):
            self.t1_tableMeasurement.item(row_index, j).setBackground(color)

    """Это UI таблицы"""
    def setupUi(self, MainWindow):
        self.window=MainWindow
        self.t1_tableMeasurement = QtWidgets.QTableWidget(self.window.t1)
        self.t1_tableMeasurement.setGeometry(QtCore.QRect(10, 10, 540, 440))
        self.t1_tableMeasurement.setMinimumSize(QtCore.QSize(540, 440))
        self.t1_tableMeasurement.setMaximumSize(QtCore.QSize(540, 440))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        self.t1_tableMeasurement.setFont(font)
        self.t1_tableMeasurement.setAutoFillBackground(False)
        self.t1_tableMeasurement.setFrameShape(QtWidgets.QFrame.WinPanel)
        self.t1_tableMeasurement.setLineWidth(1)
        self.t1_tableMeasurement.setMidLineWidth(1)
        self.t1_tableMeasurement.setAutoScroll(False)
        self.t1_tableMeasurement.setTextElideMode(QtCore.Qt.ElideMiddle)
        self.t1_tableMeasurement.setWordWrap(True)
        self.t1_tableMeasurement.setObjectName("t1_tableMeasurement")
        self.t1_tableMeasurement.setColumnCount(6)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t1_tableMeasurement.setVerticalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t1_tableMeasurement.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t1_tableMeasurement.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t1_tableMeasurement.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t1_tableMeasurement.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t1_tableMeasurement.setHorizontalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t1_tableMeasurement.setHorizontalHeaderItem(5, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        item.setBackground(brush)
        self.t1_tableMeasurement.setItem(0, 0, item)
        self.t1_tableMeasurement.horizontalHeader().setVisible(True)
        self.t1_tableMeasurement.horizontalHeader().setCascadingSectionResizes(False)
        # self.t1_tableMeasurement.horizontalHeader().setDefaultSectionSize(70)
        self.t1_tableMeasurement.horizontalHeader().setHighlightSections(True)
        # self.t1_tableMeasurement.horizontalHeader().setMinimumSectionSize(50)
        self.t1_tableMeasurement.horizontalHeader().setSortIndicatorShown(False)
        self.t1_tableMeasurement.horizontalHeader().setStretchLastSection(True)
        self.t1_tableMeasurement.verticalHeader().setVisible(True)
        self.t1_tableMeasurement.verticalHeader().setCascadingSectionResizes(True)
        # self.t1_tableMeasurement.verticalHeader().setDefaultSectionSize(25)
        self.t1_tableMeasurement.verticalHeader().setHighlightSections(False)
        # self.t1_tableMeasurement.verticalHeader().setMinimumSectionSize(25)
        self.t1_tableMeasurement.verticalHeader().setSortIndicatorShown(False)
        self.t1_tableMeasurement.verticalHeader().setStretchLastSection(False)
        self.t1_tableMeasurement.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.t1_tableMeasurement.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.t1_tableMeasurement.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        self.t1_tableMeasurement.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        self.t1_tableMeasurement.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)
        self.t1_tableMeasurement.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.t1_tableMeasurement.customContextMenuRequested.connect(self.popup)

    """Это UI таблицы"""
    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        item = self.t1_tableMeasurement.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Р0"))
        item = self.t1_tableMeasurement.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Р1"))
        item = self.t1_tableMeasurement.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Р2"))
        item = self.t1_tableMeasurement.horizontalHeaderItem(3)
        item.setText(_translate("MainWindow", "Объем, см3"))
        item = self.t1_tableMeasurement.horizontalHeaderItem(4)
        item.setText(_translate("MainWindow", "Плотность, гр/см3"))
        item = self.t1_tableMeasurement.horizontalHeaderItem(5)
        item.setText(_translate("MainWindow", "Отклонение,%"))
        __sortingEnabled = self.t1_tableMeasurement.isSortingEnabled()
        self.t1_tableMeasurement.setSortingEnabled(False)
        self.t1_tableMeasurement.setSortingEnabled(__sortingEnabled)

    """Метод для получения языковых настроек"""
    def Languages(self, title, t1_tableMeasurement_popup_Exclude, t1_tableMeasurement_popup_Include,
                  t1_tableMeasurement_popup_Add, t1_tableMeasurement_popup_Recount):
        # Мы получаем заголовки таблицы в виде списка:
        for i in range(len(title)):
            self.t1_tableMeasurement.horizontalHeaderItem(i).setText(title[i])
        # А названия для пунктов контекстного меню по одному:
        self.popup_exclude = t1_tableMeasurement_popup_Exclude
        self.popup_include = t1_tableMeasurement_popup_Include
        self.popup_add = t1_tableMeasurement_popup_Add
        self.popup_recount = t1_tableMeasurement_popup_Recount

    """Метод для получения языковых настроек для дочернего окна для ввода данных вручную"""
    def LanguagesForInputMeasurement(self, title):
        self.inputMeasurementHeader=[]
        for i in range(len(title)):
            self.inputMeasurementHeader.append(title[i])

    """Метод для удаления всех данных"""
    def clear_table(self):
        # Пока в таблице есть хотя бы строка - Удаляем!
        while self.t1_tableMeasurement.rowCount() > 0:
                self.t1_tableMeasurement.removeRow(0)

    """Метод для выключения из расчета данных в соответствие с переменной с выбором пользователя перед началом изменений"""
    def last_numbers_result(self, take_the_last_measurements):
        for i in range(len(self.measurements) - take_the_last_measurements):
            self.measurements[i].set_active_off()
            self.set_color_to_row(i, Qt.gray)

    """Метод для пересчета данных в таблице. Вызывается как из таблицы так и в процессе измерений"""
    def recalculation_results(self):

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
            from Main import toFixed
            item = QtWidgets.QTableWidgetItem(toFixed(m.deviation, self.round))
            item.setTextAlignment(Qt.AlignHCenter)
            item.setFlags(QtCore.Qt.ItemIsEnabled)
            self.t1_tableMeasurement.setItem(counter2, 5, item)
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
                squared_of_density_deviations_sum += (self.m_medium_volume - m.volume)**2
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
        # Вызываем вывод результатов на форму.
        self.set_measurement_results.emit()


