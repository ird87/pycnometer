#!/usr/bin/python
"""Проверака и комментари: 07.01.2019"""

"""
"Класс для хранения данных для таблицы "Калибровка"
    self.measurement - принимает значения типа string, может быть либо P либо P'
    self.p0 - float, давление P0 либо P0'
    self.p1 - float, давление P1 либо P1'
    self.p2 - float, давление P2 либо P2'
    self.ratio - float, Отношение для P иди P', считается как:   (P1 - P0) / (P2 - P0)     
                                                      или как:   (P1' - P0') / (P2' - P0')
    self.deviation - float, отклонение, считается в процентах отдельно для P и P' как:
                                (ср. отклонение для P - отклонение для P) / ср. отклонение для P * 100
                    или как:    (ср. отклонение для P' - отклонение для P') / ср. отклонение для P' * 100
    self.active - bool, переключатель, показывает надо ли учитывать данный экземляр данных калбровки в рассчетах.
"""


class Calibration(object):
    """docstring"""

    """Конструктор класса. Поля класса"""
    def __init__(self):
        self.measurement = ''
        self.p0 = 0.0
        self.p1 = 0.0
        self.p2 = 0.0
        self.ratio = 0.0
        self.deviation = 0.0
        self.active = True

    """Метод для сохранения данных калибровки в экземпляре класса"""
    def set_calibration(self, _measurement, _p0, _p1, _p2, _ratio, _deviation):
        self.measurement = _measurement
        self.p0 = _p0
        self.p1 = _p1
        self.p2 = _p2
        self.ratio = _ratio
        self.deviation = _deviation

    """Метод для включения данного экземляра данных калбровки в рассчеты"""
    def set_active_on(self):
        self.active = True

    """Метод для исключения данного экземляра данных калбровки в рассчеты"""
    def set_active_off(self):
        self.active = False

    """Метод для сброса данных калибровки в экземпляре класса"""
    def clear_calibration(self):
        self.measurement = 0.0
        self.p0 = 0.0
        self.p1 = 0.0
        self.p2 = 0.0
        self.ratio = 0.0
        self.deviation = 0.0

    def is_active(self):
        result = False
        if self.active:
            result = True
        return result