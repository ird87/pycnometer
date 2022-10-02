# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'Progressbar.ui'
#
# Created by: PyQt5 UI code generator 5.11.3
#
# WARNING! All changes made in this file will be lost!
import time

from PyQt5 import QtCore, QtGui, QtWidgets, uic
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog


class UiProgressbar(QDialog):

    """Конструктор класса. Поля класса"""

    def __init__(self, parent, title, msg, valua):
        super(UiProgressbar, self).__init__()
        uic.loadUi('ui/Progressbar.ui', self)
        self.parent = parent
        self.msg = msg
        self.valua = valua
        self.title = title
        self.init_ui()
        self.pause = False
        self.abort = False

    """Метод инициализации формы"""

    def activate(self):
        # Устанавливаем заголовок
        self.setWindowTitle(self.title)
        # Устанавливаем размеры
        self.setGeometry(0, 0, 280, 100)
        # Загружаем языковые настройки
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

        # self.my_thread = threading.Thread(target = self.progress_bar_run)
        # # Запускаем поток и процедуру измерения давления
        # self.my_thread.start()

    # def progress_bar_run(self):
    #     t = 0
    #     lock = threading.Lock()
    #     while t < self.valua:
    #         time.sleep(1)
    #         t += 1
    #         self.prb_Progressbar.setValue(t)
    #     # time.sleep(2)
    #     self.accept()

    def add_progress(self, t):
        if self.prb_Progressbar.value() < self.prb_Progressbar.maximum():
            self.prb_Progressbar.setValue(self.prb_Progressbar.value() + t)

    def exit(self):
        while self.prb_Progressbar.value() < self.prb_Progressbar.maximum():
            time.sleep(1)
            self.prb_Progressbar.setValue(self.prb_Progressbar.value() + 1)
            time.sleep(2)
        self.accept()

    def init_ui(self):
        self.setObjectName("DialogProgressbar")
        self.setWindowFlags(Qt.WindowTitleHint)
        self.resize(280, 100)
        self.prb_Progressbar = QtWidgets.QProgressBar(self)
        self.prb_Progressbar.setGeometry(QtCore.QRect(10, 60, 261, 23))
        self.setMinimumSize(QtCore.QSize(280, 100))
        self.setMaximumSize(QtCore.QSize(280, 100))
        self.prb_Progressbar.setMaximum(self.valua)
        self.prb_Progressbar.setValue(0)
        self.prb_Progressbar.setObjectName("prb_Progressbar")
        self.lblProgressbar = QtWidgets.QLabel(self)
        self.lblProgressbar.setGeometry(QtCore.QRect(20, 20, 241, 21))
        font = QtGui.QFont()
        font.setFamily("Arial")
        font.setPointSize(12)
        self.lblProgressbar.setFont(font)
        self.lblProgressbar.setAlignment(QtCore.Qt.AlignCenter)
        self.lblProgressbar.setObjectName("lblProgressbar")
        QtCore.QMetaObject.connectSlotsByName(self)
        _translate = QtCore.QCoreApplication.translate
        self.lblProgressbarMsg.setText(self.msg)


# if __name__ == "__main__":
#     import sys
#     app = QtWidgets.QApplication(sys.argv)
#     DialogProgressbar = QtWidgets.QDialog()
#     ui = Ui_DialogProgressbar()
#     ui.setupUi(DialogProgressbar)
#     DialogProgressbar.show()
#     sys.exit(app.exec_())

