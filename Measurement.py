#!/usr/bin/python
"""Проверака и комментари: 07.01.2019"""

"""
"Класс для хранения данных для таблицы "Измерения"    
    self.p0 - float, давление P0
    self.p1 - float, давление P1
    self.p2 - float, давление P2
    self.volume - float, Объем для P, считается как:    ((P2 - P0) * (Vd + Vc) - (P1 - P0) * Vd) / (P2 - P0)
    self.density = float, Плотность для P, считается как    (mass / volume)
    self.deviation = float, Отклонение для P в процентах, считается как:    
                                                        (ср. объем для P - объем для P) / ср. объем для P * 100
    self.active - bool, переключатель, показывает надо ли учитывать данный экземляр данных измерений в рассчетах.
"""


class Measurement(object):
    """docstring"""

    """Конструктор класса. Поля класса"""
    def __init__(self):
        self.p0 = 0.0
        self.p1 = 0.0
        self.p2 = 0.0
        self.volume = 0.0
        self.density = 0.0
        self.deviation = 0.0
        self.active = True

    """Метод для сохранения данных измерений в экземпляре класса"""
    def set_measurement(self, _p0, _p1, _p2, _volume, _density, _deviation):
        self.p0 = _p0
        self.p1 = _p1
        self.p2 = _p2
        self.volume = _volume
        self.density = _density
        self.deviation = _deviation

    """Метод для включения данного экземляра данных измерений в рассчеты"""
    def set_active_on(self):
        self.active = True

    """Метод для исключения данного экземляра данных измерений в рассчеты"""
    def set_active_off(self):
        self.active = False

    """Метод для сброса данных измерений в экземпляре класса"""
    def clear_measurement(self):
        self.p0 = 0.0
        self.p1 = 0.0
        self.p2 = 0.0
        self.volume = 0.0
        self.density = 0.0
        self.deviation = 0.0

    def is_active(self):
        result = False
        if self.active:
            result = True
        return result
