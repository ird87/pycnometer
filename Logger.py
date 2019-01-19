#!/usr/bin/python
import datetime
import logging
import os
"""Проверака и комментари: 08.01.2019"""

"""
"Класс для записи логов работы программы и работы прибора из любого модуля"    
    self.type - string, это и назначение логгера и имя файла в папке логов.
    self.config - ссылка на модуль с настройками программы
    self.logger - сюда вызываем сам логгер
    self.now - текущие дата и время
    self.logname - string, для записи полного пути к файлу
    self.fh - handler for logger
"""

class Logger(object):
    """docstring"""

    """Конструктор класса. Поля класса"""
    def __init__(self, _type, config):
        self.type = _type
        self.config = config
        self.logger = logging.getLogger("exampleApp")
        self.now = datetime.datetime.now()
        self.logname = ''
        self.fh = ''

    """Метод вывода сообщения в логфайл"""
    def debug(self, module, _line, _message):
        # мы получаем имя модуля, вызвавшего запись в логи, номер строки из которой пошел вызов и текст сообщения.
        # номер строки надо преобразовать в текст
        line = str(_line)
        # на основание полученного сообщения необходимо сформировать типовое лог-сообщение. Которое помимо сообщения
        # содержит данные по дате и времени вызова сообщения, источнику вызова и номеру строки.
        message = "[{0}]  {1}  [LINE:{2}]  #{3}  \n{4}".format(self.now.strftime("%d-%m-%Y %H:%M"), module, line,
                                                               logging.getLevelName(self.logger.level), _message)
        # теперь создаем форматтер из нашего сообщения.
        formatter = logging.Formatter(u'%(message)s')
        # назначаем его нашему handler'у
        self.fh.setFormatter(formatter)
        # и добавляем в логгер
        self.logger.addHandler(self.fh)
        # Выводим сообщение в лог файл
        self.logger.debug(message)
        # И исключаем из логгера.
        self.logger.removeHandler(self.fh)

    """Метод установок настроек"""
    def setup(self):
        # устанавливаем уровень лога
        self.logger.setLevel(logging.DEBUG)
        # создаем из текущих даты, времени и типа логгера название файла
        self.logname = self.type + ' - ' + self.get_today_date()

        # create the logging file handler уже через полное имя файла
        if self.config.is_test_mode():
            # для тестового режима (Windows) нужны такие команды:
            self.fh = logging.FileHandler(os.getcwd() + '\Logs\\' + self.logname + '.log')
        if not self.config.is_test_mode():
            # для нормального режима (Linux) нужны такие команды:
            self.fh = logging.FileHandler(os.getcwd() + '/Logs/' + self.logname + '.log', encoding='WINDOWS-1251')

    """Метод получения текущей дате в формате год-месяц-день, так нужно для удобства сортировки файлов в папке"""
    def get_today_date(self):
        logname = self.now.strftime("%Y-%m-%d")
        return logname
