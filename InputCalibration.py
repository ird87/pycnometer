#!/usr/bin/python
# Модуль открывается в виде отдельной формы, для ввода данных под таблицу "Измерения".
import sys
from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import (QWidget, QApplication)
from Calibration import Calibration
"""Проверака и комментари: 08.01.2019"""

"""
"Класс реализует форму для ручного ввода данных для таблицы "Калибровка"
"""

class UiInputCalibration(QWidget):

    """Конструктор класса. Поля класса"""
    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.init_ui()

    """Метод инициализации формы"""
    def activate(self):
        # Устанавливаем заголовок
        self.setWindowTitle('InputCalibration')
        # Устанавливаем размеры
        self.setGeometry(300, 300, 400, 260)
        # Загружаем языковые настройки
        self.languages(self.parent.inputCalibrationHeader)
        # Отображаем форму
        self.show()
        # Размещаем по центру
        base_pos_x = self.parent.window.pos().x()
        base_pos_y = self.parent.window.pos().y()
        width_parent = self.parent.window.frameGeometry().width()
        height_parent = self.parent.window.frameGeometry().height()
        width_child = self.frameGeometry().width()
        height_child = self.frameGeometry().height()
        a = base_pos_x + width_parent / 2 - width_child / 2
        b = base_pos_y + height_parent / 2 - height_child / 2
        self.move(a, b)

    """Метод для установки заголовков в соответствии с языком."""
    def languages(self, title):
        self.lbl_InputCalibration1.setText(title[0])
        self.lbl_InputCalibration2.setText(title[1])
        self.lbl_InputCalibration3.setText(title[2])
        self.lbl_InputCalibration4.setText(title[3])
        self.lbl_InputCalibration5.setText(title[4])
        self.lbl_InputCalibration6.setText(title[5])
        self.Button_InputCalibration_OK.setText(title[6])
        self.Button_InputCalibration_Cancel.setText(title[7])

    """Группа методов для смены фокусов по нажатию на "Enter"""
    def on_click1(self):
        self.Edit_InputCalibration2.setFocus()

    def on_click2(self):
        self.Edit_InputCalibration3.setFocus()

    def on_click3(self):
        self.Edit_InputCalibration4.setFocus()

    def on_click4(self):
        self.Edit_InputCalibration5.setFocus()

    def on_click5(self):
        self.Edit_InputCalibration6.setFocus()

    def on_click6(self):
        self.Button_InputCalibration_OK.setFocus()

    """Метод проверяет все ли поля были заполнены и если нет - 
    сообщает номер первого незаполненного поля (сверху-вниз)"""
    def is_data_complete(self):
        result1 = True
        result2 = 0
        if self.Edit_InputCalibration1.text() == '':
            result1 = False
            result2 = 1
        else:
            if self.Edit_InputCalibration2.text() == '':
                result1 = False
                result2 = 2
            else:
                if self.Edit_InputCalibration3.text() == '':
                    result1 = False
                    result2 = 3
                else:
                    if self.Edit_InputCalibration4.text() == '':
                        result1 = False
                        result2 = 4
                    else:
                        if self.Edit_InputCalibration5.text() == '':
                            result1 = False
                            result2 = 5
                        else:
                            if self.Edit_InputCalibration6.text() == '':
                                result1 = False
                                result2 = 6
        return result1, result2

    """Метод обработки отмены ввода данных в форму."""
    def cancel(self):
        self.hide()

    """Метод обработки введенных данных и передачу их в соответсвующий класс."""
    def ok(self):
        is_data_complete = self.is_data_complete()
        if is_data_complete[0]:
            calibration = Calibration()
            calibration.set_calibration(self.Edit_InputCalibration1.text(), float(self.Edit_InputCalibration2.text()),
                            float(self.Edit_InputCalibration3.text()), float(self.Edit_InputCalibration4.text()),
                            float(self.Edit_InputCalibration5.text()), float(self.Edit_InputCalibration6.text()))
            self.hide()

    """Это UI"""
    def init_ui(self):
        w, h = 400, 230
        self.setWindowModality(True)
        self.setMinimumSize(w, h)
        self.setMaximumSize(w, h)
        self.setGeometry(0, 0, 400, 230)
        self.setWindowTitle('InputCalibration')
        self.Edit_InputCalibration1 = QtWidgets.QLineEdit(self)
        self.Edit_InputCalibration1.setGeometry(QtCore.QRect(180, 10, 211, 20))
        self.Edit_InputCalibration1.setAlignment(QtCore.Qt.AlignCenter)
        self.Edit_InputCalibration1.setObjectName("Edit_InputCalibration1")
        self.Edit_InputCalibration1.returnPressed.connect(self.on_click1)
        self.Edit_InputCalibration2 = QtWidgets.QLineEdit(self)
        self.Edit_InputCalibration2.setGeometry(QtCore.QRect(180, 40, 211, 20))
        self.Edit_InputCalibration2.setAlignment(QtCore.Qt.AlignCenter)
        self.Edit_InputCalibration2.setObjectName("Edit_InputCalibration2")
        self.Edit_InputCalibration2.returnPressed.connect(self.on_click2)
        self.Edit_InputCalibration3 = QtWidgets.QLineEdit(self)
        self.Edit_InputCalibration3.setGeometry(QtCore.QRect(180, 70, 211, 20))
        self.Edit_InputCalibration3.setAlignment(QtCore.Qt.AlignCenter)
        self.Edit_InputCalibration3.setObjectName("Edit_InputCalibration3")
        self.Edit_InputCalibration3.returnPressed.connect(self.on_click3)
        self.Edit_InputCalibration4 = QtWidgets.QLineEdit(self)
        self.Edit_InputCalibration4.setGeometry(QtCore.QRect(180, 100, 211, 20))
        self.Edit_InputCalibration4.setAlignment(QtCore.Qt.AlignCenter)
        self.Edit_InputCalibration4.setObjectName("Edit_InputCalibration4")
        self.Edit_InputCalibration4.returnPressed.connect(self.on_click4)
        self.Edit_InputCalibration5 = QtWidgets.QLineEdit(self)
        self.Edit_InputCalibration5.setGeometry(QtCore.QRect(180, 130, 211, 20))
        self.Edit_InputCalibration5.setAlignment(QtCore.Qt.AlignCenter)
        self.Edit_InputCalibration5.setObjectName("Edit_InputCalibration5")
        self.Edit_InputCalibration5.returnPressed.connect(self.on_click5)
        self.Edit_InputCalibration6 = QtWidgets.QLineEdit(self)
        self.Edit_InputCalibration6.setGeometry(QtCore.QRect(180, 160, 211, 20))
        self.Edit_InputCalibration6.setAlignment(QtCore.Qt.AlignCenter)
        self.Edit_InputCalibration6.setObjectName("Edit_InputCalibration6")
        self.Edit_InputCalibration6.returnPressed.connect(self.on_click6)
        self.lbl_InputCalibration1 = QtWidgets.QLabel(self)
        self.lbl_InputCalibration1.setGeometry(QtCore.QRect(10, 10, 160, 20))
        self.lbl_InputCalibration1.setObjectName("lbl_InputCalibration1")
        self.lbl_InputCalibration2 = QtWidgets.QLabel(self)
        self.lbl_InputCalibration2.setGeometry(QtCore.QRect(10, 40, 160, 20))
        self.lbl_InputCalibration2.setObjectName("lbl_InputCalibration2")
        self.lbl_InputCalibration3 = QtWidgets.QLabel(self)
        self.lbl_InputCalibration3.setGeometry(QtCore.QRect(10, 70, 160, 20))
        self.lbl_InputCalibration3.setObjectName("lbl_InputCalibration3")
        self.lbl_InputCalibration4 = QtWidgets.QLabel(self)
        self.lbl_InputCalibration4.setGeometry(QtCore.QRect(10, 100, 160, 20))
        self.lbl_InputCalibration4.setObjectName("lbl_InputCalibration4")
        self.lbl_InputCalibration5 = QtWidgets.QLabel(self)
        self.lbl_InputCalibration5.setGeometry(QtCore.QRect(10, 130, 160, 20))
        self.lbl_InputCalibration5.setObjectName("lbl_InputCalibration5")
        self.lbl_InputCalibration6 = QtWidgets.QLabel(self)
        self.lbl_InputCalibration6.setGeometry(QtCore.QRect(10, 160, 160, 20))
        self.lbl_InputCalibration6.setObjectName("lbl_InputCalibration6")
        self.Button_InputCalibration_OK = QtWidgets.QPushButton(self)
        self.Button_InputCalibration_OK.setGeometry(QtCore.QRect(20, 190, 151, 31))
        self.Button_InputCalibration_OK.setObjectName("Button_InputCalibration_OK")
        self.Button_InputCalibration_OK.clicked.connect(self.ok)
        self.Button_InputCalibration_Cancel = QtWidgets.QPushButton(self)
        self.Button_InputCalibration_Cancel.setGeometry(QtCore.QRect(210, 190, 151, 31))
        self.Button_InputCalibration_Cancel.setObjectName("Button_InputCalibration_Cancel")
        self.Button_InputCalibration_Cancel.clicked.connect(self.cancel)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    ex = UiInputCalibration()
    sys.exit(app.exec_())
