# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'SamplePreparation.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!
import threading
import time

from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog


class UiSamplePreparation(QDialog):

    """Конструктор класса. Поля класса"""

    def __init__(self, parent, type, valua):
        super().__init__()
        self.parent = parent
        self.type = type
        self.valua = valua
        self.init_ui()

    """Метод инициализации формы"""

    def activate(self):
        # Устанавливаем заголовок
        self.setWindowTitle('SamplePreparation')
        # Устанавливаем размеры
        self.setGeometry(0, 0, 280, 100)
        # Загружаем языковые настройки
        """Метод для установки заголовков в соответствии с языком."""
        self.setWindowTitle(self.parent.languages.get_sample_preparation_title())
        self.setWindowModality(Qt.ApplicationModal)
        # Отображаем форму
        self.show()
        # Размещаем по центру
        base_pos_x = self.parent.t1.window().pos().x()
        base_pos_y = self.parent.t1.window().pos().y()
        # width_parent = self.parent.t1.window().frameGeometry().width()
        # height_parent = self.parent.t1.window().frameGeometry().height()
        width_parent = 1280
        height_parent = 720
        width_child = self.frameGeometry().width()
        height_child = self.frameGeometry().height()
        a = base_pos_x + width_parent / 2 - width_child / 2
        b = base_pos_y + height_parent / 2 - height_child / 2
        self.move(a, b)

        self.my_thread = threading.Thread(target = self.progress_bar_run)
        # Запускаем поток и процедуру измерения давления
        self.my_thread.start()

    def progress_bar_run(self):
        t = 0
        while t < self.valua:
            time.sleep(1)
            t += 1
            self.prb_SamplePreparation.setValue(t)
        # time.sleep(2)
        self.close()

    def init_ui(self):
        self.setObjectName("DialogSamplePreparation")
        self.setWindowFlags(Qt.WindowTitleHint)
        self.resize(280, 100)
        self.prb_SamplePreparation = QtWidgets.QProgressBar(self)
        self.prb_SamplePreparation.setGeometry(QtCore.QRect(10, 60, 261, 23))
        self.prb_SamplePreparation.setMaximum(self.valua)
        self.prb_SamplePreparation.setValue(0)
        self.prb_SamplePreparation.setObjectName("prb_SamplePreparation")
        self.lblSamplePreparation = QtWidgets.QLabel(self)
        self.lblSamplePreparation.setGeometry(QtCore.QRect(20, 20, 241, 21))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        self.lblSamplePreparation.setFont(font)
        self.lblSamplePreparation.setAlignment(QtCore.Qt.AlignCenter)
        self.lblSamplePreparation.setObjectName("lblSamplePreparation")
        QtCore.QMetaObject.connectSlotsByName(self)
        _translate = QtCore.QCoreApplication.translate
        self.setWindowTitle(_translate("DialogSamplePreparation", "SamplePreparation"))
        self.lblSamplePreparation.setText(self.type)


# if __name__ == "__main__":
#     import sys
#     app = QtWidgets.QApplication(sys.argv)
#     DialogSamplePreparation = QtWidgets.QDialog()
#     ui = Ui_DialogSamplePreparation()
#     ui.setupUi(DialogSamplePreparation)
#     DialogSamplePreparation.show()
#     sys.exit(app.exec_())

