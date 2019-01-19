#!/usr/bin/python
# Модуль для загрузки используемого языка из Language/*.ini
import configparser
import json
import os

"""Проверака и комментари: 13.01.2019"""

"""
"Класс загружает все наименования, используемые в программе из файла в соответствии с выбранным языком.
    Все поля класса - это переменные для загрузки соответсвующих данных.
"""

class Languages(object):
    """docstring"""

    """Конструктор класса. Поля класса"""
    def __init__(self):
        self.languages = configparser.ConfigParser()
        self.mainWindow = ''
        self.t1 = ''
        self.t2 = ''
        self.t3 = ''

        # [InputMeasurement]
        self.Edit_InputMeasurement = []
        self.Button_InputMeasurement_OK = ''
        self.Button_InputMeasurement_Cancel = ''

        # [TAB1]
        self.t1_tableMeasurement_Column = []
        self.t1_groupGeneralInformation = ''
        self.t1_gMI_lbl1 = ''
        self.t1_gMI_lbl2 = ''
        self.t1_gMI_lbl3 = ''
        self.t1_gMI_lbl4 = ''
        self.t1_groupSamplePreparation = ''
        self.t1_gSP_gRB_rb1 = ''
        self.t1_gSP_gRB_rb2 = ''
        self.t1_gSP_gRB_rb3 = ''
        self.t1_gSP_lbl1 = ''
        self.t1_groupMeasurementResults = ''
        self.t1_gMR_lbl1 = ''
        self.t1_gMR_lbl2 = ''
        self.t1_gMR_lbl3 = ''
        self.t1_gMR_lbl4 = ''
        self.t1_groupMeasurement = ''
        self.t1_gM_lbl1 = ''
        self.t1_gM_lbl2 = ''
        self.t1_gM_lbl3 = ''
        self.t1_gM_lbl4 = ''
        self.t1_gM_cmd1_1 = ''
        self.t1_gM_cmd1_2 = ''
        self.t1_gM_cmd1_3 = ''
        self.t1_gM_button1 = ''
        self.t1_gM_button2 = ''
        self.t1_tableMeasurement_popup_Exclude = ''
        self.t1_tableMeasurement_popup_Include = ''
        self.t1_tableMeasurement_popup_Add = ''
        self.t1_tableMeasurement_popup_Recount = ''

        # [InputCalibration]
        self.Edit_InputCalibration = []
        self.Button_InputCalibration_OK = ''
        self.Button_InputCalibration_Cancel = ''

        # [TAB2]
        self.t2_tableCalibration_Column = []
        self.t2_groupCalibratonResult = ''
        self.t2_gCR_lbl1 = ''
        self.t2_gCR_lbl2 = ''
        self.t2_groupInitialData = ''
        self.t2_gID_lbl1 = ''
        self.t2_gID_lbl2 = ''
        self.t2_gID_lbl3 = ''
        self.t2_gID_cmd1_1 = ''
        self.t2_gID_cmd1_2 = ''
        self.t2_gID_cmd1_3 = ''
        self.t2_gID_button1 = ''
        self.t2_gID_button2 = ''
        self.t2_tableCalibration_popup_Exclude = ''
        self.t2_tableCalibration_popup_Include = ''
        self.t2_tableCalibration_popup_Add = ''
        self.t2_tableCalibration_popup_Recount = ''

        # [TAB3]
        self.t3_lblValve1 = ''
        self.t3_lblValve2 = ''
        self.t3_lblValve3 = ''
        self.t3_lblValve4 = ''
        self.t3_lblValve5 = ''
        self.t3_lbl_Helium = ''
        self.t3_lbl_Atmosphere = ''
        self.t3_lbl_Vacuum = ''
        self.t3_lblPressure1 = ''

        # [TAB4]
        self.t4_groupInterfaceSettings = ''
        self.t4_gIS_lbl1 = ''
        self.t4_button_1 = ''
        self.t4_button_2 = ''
        self.t4_groupMeasurementSettings = ''
        self.t4_gMS_lbl1 = ''
        self.t4_gMS_lbl2 = ''
        self.t4_gMS_lbl3 = ''
        self.t4_gMS_lbl4 = []

        # [MeasurementSetting]
        self.pressure_setting = []

        # [Menu]
        self.menu1 = ''
        self.menu1_command1 = ''
        self.menu2 = ''
        self.menu3 = ''
        self.menu4 = ''

        # [Message]
        self.message_headline1 = ''
        self.message_txt1 = ''
        self.message_txt2 = ''
        self.message_txt3 = ''



        self.file = os.path.basename(__file__)


        # Выбираем файл с языком в зависимости от прописанного в настройках Configure.ini

    """Метод для назначения файла, в качестве источника данных"""
    def setup(self, config):
        if config.is_test_mode():
            # для тестового режима (Windows) нужны такие команды:
            self.languages.read(os.getcwd() + '\Language\\' + config.get_language() + '.ini')
            print(os.getcwd() + '\Language\\' + config.get_language() + '.ini')
        if not config.is_test_mode():
            # для нормального режима (Linux) нужны такие команды:
            self.languages.read(os.getcwd() + '/Language/' + config.get_language() + '.ini', encoding='WINDOWS-1251')

    """Метод необходимый для загрузки из файлов символа '%', в файлах он заменен на 'U+0025', при загрузке из файла 
    любое значение проходит этот метод и преобразует данную строку в '%' """
    def get_string(self, section, variable):
        retVal = self.languages.get(section, variable)
        retVal = retVal.replace('U+0025', '%')
        return retVal

    """Метод загрузки всех данных из файла. Метод разбит на разделы в соответствии с файлами, содержащими данные"""
    def load(self,config):
        # [MAIN]
        self.mainWindow = self.get_string('MAIN', 'MainWindow')
        self.t1 = self.get_string('MAIN', 't1')
        self.t2 = self.get_string('MAIN', 't2')
        self.t3 = self.get_string('MAIN', 't3')
        self.t4 = self.get_string('MAIN', 't4')

        # [InputMeasurement]
        self.Edit_InputMeasurement.clear()
        self.Edit_InputMeasurement.append(self.get_string('InputMeasurement', 'Edit_InputMeasurement1'))
        self.Edit_InputMeasurement.append(self.get_string('InputMeasurement', 'Edit_InputMeasurement2'))
        self.Edit_InputMeasurement.append(self.get_string('InputMeasurement', 'Edit_InputMeasurement3'))
        self.Edit_InputMeasurement.append(self.get_string('InputMeasurement', 'Edit_InputMeasurement4'))
        self.Edit_InputMeasurement.append(self.get_string('InputMeasurement', 'Edit_InputMeasurement5'))
        self.Edit_InputMeasurement.append(self.get_string('InputMeasurement', 'Edit_InputMeasurement6'))
        self.Button_InputMeasurement_OK = self.get_string('InputMeasurement', 'Button_InputMeasurement_OK')
        self.Button_InputMeasurement_Cancel = self.get_string('InputMeasurement', 'Button_InputMeasurement_Cancel')

        # [TAB1]
        self.t1_tableMeasurement_Column.clear()
        self.t1_tableMeasurement_Column.append(self.get_string('TAB1', 't1_tableMeasurement_Column1'))
        self.t1_tableMeasurement_Column.append(self.get_string('TAB1', 't1_tableMeasurement_Column2'))
        self.t1_tableMeasurement_Column.append(self.get_string('TAB1', 't1_tableMeasurement_Column3'))
        self.t1_tableMeasurement_Column.append(self.get_string('TAB1', 't1_tableMeasurement_Column4'))
        self.t1_tableMeasurement_Column.append(self.get_string('TAB1', 't1_tableMeasurement_Column5'))
        self.t1_tableMeasurement_Column.append(self.get_string('TAB1', 't1_tableMeasurement_Column6'))
        self.t1_groupGeneralInformation = self.get_string('TAB1', 't1_groupGeneralInformation')
        self.t1_gMI_lbl1 = self.get_string('TAB1', 't1_gMI_lbl1')
        self.t1_gMI_lbl2 = self.get_string('TAB1', 't1_gMI_lbl2')
        self.t1_gMI_lbl3 = self.get_string('TAB1', 't1_gMI_lbl3')
        self.t1_gMI_lbl4 = self.get_string('TAB1', 't1_gMI_lbl4')
        self.t1_groupSamplePreparation = self.get_string('TAB1', 't1_groupSamplePreparation')
        self.t1_gSP_gRB_rb1 = self.get_string('TAB1', 't1_gSP_gRB_rb1')
        self.t1_gSP_gRB_rb2 = self.get_string('TAB1', 't1_gSP_gRB_rb2')
        self.t1_gSP_gRB_rb3 = self.get_string('TAB1', 't1_gSP_gRB_rb3')
        self.t1_gSP_lbl1 = self.get_string('TAB1', 't1_gSP_lbl1')
        self.t1_groupMeasurementResults = self.get_string('TAB1', 't1_groupMeasurementResults')
        self.t1_gMR_lbl1 = self.get_string('TAB1', 't1_gMR_lbl1')
        self.t1_gMR_lbl2 = self.get_string('TAB1', 't1_gMR_lbl2')
        self.t1_gMR_lbl3 = self.get_string('TAB1', 't1_gMR_lbl3')
        self.t1_gMR_lbl4 = self.get_string('TAB1', 't1_gMR_lbl4')
        self.t1_groupMeasurement = self.get_string('TAB1', 't1_groupMeasurement')
        self.t1_gM_lbl1 = self.get_string('TAB1', 't1_gM_lbl1')
        self.t1_gM_lbl2 = self.get_string('TAB1', 't1_gM_lbl2')
        self.t1_gM_lbl3 = self.get_string('TAB1', 't1_gM_lbl3')
        self.t1_gM_lbl4 = self.get_string('TAB1', 't1_gM_lbl4')
        self.t1_gM_cmd1_1 = self.get_string('TAB1', 't1_gM_cmd1_1')
        self.t1_gM_cmd1_2 = self.get_string('TAB1', 't1_gM_cmd1_2')
        self.t1_gM_cmd1_3 = self.get_string('TAB1', 't1_gM_cmd1_3')
        self.t1_gM_button1 = self.get_string('TAB1', 't1_gM_button1')
        self.t1_gM_button2 = self.get_string('TAB1', 't1_gM_button2')
        self.t1_tableMeasurement_popup_Exclude = self.get_string('TAB1', 't1_tableMeasurement_popup_Exclude')
        self.t1_tableMeasurement_popup_Include = self.get_string('TAB1', 't1_tableMeasurement_popup_Include')
        self.t1_tableMeasurement_popup_Add = self.get_string('TAB1', 't1_tableMeasurement_popup_Add')
        self.t1_tableMeasurement_popup_Recount = self.get_string('TAB1', 't1_tableMeasurement_popup_Recount')

        # [InputCalibration]
        self.Edit_InputCalibration.clear()
        self.Edit_InputCalibration.append(self.get_string('InputCalibration', 'Edit_InputCalibration1'))
        self.Edit_InputCalibration.append(self.get_string('InputCalibration', 'Edit_InputCalibration2'))
        self.Edit_InputCalibration.append(self.get_string('InputCalibration', 'Edit_InputCalibration3'))
        self.Edit_InputCalibration.append(self.get_string('InputCalibration', 'Edit_InputCalibration4'))
        self.Edit_InputCalibration.append(self.get_string('InputCalibration', 'Edit_InputCalibration5'))
        self.Edit_InputCalibration.append(self.get_string('InputCalibration', 'Edit_InputCalibration6'))
        self.Button_InputCalibration_OK = self.get_string('InputCalibration', 'Button_InputCalibration_OK')
        self.Button_InputCalibration_Cancel = self.get_string('InputCalibration', 'Button_InputCalibration_Cancel')

        # [TAB2]
        self.t2_tableCalibration_Column.clear()
        self.t2_tableCalibration_Column.append(self.get_string('TAB2', 't2_tableCalibration_Column1'))
        self.t2_tableCalibration_Column.append(self.get_string('TAB2', 't2_tableCalibration_Column2'))
        self.t2_tableCalibration_Column.append(self.get_string('TAB2', 't2_tableCalibration_Column3'))
        self.t2_tableCalibration_Column.append(self.get_string('TAB2', 't2_tableCalibration_Column4'))
        self.t2_tableCalibration_Column.append(self.get_string('TAB2', 't2_tableCalibration_Column5'))
        self.t2_tableCalibration_Column.append(self.get_string('TAB2', 't2_tableCalibration_Column6'))
        self.t2_groupCalibratonResult  = self.get_string('TAB2', 't2_groupCalibratonResult')
        self.t2_gCR_lbl1 = self.get_string('TAB2', 't2_gCR_lbl1')
        self.t2_gCR_lbl2 = self.get_string('TAB2', 't2_gCR_lbl2')
        self.t2_groupInitialData = self.get_string('TAB2', 't2_groupInitialData')
        self.t2_gID_lbl1 = self.get_string('TAB2', 't2_gID_lbl1')
        self.t2_gID_lbl2 = self.get_string('TAB2', 't2_gID_lbl2')
        self.t2_gID_lbl3 = self.get_string('TAB2', 't2_gID_lbl3')
        self.t2_gID_cmd1_1 = self.get_string('TAB2', 't2_gID_cmd1_1')
        self.t2_gID_cmd1_2 = self.get_string('TAB2', 't2_gID_cmd1_2')
        self.t2_gID_cmd1_3 = self.get_string('TAB2', 't2_gID_cmd1_3')
        self.t2_gID_button1 = self.get_string('TAB2', 't2_gID_button1')
        self.t2_gID_button2 = self.get_string('TAB2', 't2_gID_button2')
        self.t2_gID_button3 = self.get_string('TAB2', 't2_gID_button3')
        self.t2_tableCalibration_popup_Exclude = self.get_string('TAB2', 't2_tableCalibration_popup_Exclude')
        self.t2_tableCalibration_popup_Include = self.get_string('TAB2', 't2_tableCalibration_popup_Include')
        self.t2_tableCalibration_popup_Add = self.get_string('TAB2', 't2_tableCalibration_popup_Add')
        self.t2_tableCalibration_popup_Recount = self.get_string('TAB2', 't2_tableCalibration_popup_Recount')

        # [TAB3]
        self.t3_lblValve1 = self.get_string('TAB3', 't3_lblValve1')
        self.t3_lblValve2 = self.get_string('TAB3', 't3_lblValve2')
        self.t3_lblValve3 = self.get_string('TAB3', 't3_lblValve3')
        self.t3_lblValve4 = self.get_string('TAB3', 't3_lblValve4')
        self.t3_lblValve5 = self.get_string('TAB3', 't3_lblValve5')
        self.t3_lbl_Helium = self.get_string('TAB3', 't3_lbl_Helium')
        self.t3_lbl_Atmosphere = self.get_string('TAB3', 't3_lbl_Atmosphere')
        self.t3_lbl_Vacuum = self.get_string('TAB3', 't3_lbl_Vacuum')
        if config.pressure.value==0:
            self.t3_lblPressure1 = self.get_string('TAB3', 't3_lblPressure1_kPa')
        if config.pressure.value==1:
            self.t3_lblPressure1 = self.get_string('TAB3', 't3_lblPressure1_Bar')
        if config.pressure.value==2:
            self.t3_lblPressure1 = self.get_string('TAB3', 't3_lblPressure1_Psi')

        # [TAB4]
        self.t4_groupInterfaceSettings = self.get_string('TAB4', 't4_groupInterfaceSettings')
        self.t4_gIS_lbl1 = self.get_string('TAB4', 't4_gIS_lbl1')
        self.t4_button_1 = self.get_string('TAB4', 't4_button_1')
        self.t4_button_2 = self.get_string('TAB4', 't4_button_2')
        self.t4_groupMeasurementSettings = self.get_string('TAB4', 't4_groupMeasurementSettings')
        self.t4_gMS_lbl1 = self.get_string('TAB4', 't4_gMS_lbl1')
        self.t4_gMS_lbl2 = self.get_string('TAB4', 't4_gMS_lbl2')
        self.t4_gMS_lbl3 = self.get_string('TAB4', 't4_gMS_lbl3')
        self.t4_gMS_lbl4.clear()
        dumps = json.dumps(self.languages.get('TAB4', 't4_gMS_lbl4'))
        dumpsload = json.loads(dumps)
        self.t4_gMS_lbl4 = dumpsload.split(',')

        # [MeasurementSetting]
        self.pressure_setting.clear()
        self.pressure_setting.append(self.get_string('MeasurementSetting', 'pressure_kPa'))
        self.pressure_setting.append(self.get_string('MeasurementSetting', 'pressure_Bar'))
        self.pressure_setting.append(self.get_string('MeasurementSetting', 'pressure_Psi'))

        # [Menu]
        self.menu1 = self.get_string('Menu', 'menu1')
        self.menu1_command1 = self.get_string('Menu', 'menu1_command1')
        self.menu2 = self.get_string('Menu', 'menu2')
        self.menu3 = self.get_string('Menu', 'menu3')
        self.menu4 = self.get_string('Menu', 'menu4')

        # [Message]
        self.message_headline1 = self.get_string('Message', 'message_headline1')
        self.message_txt1 = self.get_string('Message', 'message_txt1')
        self.message_txt2 = self.get_string('Message', 'message_txt2')
        self.message_txt3 = self.get_string('Message', 'message_txt3')


