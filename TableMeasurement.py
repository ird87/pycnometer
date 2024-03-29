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
from InputMeasurement import UiInputMeasurement
import helper

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
    для приминения языковых настроек из ini файла, все названия элементов контекстного меню вынесены в переменные:      
    self.popup_exclude - string, контекстное меню, исключить из рассчетов
    self.popup_include - string, контекстное меню, включить в рассчеты
    self.popup_add - string, контекстное меню, вызвать форму для ручного ввода даннх |Будет выключено|
    self.popup_recount - string, контекстное меню, пересчитать  |Будет выключено|
    
    self.popup_menu_enable -  bool, переключатель для отключения контексного меню таблицы во время рассчетов и пока 
                                                                        все поля вкладки не будут корректно заполенны.

"""

class UiTableMeasurement(object):

    """Конструктор класса. Поля класса"""
    def __init__(self, main):
        self.main = main
        self.config = self.main.config
        self.round = self.config.round
        self.file = os.path.basename(__file__)
        self.debug_log = self.main.debug_log
        self.measurement_log = self.main.measurement_log
        self.popup_exclude = ''
        self.popup_include = ''
        self.popup_add = ''
        self.popup_recount = ''
        self.popup_menu_enable = False

        """Метод добавляет в таблицу массив измерений."""
    def add_measurement(self, _measurements):
        # определяем сколько у нас строк в таблице, а значит и индекс для новой строки.
        rowPosition = self.t1_tableMeasurement.rowCount()
        # добавляем новую строку
        self.t1_tableMeasurement.insertRow(rowPosition)
        # для размещения данных в ячейке таблицы, надо убедиться, что они string и разместить их в QTableWidgetItem
        p0 = _measurements.p0
        p1 = _measurements.p1
        p2 = _measurements.p2
        volume = _measurements.volume
        density = _measurements.density
        deviation = _measurements.deviation
        active = _measurements.active

        if p0 < 0:
            p0 = 0
        if p1 < 0:
            p1 = 0
        if p2 < 0:
            p2 = 0

        item1 = QtWidgets.QTableWidgetItem(helper.to_fixed(p0, self.round))
        # Указать им ориентацию по центру
        item1.setTextAlignment(QtCore.Qt.AlignCenter)
        # Указать, что ячейку нельзя редактировать
        item1.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        # и, наконец, разместить в нужной ячейке по координатом строки и столбца
        self.t1_tableMeasurement.setItem(rowPosition, 0, item1)
        # повторить для каждой ячейки, куда надо внести данные.
        item2 = QtWidgets.QTableWidgetItem(helper.to_fixed(p1, self.round))
        item2.setTextAlignment(QtCore.Qt.AlignCenter)
        item2.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.t1_tableMeasurement.setItem(rowPosition, 1, item2)
        item3 = QtWidgets.QTableWidgetItem(helper.to_fixed(p2, self.round))
        item3.setTextAlignment(QtCore.Qt.AlignCenter)
        item3.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.t1_tableMeasurement.setItem(rowPosition, 2, item3)
        item4 = QtWidgets.QTableWidgetItem(helper.to_fixed(volume, self.round))
        item4.setTextAlignment(QtCore.Qt.AlignCenter)
        item4.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.t1_tableMeasurement.setItem(rowPosition, 3, item4)
        item5 = QtWidgets.QTableWidgetItem(helper.to_fixed(density, self.round))
        item5.setTextAlignment(QtCore.Qt.AlignCenter)
        item5.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.t1_tableMeasurement.setItem(rowPosition, 4, item5)
        item6 = QtWidgets.QTableWidgetItem(helper.to_fixed(deviation, self.round))
        item6.setTextAlignment(QtCore.Qt.AlignCenter)
        item6.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.t1_tableMeasurement.setItem(rowPosition, 5, item6)
        if not active or active is None:
            self.set_color_to_row_unactive(rowPosition)
        self.t1_tableMeasurement.reset()

    """Метод добавляет контекстное меню"""
    def popup(self):
        # Контекстное меню не будет работать если идет измерение или не все поля ввода данных заполнены
        if self.popup_menu_enable:
            # перебираем выделенные ячейки
            for i in self.t1_tableMeasurement.selectionModel().selectedIndexes():
                # Создаем контекстное меню
                menu = QMenu()
                # Добавляем пункт меню "Пересчет", он будет доступен при нажатии на любую строку
                recalculation_action = menu.addAction(self.popup_recount)
                if not self.main.get_measurements()[i.row()].active is None:
                    # Проверяем для данных выбранной строки включены ли они в рассчеты
                    if self.main.get_measurements()[i.row()].active:
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
            if action == add_action:
                self.add_items_input()

    """Метод добавления строки с вводом данных через вспомогательное окно |Будет отключена|"""
    def add_items_input(self):
        # инициализируем ее как дочернюю форму
        self.inputMeasurement = UiInputMeasurement(self)
        self.inputMeasurement.activate()

    """Метод для исключения из рассчета выбранной строки таблицы"""
    def exclude_items(self, row):
        # вызываем метод класа Measurement.py, который устанавливает статус переключателя включен в рассчеты на False
        self.main.get_measurements()[row].set_active_off()
        # пересчитываем результаты
        self.recalculation_results()
        # вызываем метод, который изменяет цвет данной строки как для неактивной строки
        self.set_color_to_row_unactive(row)

    """Метод для проверки можно ли исключить из рассчета строку таблицы"""
    def can_exclude_more(self):
        val = 0
        result = True
        # Считаем сколько у нас активных строк
        for i in self.main.get_measurements():
            if i.active:
                val += 1
        # Если меньше или равно одному, то нельзя. Иначе можно
        if val <= 1:
            result = False
        return result

    """Метод для включения в рассчет выбранной строки таблицы"""
    def include_items(self, row):
        # вызываем метод класа Measurement.py, который устанавливает статус переключателя включен в рассчеты на True
        self.main.get_measurements()[row].set_active_on()
        # пересчитываем результаты
        self.recalculation_results()
        # вызываем метод, который изменяет цвет данной строки как для активной строки
        self.set_color_to_row_active(row)


    """Метод для изменения цвета строки"""
    def set_color_to_row(self, row_index, color):
        # Мы знаем индекс строки, но нам надо пробежаться по каждой колонки для нее и установить нужный увет
        for j in range(self.t1_tableMeasurement.columnCount()):
            self.t1_tableMeasurement.item(row_index, j).setBackground(color)

    """Метод для изменения цвета строки как для активной"""
    def set_color_to_row_active(self, row):
        self.set_color_to_row(row, Qt.white)

    """Метод для изменения цвета строки как для неактивной"""
    def set_color_to_row_unactive(self, row):
        self.set_color_to_row(row, Qt.gray)



    """Это UI таблицы"""
    def setupUi(self, MainWindow):
        self.window=MainWindow
        self.t1_tableMeasurement = QtWidgets.QTableWidget(self.window.t1)
        self.t1_tableMeasurement.setGeometry(QtCore.QRect(10, 10, 730, 510))
        self.t1_tableMeasurement.setMinimumSize(QtCore.QSize(730, 510))
        self.t1_tableMeasurement.setMaximumSize(QtCore.QSize(730, 510))
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

    """Метод для пересчета данных в таблице. Вызывается как из таблицы так и в процессе измерений"""
    def recalculation_results(self):
        self.main.measurement_procedure.calculation()

    def add_item(self, x, row, column, active):
        # Добавляем в таблицу в столбец для отклонений
        if 2 >= column >= 0 > x:
            x = 0
        item = QtWidgets.QTableWidgetItem(helper.to_fixed(x, self.round))
        item.setTextAlignment(Qt.AlignCenter)
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.t1_tableMeasurement.setItem(row, column, item)
        if not active or active is None:
            self.set_color_to_row_unactive(row)
        self.t1_tableMeasurement.reset()



