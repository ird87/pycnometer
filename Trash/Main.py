#!/usr/bin/python
import sys  # sys нужен для передачи argv в QApplication
from PyQt5 import QtWidgets
from PyQt5.QtWidgets import QWidget, QCheckBox, QApplication
from PyQt5.QtCore import Qt
import MainWindow  # Это наш конвертированный файл дизайна
from ModulRPIO import RPIO
#from ModulRPIOtest import RPIO
from Config import Configure




class ExampleApp(QtWidgets.QMainWindow, MainWindow.Ui_MainWindow):  # название файла с дизайном и название класса в нем.
    def __init__(self):
        #self.ports = [17, 22, 24, 0, 0]
        # Это здесь нужно для доступа к переменным, методам
        # и т.д. в файле design.py
        super().__init__()
        self.setupUi(self)  # Это нужно для инициализации нашего дизайна
        self.config=Configure()
        self.ports =self.config.GetPorts()
        self.rpio = RPIO()
        self.checkValve1.stateChanged.connect(self.onOffPort1)
        self.checkValve2.stateChanged.connect(self.onOffPort2)
        self.checkValve3.stateChanged.connect(self.onOffPort3)
        self.checkValve4.stateChanged.connect(self.onOffPort4)
        self.checkValve5.stateChanged.connect(self.onOffPort5)


        #Этот ужас временно, я узнаю как сделать список виджетов и станет лучше.

    def onOffPort1(self):

        if self.checkValve1.isChecked():
            self.rpio.PortOn(self.ports[0])
        else:
            self.rpio.PortOff(self.ports[0])

    def onOffPort2(self):

        if self.checkValve2.isChecked():
            self.rpio.PortOn(self.ports[1])
        else:
            self.rpio.PortOff(self.ports[1])

    def onOffPort3(self):

        if self.checkValve3.isChecked():
            self.rpio.PortOn(self.ports[2])
        else:
            self.rpio.PortOff(self.ports[2])

    def onOffPort4(self):

        if self.checkValve4.isChecked():
            self.rpio.PortOn(self.ports[3])
        else:
            self.rpio.PortOff(self.ports[3])

    def onOffPort5(self):

        if self.checkValve5.isChecked():
            self.rpio.PortOn(self.ports[4])
        else:
            self.rpio.PortOff(self.ports[4])

    def closeEvent(self, event):
        self.rpio.Exit()

def main():
    app = QtWidgets.QApplication(sys.argv)  # Новый экземпляр QApplication
    window = ExampleApp()  # Создаём объект класса ExampleApp
    window.show()  # Показываем окно
    app.exec_()  # и запускаем приложение


if __name__ == '__main__':  # Если мы запускаем файл напрямую, а не импортируем
    main()  # то запускаем функцию main()
