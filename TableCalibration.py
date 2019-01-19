#!/usr/bin/python
import inspect
import os

from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QHeaderView, QMenu

"""Проверака и комментари: 19.01.2019"""

"""
"Класс реализует интерфейс и работу таблицы "Калибровка"
    1) Хранение, вывод и обработка данных типа "калибровка"
    2) контекстное меню для работы с таблицей
    3) Ui таблицы

    self.set_calibration_results - ссылка на СИГНАЛ, для вывода результатов калибровки на форму программы
    self.file - записываем название текущего файла 'TableCalibration.py'
    self.debug_log - ссылка на модуль для записи логов программы
    self.measurement_log - ссылка на модуль для записи логов прибора
    self.calibrations = [] - список экземляров класса "калибровка", куда будут сохранятся все данные для 
                                                                                                        вывода в таблицу
    для приминения языковых настроек из ini файла, все названия элементов контекстного меню вынесены в переменные:                                                                                                    
    self.popup_exclude - string, контекстное меню, исключить из рассчетов
    self.popup_include - string, контекстное меню, включить в рассчеты
    self.popup_add - string, контекстное меню, вызвать форму для ручного ввода даннх |Будет выключено|
    self.popup_recount - string, контекстное меню, пересчитать  |Будет выключено|
    self.Vss - float, сюда записываются данные стандартного образца, введенные пользователем. Это происходит в Main.py 
        непосредственно в момент ввода данных, так как процедура пересчета вызывается и вне калибровки и в нее нельзя 
                                                                                    передавать переменные из калибровки.
    self.popup_menu_enable - bool, переключатель для отключения контексного меню таблицы во время рассчетов.
    self.popup_menu_enable2 - bool, переключатель для отключения контексного меню таблицы, пока 
                                                                        все поля вкладки не будут корректно заполенны.
    self.c_Vc - float, сюда записывается рассчитанное в результате калибровки значение объема кюветы.
    self.c_Vd - float, сюда записывается рассчитанное в результате калибровки значение дополнительного объема кюветы.
"""


