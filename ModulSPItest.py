#!/usr/bin/python
# Модуль для считывания данных с датчика (Тестовая версия!!!)
import inspect
import os
import random
import threading
import time
"""Проверака и комментари: 13.01.2019"""

"""
"Класс для работы программы в тестовом режиме под Windows"    
    self.config - ссылка на модуль настроек
    self.temp_channel - must be an integer 0-7
    self.t - время ожидания между замерами давления
    self.smq_now - сколько замеров мы делаем для получения среднего давления
    self.spi - модуль SPI
    self.spi.max_speed_hz  - максимальная скорость
    self.test_on - bool, переключатель, показывает выполняется ли в данный момент измерение или нет.      
    self.file - записываем название текущего файла 'CalibrationProcedure.py'
    self.debug_log - ссылка на модуль для записи логов программы
    self.measurement_log - ссылка на модуль для записи логов прибора
    self.message - ссылка на СИГНАЛ, для вывода полученного давления на форму
"""

class SPI(object):
    """docstring"""

    """Конструктор класса. Поля класса"""
    def __init__(self, main):
        self.main = main
        self.config = self.main.config
        self.t = 0
        self.temp_channel = 0        
        # я все еще не уверен до конца, но кажется это нигде не используется.
        # self.smq_min = 0
        # self.smq_max = 0
        self.smq_now = 0
        self.test_on = False
        self.spi_max_speed_hz = 0
        self.set_option()
        self.file = os.path.basename(__file__)
        self.debug_log = self.main.debug_log
        self.measurement_log = self.main.measurement_log
        self.message = self.main.set_pressure_message
        self.correct_data = 0

    def set_correct_data(self, x):
        self.config.set_correct_data(x)
        self.correct_data = self.config.correct_data

    """Метод для применения настроек"""
    def set_option(self):
        # Тест должен быть выключен для применения настроек. Ситуации, когда настройки применяются, а он включен
        # быть не должно, но на всякий случай мы явно вызовем его выключение.
        self.close_test()
        # Присваиваем значения.
        self.t = self.config.periodicity_of_removal_of_sensor_reading
        self.spi_max_speed_hz = self.config.spi_max_speed_hz
        self.smq_now = self.config.smq_now

    """Метод для проверки. Возвращает True, если измерение давления запущено иначе False"""
    def is_test_on(self):
        result = False
        if self.test_on:
            result = True
        return result

    """Метод для установки состояния переключателя работы измерения давления в положение True/False"""
    def set_test_on(self, s):
        self.test_on = s

    """Метод для запуска отдельного потока для измерения давления"""
    def start_test(self):
        # Проверяем, что измерение давления еще не запущео
        if not self.is_test_on():
            # Устанавливаем состояние в режим "запущена"
            self.set_test_on(True)
            # Это команда присваивает отдельному потоку исполняемую процедуру калибровки
            self.my_thread = threading.Thread(target=self.implementation_test)
            # Запускаем поток и процедуру измерения давления
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Thread "Pressure measurement" started in the TEST MODE')
            self.my_thread.start()

    """Метод для выключения отдельного потока калибровки прибора"""
    def close_test(self):
        # Проверяем, что измерение давления запущено
        if self.is_test_on():
            # Устанавливаем состояние в режим "не запущено"
            self.set_test_on(False)
            # Вызываем выключение потока
            self.my_thread.join()
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Thread "Pressure measurement" finished '
                                                                         'in the TEST MODE')

    """Метод, где расположена процедура обработки измерения давления в отдельном потоке"""
    def implementation_test(self):
        # до тех пор пока процедура активна
        # (а она активна, пока пользователь не покинет вкладку "Ручное управление") выполняем:
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Pressure measurement for Manual control started\nself.spi.max_speed_hz = {0}'
                                   '\nself.t = {1}\nself.smq_now  = {2}'.format(str(self.spi_max_speed_hz),
                                                                                str(self.t), str(self.smq_now)))
        while self.test_on:
            # получить давление
            p = self.get_pressure()
            self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                       'Pressure = {0}'.format(p))
            # отправляем сообщение о том, что давление рассчитано и его можно выводить в форму
            self.message.emit(p)
            # ожидание в соответсвии с config.ini
            time.sleep(self.t)
        self.measurement_log.debug(self.file, inspect.currentframe().f_lineno,
                                   'Pressure measurement for Manual control finished')

    """Метод, где мы получаем данные с датчика"""
    def read_channel(self):
        # инициализируем под измерение переменную data
        data = 0
        # это для тестового режима, чтобы генерить данные вместо получения с датчика
        p_num1 = 0
        p_num2 = 1000000
        # делаем цикл по требуемому количеству замеров согласно config.ini
        for i in range(self.smq_now):
            # считываем данные с датчика /// ну типо того
            data = data + random.randint(p_num1, p_num2) / 1000
        # берем среднее значение
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation data.....')
        try:
            data = data / self.smq_now
        except ArithmeticError:
            self.debug_log.debug(self.file, inspect.currentframe().f_lineno,
                                 'Division by zero when calculating data, '
                                 'denominator: self.smq_now = {0}'.format(str(self.smq_now)))
            data = 0
        self.debug_log.debug(self.file, inspect.currentframe().f_lineno, 'Calculation data..... Done.')
        return data

    """Метод рассчета давления на основание данных с датчика"""
    def calc_pressure(self, data):
        # считаем сразу в кПа, Бар и psi и заворачиваем в массив
        p1 = self.getkPa(data)  # кПа
        p2 = self.getBar(data)  # Бар
        p3 = self.getPsi(data)  # psi
        # Возвращаем массив
        return [p1, p2, p3]

    """Метод для получения давления с датчика"""
    def get_pressure(self, p_num = "p2"):
        # вместо данных с датчика мы их тут наигрываем через рандом
        data = 0
        p_num1 = 0
        p_num2 = 0
        if p_num == 'p0':
            p_num1 = 0
            p_num2 = 0
        if p_num == 'p1':
            p_num1 = 900
            p_num2 = 1000
        if p_num == 'p2':
            p_num1 = 300
            p_num2 = 600
        for i in range(100):
            data = data + random.randint(p_num1, p_num2)
        data = data / 100
        p = self.calc_pressure(data)
        s = p[self.config.pressure.value]
        return s

        """Метод, который на основание измерения высчитывает давление в кПа"""
    def getkPa(self, data):
        p = data / 1023 * 130 # кПа
        return p

    """Метод, который на основание измерения высчитывает давление в Бар"""
    def getBar(self, data):
        p = data / 1023 * 1.3  # Бар
        return p

    """Метод, который на основание измерения высчитывает давление в psi"""
    def getPsi(self, data):
        p = data / 1023 * 130 * 0.14503773773  # psi
        return p

    """Метод, который возвращает из давление в кПа значение измерения"""
    def getDataFromkPa(self, p):
        data = p * 1023 / 130  # кПа
        return data

    """Метод, который возвращает из давление в Бар значение измерения"""
    def getDataFromBar(self, p):
        data = p * 1023 / 1.3  # кПа
        return data

    """Метод, который возвращает из давление в psi значение измерения"""
    def getDataFromPsi(self, p):
        data = p * 1023 / 130 / 0.14503773773  # кПа
        return data