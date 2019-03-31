import time

import wifi
from wifi import Cell, Scheme

class WIFI(object):
    """Конструктор класса. Поля класса"""
    def __init__(self):
        self.wifi_name = ""
        self.wifi_pass = ""
        self.myssid = None
        self.myssidA = None
        self.connect = False

    def set_wifi(self, name, password):
        self.wifi_name = name
        self.wifi_pass = password

    def wifiscan(self):
        allSSID = Cell.all('wlan0')
        allSSID_list = list(allSSID)
        print(allSSID_list)   # prints all available WIFI SSIDs
        myssid= 'Cell(ssid={0})'.format(self.wifi_name)   # vivekHome is my wifi name
        # print("myssid: " + myssid)
        for i in range(len(allSSID_list)):
            print("{0}: {1}".format(i, str(allSSID_list[i])))
            if str(allSSID_list[i]) == myssid:
                a = i
                self.myssidA = allSSID_list[a]
                print("myssidA: " + str(self.myssidA))
                return True
            else:
                print("getout")
                return False

    def wifi_connect(self):
        self.myssid = Scheme.for_cell('wlan0', 'home', self.myssidA, self.wifi_pass)
        try:
            self.myssid.save()
        except Exception:
            pass
        try:
            self.myssid.activate()
            # Wrong Password
        except Exception:
            self.myssid.delete()
            print("JOPA")
            return False
        self.connect = True

    def wifi_disconnect(self):
        self.myssid = Scheme.for_cell('wlan0', 'home', self.myssidA, "disconnect")
        try:
            self.myssid.save()
        except Exception:
            pass
        try:
            self.myssid.activate()
            # Wrong Password
        except Exception:
            self.myssid.delete()
            print("JOPA")
            return False
        self.connect = False


