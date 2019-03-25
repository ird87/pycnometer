#!/usr/bin/python
import inspect
import os

from PyQt5 import QtGui, QtCore
from PyQt5 import QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QCursor
from PyQt5.QtWidgets import QHeaderView, QMenu

from InputCalibration import UiInputCalibration

"""
"Класс реализует интерфейс таблицы "Калибровка"

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
    self.popup_menu_enable - bool, переключатель для отключения контексного меню таблицы во время рассчетов.
    self.popup_menu_enable2 - bool, переключатель для отключения контексного меню таблицы, пока 
                                                                        все поля вкладки не будут корректно заполенны.

"""


class UiTableCalibration(object):
    """Конструктор класса. Поля класса"""
    def __init__(self, main):
        self.main = main
        self.config = main.config
        self.round = self.config.round
        self.file = os.path.basename(__file__)
        self.debug_log = main.debug_log
        self.measurement_log = main.measurement_log
        self.popup_exclude = ''
        self.popup_include = ''
        self.popup_add = ''
        self.popup_recount = ''
        self.popup_menu_enable = True
        self.popup_menu_enable2 = False

    """Метод добавляет в таблицу массив калибровок."""
    def add_calibration(self, _calibrations):
        # определяем сколько у нас строк в таблице, а значит и индекс для новой строки.
        rowPosition = self.t2_tableCalibration.rowCount()
        # добавляем новую строку
        self.t2_tableCalibration.insertRow(rowPosition)
        # для размещения данных в ячейке таблицы, надо убедиться, что они string и разместить их в QTableWidgetItem
        item1 = QtWidgets.QTableWidgetItem(self.main.get_calibrations()[rowPosition].measurement)
        # Указать им ориентацию по центру
        item1.setTextAlignment(QtCore.Qt.AlignCenter)
        # Указать, что ячейку нельзя редактировать
        item1.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        # и, наконец, разместить в нужной ячейке по координатом строки и столбца
        self.t2_tableCalibration.setItem(rowPosition, 0, item1)
        # повторить для каждой ячейки, куда надо внести данные.
        from Main import toFixed
        item2 = QtWidgets.QTableWidgetItem(toFixed(_calibrations.p0, self.round))
        item2.setTextAlignment(QtCore.Qt.AlignCenter)
        item2.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.t2_tableCalibration.setItem(rowPosition, 1, item2)
        item3 = QtWidgets.QTableWidgetItem(toFixed(_calibrations.p1, self.round))
        item3.setTextAlignment(QtCore.Qt.AlignCenter)
        item3.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.t2_tableCalibration.setItem(rowPosition, 2, item3)
        item4 = QtWidgets.QTableWidgetItem(toFixed(_calibrations.p2, self.round))
        item4.setTextAlignment(QtCore.Qt.AlignCenter)
        item4.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.t2_tableCalibration.setItem(rowPosition, 3, item4)
        item5 = QtWidgets.QTableWidgetItem(toFixed(_calibrations.ratio, self.round))
        item5.setTextAlignment(QtCore.Qt.AlignCenter)
        item5.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.t2_tableCalibration.setItem(rowPosition, 4, item5)
        item6 = QtWidgets.QTableWidgetItem(toFixed(_calibrations.deviation, self.round))
        item6.setTextAlignment(QtCore.Qt.AlignCenter)
        item6.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.t2_tableCalibration.setItem(rowPosition, 5, item6)
        if not _calibrations.active  or _calibrations.active is None:
            self.set_color_to_row_unactive(rowPosition)
        self.t2_tableCalibration.reset()

    """Метод добавляет контекстное меню"""
    def popup(self):
        # У нас в таблице лежат данные для P и для P', чтобы верно работать с данными нам надо знать
        # сколько у нас элементов для каждого списка:
        l = int(len(self.main.get_calibrations()) / 2)
        # Контекстное меню не будет работать если идет калибровка или не все поля ввода данных заполнены
        if self.popup_menu_enable and self.popup_menu_enable2:
            # перебираем выделенные ячейки
            for i in self.t2_tableCalibration.selectionModel().selection().indexes():
                # Создаем контекстное меню
                menu = QMenu()
                # Добавляем пункт меню "Пересчет", он будет доступен при нажатии на любую строку
                recalculation_action = menu.addAction(self.popup_recount)
                if not self.main.get_calibrations()[i.row()].active is None:
                    # Проверяем для данных выбранной строки включены ли они в рассчеты
                    if self.main.get_calibrations()[i.row()].active:
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
                else:
                    return
            # Сюда мы попадаем только если пользователь кликнул по таблице, но не по строкам.
            # Создаем контекстное меню
            menu = QMenu()
            # Добавляем пункт меню "Добавить"
            add_action = menu.addAction(self.popup_add)
            # Отображаем меню для пользователя
            action = menu.exec_(QCursor.pos())
            # Обработка выбора пунктов меню пользователем.
            if action == add_action and self.main.config.is_test_mode():
                self.add_items_input()

    """Метод добавления строки с вводом данных через вспомогательное окно |Будет отключена|"""
    def add_items_input(self):
        # Импортируем модуль с формой для ввода данных

        # инициализируем ее как дочернюю форму
        self.inputCalibration = UiInputCalibration(self)
        self.inputCalibration.activate()


    """Метод для исключения из рассчета выбранной строки таблицы"""
    def exclude_items(self, row):
        # вызываем метод класа Сalibration.py, который устанавливает статус переключателя включен в рассчеты на False
        self.main.get_calibrations()[row].set_active_off()
        # вызываем метод, который изменяет цвет данной строки на серый.
        self.set_color_to_row_unactive(row)
        # пересчитываем результаты
        self.recalculation_results()

    """Метод для проверки можно ли исключить из рассчета строку P таблицы"""
    def can_exclude_more1(self):
        result = True
        # Определяем длинну массива
        l = int(len(self.main.get_calibrations()) / 2)
        val1 = 0
        # Считаем сколько у нас активных строк
        for i in range(l):
            index = i
            if self.main.get_calibrations()[index].active:
                val1 += 1
        # Если меньше или равно одному, то нельзя. Иначе можно
        if val1 <= 1:
            result = False
        return result

    """Метод для проверки можно ли исключить из рассчета строку P' таблицы"""
    def can_exclude_more2(self):
        result = True
        # Определяем длинну массива
        l = int(len(self.main.get_calibrations()) / 2)
        val2 = 0
        # Считаем сколько у нас активных строк
        for i in range(l):
            # Прибавляем к индексу длинну массива так как мы работаем с P'
            index = i + l
            if self.main.get_calibrations()[index].active:
                val2 += 1
        # Если меньше или равно одному, то нельзя. Иначе можно
        if val2 <= 1:
            result = False
        return result

    """Метод для включения в рассчет выбранной строки таблицы"""
    def include_items(self, row):
        # вызываем метод класа Сalibration.py, который устанавливает статус переключателя включен в рассчеты на True
        self.main.get_calibrations()[row].set_active_on()
        # вызываем метод, который изменяет цвет данной строки на белый (по-умолчанию).
        self.set_color_to_row_active(row)
        # пересчитываем результаты
        self.recalculation_results()

    """Метод для изменения цвета строки"""
    def set_color_to_row(self, row_index, color):
        # Мы знаем индекс строки, но нам надо пробежаться по каждой колонки для нее и установить нужный увет
        for j in range(self.t2_tableCalibration.columnCount()):
            self.t2_tableCalibration.item(row_index, j).setBackground(color)

    """Метод для изменения цвета строки как для активной"""
    def set_color_to_row_active(self, row):
        self.set_color_to_row(row, Qt.white)

    """Метод для изменения цвета строки как для неактивной"""
    def set_color_to_row_unactive(self, row):
        self.set_color_to_row(row, Qt.gray)

    """Это UI таблицы"""
    def setupUi(self, MainWindow):
        self.window = MainWindow
        self.t2_tableCalibration = QtWidgets.QTableWidget(self.window.t2)
        self.t2_tableCalibration.setGeometry(QtCore.QRect(10, 10, 730, 510))
        self.t2_tableCalibration.setMinimumSize(QtCore.QSize(730, 510))
        self.t2_tableCalibration.setMaximumSize(QtCore.QSize(730, 510))
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
        self.t2_tableCalibration.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.t2_tableCalibration.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.t2_tableCalibration.horizontalHeader().setSectionResizeMode(4, QtWidgets.QHeaderView.Stretch)
        self.t2_tableCalibration.horizontalHeader().setSectionResizeMode(5, QtWidgets.QHeaderView.Stretch)
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
        self.main.calibration_procedure.calculation()

    def add_item(self, x, row, column, active):
        from Main import toFixed
        item = QtWidgets.QTableWidgetItem(toFixed(x, self.round))
        item.setTextAlignment(Qt.AlignCenter)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.t2_tableCalibration.setItem(row, column, item)
        if not active or active is None:
            self.set_color_to_row_unactive(row)
        self.t2_tableCalibration.reset()
