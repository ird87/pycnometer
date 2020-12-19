# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'FileManager.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!
import operator
import os
import sys
import time

from PyQt5 import QtCore, QtWidgets, QtGui, uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (QWidget, QApplication, QHeaderView, QAbstractItemView, QDialog)


class UiFileManager(QDialog):
    """Конструктор класса. Поля класса"""

    def __init__(self, parent, dir):
        super(UiFileManager, self).__init__()
        uic.loadUi('ui/FileManager.ui', self)
        self.parent = parent
        self.dir = dir
        self.init_ui()


    """Метод добавляет файлы в список"""
    def add_files(self, files):
        files_sorted = sorted(files.items(), key= operator.itemgetter(1), reverse = True)
        for f in files_sorted:
            # определяем сколько у нас строк в таблице, а значит и индекс для новой строки.
            rowPosition = self.table_files.rowCount()
            # добавляем новую строку
            self.table_files.insertRow(rowPosition)
            # для размещения данных в ячейке таблицы, надо убедиться, что они string и разместить их в QTableWidgetItem
            item1 = QtWidgets.QTableWidgetItem(f[0])
            # Указать им ориентацию по центру
            item1.setTextAlignment(QtCore.Qt.AlignCenter)
            # Указать, что ячейку нельзя редактировать
            item1.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            # и, наконец, разместить в нужной ячейке по координатом строки и столбца
            self.table_files.setItem(rowPosition, 0, item1)
            # повторить для каждой ячейки, куда надо внести данные.
            item2 = QtWidgets.QTableWidgetItem(time.strftime('%m/%d/%Y-%H.%M.%S', f[1]))
            item2.setTextAlignment(QtCore.Qt.AlignCenter)
            item2.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
            self.table_files.setItem(rowPosition, 1, item2)
        # Устанавливаем ориентацию по центру по вертикали.
        header = self.table_files.verticalHeader()
        header.setDefaultAlignment(Qt.AlignHCenter)

    """Метод инициализации формы"""
    def activate(self):
        # Устанавливаем заголовок
        self.setWindowTitle('FileManager')
        # Устанавливаем размеры
        self.setGeometry(300, 300, 500, 300)
        # Загружаем языковые настройки
        self.languages(self.parent.languages.get_file_manager_title())

        self.setWindowModality(Qt.ApplicationModal)
        # Отображаем форму
        self.show()
        # Размещаем по центру
        base_pos_x = self.parent.t1.window().pos().x()
        base_pos_y = self.parent.t1.window().pos().y()
        #width_parent = self.parent.t1.window().frameGeometry().width()
        #height_parent = self.parent.t1.window().frameGeometry().height()
        width_parent = 1280
        height_parent = 720
        width_child = self.frameGeometry().width()
        height_child = self.frameGeometry().height()
        a = base_pos_x + width_parent / 2 - width_child / 2
        b = base_pos_y + height_parent / 2 - height_child / 2
        self.move(a, b)


    """Метод для установки заголовков в соответствии с языком."""
    def languages(self, title):
        self.Button_FM_OK.setText(title[0])
        self.Button_FM_Cancel.setText(title[1])
        self.table_files.horizontalHeaderItem(0).setText(title[2])
        self.table_files.horizontalHeaderItem(1).setText(title[3])

    def init_ui(self):
        self.setObjectName("FileManager")
        self.setWindowFlags(Qt.WindowTitleHint)
        self.resize(500, 300)
        self.setMinimumSize(QtCore.QSize(500, 300))
        self.setMaximumSize(QtCore.QSize(500, 300))
        self.setWindowFilePath("")
        self.Button_FM_OK = QtWidgets.QPushButton(self)
        self.Button_FM_OK.setGeometry(QtCore.QRect(10, 260, 235, 30))
        self.Button_FM_OK.setObjectName("Button_FM_OK")
        self.Button_FM_Cancel = QtWidgets.QPushButton(self)
        self.Button_FM_Cancel.setGeometry(QtCore.QRect(255, 260, 235, 30))
        self.Button_FM_Cancel.setObjectName("Button_FM_Cancel")
        QtCore.QMetaObject.connectSlotsByName(self)
        self.window = self
        self.table_files = QtWidgets.QTableWidget(self)
        self.table_files.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_files.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_files.setGeometry(QtCore.QRect(10, 10, 480, 240))
        self.table_files.setMinimumSize(QtCore.QSize(480, 240))
        self.table_files.setMaximumSize(QtCore.QSize(480, 240))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        self.table_files.setFont(font)
        self.table_files.setAutoFillBackground(False)
        self.table_files.setFrameShape(QtWidgets.QFrame.WinPanel)
        self.table_files.setLineWidth(1)
        self.table_files.setMidLineWidth(1)
        self.table_files.setAutoScroll(False)
        self.table_files.setTextElideMode(QtCore.Qt.ElideMiddle)
        self.table_files.setWordWrap(True)
        self.table_files.setObjectName("t1_tableMeasurement")
        self.table_files.setColumnCount(2)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.table_files.setVerticalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.table_files.setHorizontalHeaderItem(0, item)
        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        self.table_files.setHorizontalHeaderItem(1, item)

        item = QtWidgets.QTableWidgetItem()
        item.setTextAlignment(QtCore.Qt.AlignCenter)
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(10)
        item.setFont(font)
        brush = QtGui.QBrush(QtGui.QColor(0, 0, 0))
        brush.setStyle(QtCore.Qt.NoBrush)
        item.setBackground(brush)
        self.table_files.setItem(0, 0, item)
        self.table_files.horizontalHeader().setVisible(True)
        self.table_files.horizontalHeader().setCascadingSectionResizes(False)
        # self.table_files.horizontalHeader().setDefaultSectionSize(70)
        self.table_files.horizontalHeader().setHighlightSections(True)
        # self.table_files.horizontalHeader().setMinimumSectionSize(50)
        self.table_files.horizontalHeader().setSortIndicatorShown(False)
        self.table_files.horizontalHeader().setStretchLastSection(True)
        self.table_files.verticalHeader().setVisible(True)
        self.table_files.verticalHeader().setCascadingSectionResizes(True)
        # self.table_files.verticalHeader().setDefaultSectionSize(25)
        self.table_files.verticalHeader().setHighlightSections(False)
        # self.table_files.verticalHeader().setMinimumSectionSize(25)
        self.table_files.verticalHeader().setSortIndicatorShown(False)
        self.table_files.verticalHeader().setStretchLastSection(False)
        self.table_files.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.table_files.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        self.table_files.horizontalHeader().setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("FileManager", "Dialog_InputMeasurement"))
        self.Button_FM_OK.setText(_translate("FileManager", "Button_FM_OK"))
        self.Button_FM_Cancel.setText(_translate("FileManager", "Button_FM_Cancel"))
        _translate = QtCore.QCoreApplication.translate
        item = self.table_files.horizontalHeaderItem(0)
        item.setText(_translate("FileManager", "Название"))
        item = self.table_files.horizontalHeaderItem(1)
        item.setText(_translate("FileManager", "Изменен"))
        __sortingEnabled = self.table_files.isSortingEnabled()
        self.table_files.setSortingEnabled(False)
        self.table_files.setSortingEnabled(__sortingEnabled)
        self.Button_FM_OK.clicked.connect(self.ok)
        self.Button_FM_Cancel.clicked.connect(self.reject)

    """Метод обработки отмены ввода данных в форму."""
    def ok(self):
        if len(self.table_files.selectionModel().selectedRows()) > 0:
            self.accept()

    """Метод обработки введенных данных и передачу их в соответсвующий класс."""
    def get_file(self):
        file = ''
        if len(self.table_files.selectionModel().selectedRows()) > 0:
            file = os.path.join(self.dir, self.table_files.item(self.table_files.currentItem().row(), 0).text())
        return file



# if __name__ == '__main__':
#     app = QApplication(sys.argv)
#     ex = UiFileManager()
#     sys.exit(app.exec_())