class UiTableCalibration(object):
    """Конструктор класса. Поля класса"""
    def __init__(self, calibration_results_message, debug_log, measurement_log):

        self.set_calibration_results = calibration_results_message
        self.file = os.path.basename(__file__)
        self.debug_log = debug_log
        self.measurement_log = measurement_log
        self.calibrations = []
        self.popup_exclude = ''
        self.popup_include = ''
        self.popup_add = ''
        self.popup_recount = ''
        self.Vss = 0
        self.popup_menu_enable = True
        self.popup_menu_enable2 = False
        self.c_Vc = 0.0
        self.c_Vd = 0.0

    """Метод добавляет новые значения в массив данных и вносит их в таблицу."""
    def add_calibration(self, _calibrations):
        # сначала записываем входящие данные калибровки в наш список
        self.calibrations.append(_calibrations)
        # определяем сколько у нас строк в таблице, а значит и индекс для новой строки.
        rowPosition = self.t2_tableCalibration.rowCount()
        # добавляем новую строку
        self.t2_tableCalibration.insertRow(rowPosition)
        # для размещения данных в ячейке таблицы, надо убедиться, что они string и разместить их в QTableWidgetItem
        item1 = QtWidgets.QTableWidgetItem(self.calibrations[rowPosition].measurement)
        # Указать им ориентацию по центру
        item1.setTextAlignment(QtCore.Qt.AlignCenter)
        # и, наконец, разместить в нужной ячейке по координатом строки и столбца
        self.t2_tableCalibration.setItem(rowPosition, 0, item1)
        # повторить для каждой ячейки, куда надо внести данные.
        item2 = QtWidgets.QTableWidgetItem(str(self.calibrations[rowPosition].p0))
        item2.setTextAlignment(QtCore.Qt.AlignCenter)
        self.t2_tableCalibration.setItem(rowPosition, 1, item2)
        item3 = QtWidgets.QTableWidgetItem(str(self.calibrations[rowPosition].p1))
        item3.setTextAlignment(QtCore.Qt.AlignCenter)
        self.t2_tableCalibration.setItem(rowPosition, 2, item3)
        item4 = QtWidgets.QTableWidgetItem(str(self.calibrations[rowPosition].p2))
        item4.setTextAlignment(QtCore.Qt.AlignCenter)
        self.t2_tableCalibration.setItem(rowPosition, 3, item4)
        item5 = QtWidgets.QTableWidgetItem(str(self.calibrations[rowPosition].ratio))
        item5.setTextAlignment(QtCore.Qt.AlignCenter)
        self.t2_tableCalibration.setItem(rowPosition, 4, item5)
        item6 = QtWidgets.QTableWidgetItem(str(self.calibrations[rowPosition].deviation))
        item6.setTextAlignment(QtCore.Qt.AlignCenter)
        self.t2_tableCalibration.setItem(rowPosition, 5, item6)
        # Устанавливаем ориентацию по центру по вертикали.
        header = self.t2_tableCalibration.verticalHeader()
        header.setDefaultAlignment(Qt.AlignHCenter)

    """Метод добавляет контекстное меню"""
    def popup(self):
        # У нас в таблице лежат данные для P и для P', чтобы верно работать с данными нам надо знать
        # сколько у нас элементов для каждого списка:
        l = int(len(self.calibrations) / 2)
        # Контекстное меню не будет работать если идет калибровка или не все поля ввода данных заполнены
        if self.popup_menu_enable and self.popup_menu_enable2:
            # перебираем выделенные ячейки
            for i in self.t2_tableCalibration.selectionModel().selection().indexes():
                # Создаем контекстное меню
                menu = QMenu()
                # Добавляем пункт меню "Пересчет", он будет доступен при нажатии на любую строку
                recalculation_action = menu.addAction(self.popup_recount)
                # Проверяем для данных выбранной строки включены ли они в рассчеты
                if self.calibrations[i.row()].active:
                    # Если включены, то определяем в какой массив данных попадает эта строка: P или P'
                    if i.row() < l:
                        # Для P проверяем можно ли еще исключать строки или больше нельзя.
                        if self.can_exclude_more1():
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
                    if i.row() >= l:
                        # Для P' проверяем можно ли еще исключать строки или больше нельзя.
                        if self.can_exclude_more2():
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
        import InputCalibration
        # инициализируем ее как дочернюю форму
        self.inputCalibration = InputCalibration.UiInputCalibration(self)
        # Устанавливаем заголовок
        self.inputCalibration.setWindowTitle('InputCalibration')
        # Устанавливаем размеры
        self.inputCalibration.setGeometry(300, 300, 400, 260)
        # Загружаем языковые настройки
        self.inputCalibration.languages(self.inputCalibrationHeader)
        # Отображаем форму
        self.inputCalibration.show()
        # Размещаем по центру
        base_pos_x = self.window.pos().x()
        base_pos_y = self.window.pos().y()
        width_parent = self.window.frameGeometry().width()
        height_parent = self.window.frameGeometry().height()
        width_child = self.inputCalibration.frameGeometry().width()
        height_child = self.inputCalibration.frameGeometry().height()
        a = base_pos_x + width_parent / 2 - width_child / 2
        b = base_pos_y + height_parent / 2 - height_child / 2
        self.inputCalibration.move(a, b)

    """Метод для исключения из рассчета выбранной строки таблицы"""
    def exclude_items(self, row):
        # вызываем метод класа Сalibration.py, который устанавливает статус переключателя включен в рассчеты на False
        self.calibrations[row].set_active_off()
        # вызываем метод, который изменяет цвет данной строки на серый.
        self.set_color_to_row(row, Qt.gray)
        # пересчитываем результаты
        self.recalculation_results()

    """Метод для проверки можно ли исключить из рассчета строку P таблицы"""
    def can_exclude_more1(self):
        result = True
        # Определяем длинну массива
        l = int(len(self.calibrations) / 2)
        val1 = 0
        # Считаем сколько у нас активных строк
        for i in range(l):
            index = i
            if self.calibrations[index].active:
                val1 += 1
        # Если меньше или равно одному, то нельзя. Иначе можно
        if val1 <= 1:
            result = False
        return result

    """Метод для проверки можно ли исключить из рассчета строку P' таблицы"""
    def can_exclude_more2(self):
        result = True
        # Определяем длинну массива
        l = int(len(self.calibrations) / 2)
        val2 = 0
        # Считаем сколько у нас активных строк
        for i in range(l):
            # Прибавляем к индексу длинну массива так как мы работаем с P'
            index = i + l
            if self.calibrations[index].active:
                val2 += 1
        # Если меньше или равно одному, то нельзя. Иначе можно
        if val2 <= 1:
            result = False
        return result

    """Метод для включения в рассчет выбранной строки таблицы"""
    def include_items(self, row):
        # вызываем метод класа Сalibration.py, который устанавливает статус переключателя включен в рассчеты на True
        self.calibrations[row].set_active_on()
        # вызываем метод, который изменяет цвет данной строки на белый (по-умолчанию).
        self.set_color_to_row(row, Qt.white)
        # пересчитываем результаты
        self.recalculation_results()

    """Метод для изменения цвета строки"""
    def set_color_to_row(self, row_index, color):
        # Мы знаем индекс строки, но нам надо пробежаться по каждой колонки для нее и установить нужный увет
        for j in range(self.t2_tableCalibration.columnCount()):
            self.t2_tableCalibration.item(row_index, j).setBackground(color)

    """Это UI таблицы"""
    def setupUi(self, MainWindow):
        self.window = MainWindow
        self.t2_tableCalibration = QtWidgets.QTableWidget(self.window.t2)
        self.t2_tableCalibration.setGeometry(QtCore.QRect(10, 10, 540, 440))
        self.t2_tableCalibration.setMinimumSize(QtCore.QSize(540, 440))
        self.t2_tableCalibration.setMaximumSize(QtCore.QSize(540, 440))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        self.t2_tableCalibration.setFont(font)
        self.t2_tableCalibration.setAutoFillBackground(False)
        self.t2_tableCalibration.setFrameShape(QtWidgets.QFrame.WinPanel)
        self.t2_tableCalibration.setLineWidth(1)
        self.t2_tableCalibration.setMidLineWidth(1)
        self.t2_tableCalibration.setAutoScroll(False)
        self.t2_tableCalibration.setTextElideMode(QtCore.Qt.ElideMiddle)
        self.t2_tableCalibration.setWordWrap(True)
        self.t2_tableCalibration.setObjectName("t2_tableCalibration")
        self.t2_tableCalibration.setColumnCount(6)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t2_tableCalibration.setVerticalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t2_tableCalibration.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t2_tableCalibration.setHorizontalHeaderItem(1, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t2_tableCalibration.setHorizontalHeaderItem(2, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t2_tableCalibration.setHorizontalHeaderItem(3, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t2_tableCalibration.setHorizontalHeaderItem(4, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.t2_tableCalibration.setHorizontalHeaderItem(5, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        item.setBackground(brush)
        self.t2_tableCalibration.setItem(0, 0, item)
        self.t2_tableCalibration.horizontalHeader().setVisible(True)
        self.t2_tableCalibration.horizontalHeader().setCascadingSectionResizes(False)
        # self.t2_tableCalibration.horizontalHeader().setDefaultSectionSize(70)
        self.t2_tableCalibration.horizontalHeader().setHighlightSections(True)
        # self.t2_tableCalibration.horizontalHeader().setMinimumSectionSize(50)
        self.t2_tableCalibration.horizontalHeader().setSortIndicatorShown(False)
        self.t2_tableCalibration.horizontalHeader().setStretchLastSection(True)
        self.t2_tableCalibration.verticalHeader().setVisible(True)
        self.t2_tableCalibration.verticalHeader().setCascadingSectionResizes(True)
        # self.t2_tableCalibration.verticalHeader().setDefaultSectionSize(25)
        self.t2_tableCalibration.verticalHeader().setHighlightSections(False)
        # self.t2_tableCalibration.verticalHeader().setMinimumSectionSize(25)
        self.t2_tableCalibration.verticalHeader().setSortIndicatorShown(False)
        self.t2_tableCalibration.verticalHeader().setStretchLastSection(False)
        self.t2_tableCalibration.horizontalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.t2_tableCalibration.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.t2_tableCalibration.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        self.t2_tableCalibration.horizontalHeader().setSectionResizeMode(2, QtWidgets.QHeaderView.Stretch)
        self.t2_tableCalibration.horizontalHeader().setSectionResizeMode(3, QtWidgets.QHeaderView.Stretch)
        self.t2_tableCalibration.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        self.t2_tableCalibration.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)
        self.t2_tableCalibration.resizeColumnsToContents()
        self.t2_tableCalibration.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.t2_tableCalibration.customContextMenuRequested.connect(self.popup)

    """Это UI таблицы"""
    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        item = self.t2_tableCalibration.horizontalHeaderItem(0)
        item.setText(_translate("MainWindow", "Измерение"))
        item = self.t2_tableCalibration.horizontalHeaderItem(1)
        item.setText(_translate("MainWindow", "Р0"))
        item = self.t2_tableCalibration.horizontalHeaderItem(2)
        item.setText(_translate("MainWindow", "Р1"))
        item = self.t2_tableCalibration.horizontalHeaderItem(3)
        item.setText(_translate("MainWindow", "Р2"))
        item = self.t2_tableCalibration.horizontalHeaderItem(4)
        item.setText(_translate("MainWindow", "Отношение"))
        item = self.t2_tableCalibration.horizontalHeaderItem(5)
        item.setText(_translate("MainWindow", "Отклонение,%"))
        __sortingEnabled = self.t2_tableCalibration.isSortingEnabled()
        self.t2_tableCalibration.setSortingEnabled(False)
        self.t2_tableCalibration.setSortingEnabled(__sortingEnabled)

    """Метод для получения языковых настроек"""
    def Languages(self, title, t2_tableCalibration_popup_Exclude, t2_tableCalibration_popup_Include,
                  t2_tableCalibration_popup_Add, t2_tableCalibration_popup_Recount):
        # Мы получаем заголовки таблицы в виде списка:
        for i in range(len(title)):
            self.t2_tableCalibration.horizontalHeaderItem(i).setText(title[i])
        # А названия для пунктов контекстного меню по одному:
        self.popup_exclude = t2_tableCalibration_popup_Exclude
        self.popup_include = t2_tableCalibration_popup_Include
        self.popup_add = t2_tableCalibration_popup_Add
        self.popup_recount = t2_tableCalibration_popup_Recount

    """Метод для получения языковых настроек для дочернего окна для ввода данных вручную"""
    def LanguagesForInputCalibration(self, title):
        self.inputCalibrationHeader = []
        for i in range(len(title)):
            self.inputCalibrationHeader.append(title[i])

    """Метод для удаления всех данных"""
    def clear_table(self):
        # Пока в таблице есть хотя бы строка - Удаляем!
        while self.t2_tableCalibration.rowCount() > 0:
            self.t2_tableCalibration.removeRow(0)

    """Метод для пересчета даннвх в таблице. Вызывается как из таблицы так и в процессе калибровки"""
    def recalculation_results(self):
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
            medium_ratio1 = round(ratio_sum1 / counter1, 3)
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
            medium_ratio2 = round(ratio_sum2 / counter1, 3)
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
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation '
                                                                             'for P[{0}].....'.format(i))
            try:
                # Рассчитываем отклонение для P
                deviation1 = round((medium_ratio1 - self.calibrations[index].ratio) / medium_ratio1 * 100, 3)
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
            item = QtWidgets.QTableWidgetItem(str(self.calibrations[index].deviation))
            item.setTextAlignment(Qt.AlignHCenter)
            self.t2_tableCalibration.setItem(counter2, 5, item)
            counter2 += 1
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation for ALL P.....Done')

        # --------------------------------------------------------------------------------------------------------------

        # Теперь считаем отклонения для каждой строки для P0', P1' и P2'
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation for ALL P\'.....')
        for i in range(num):
            # Для P'  index = i + num
            index = i + num
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation deviation '
                                                                             'for P\'[{0}].....'.format(i))
            try:
                # Рассчитываем отклонение для P'
                deviation2 = round((medium_ratio2 - self.calibrations[index].ratio) / medium_ratio2 * 100, 3)
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
            item = QtWidgets.QTableWidgetItem(str(self.calibrations[index].deviation))
            item.setTextAlignment(Qt.AlignHCenter)
            self.t2_tableCalibration.setItem(counter2, 5, item)
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
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation Vc & Vd.....')
        for i in range(num):
            for j in range(num):
                index1 = i
                index2 = j + num
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

        # --------------------------------------------------------------------------------------------------------------

        # Считаем количество комбинаций
        divider = num ** 2

        # -----------------------------------------------------------------------------------------------------

        self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                             'Calculation c_Vc.....')
        try:
            # Рассчитываем объем кюветы
            self.c_Vc = round((Vc / divider), 3)
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
            self.c_Vd = round((Vd / divider), 3)
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
        # Вызываем вывод результатов на форму.
        self.set_calibration_results.emit()
