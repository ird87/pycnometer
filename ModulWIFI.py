from wifi import Cell, Scheme

class WIFI(object):
    """Конструктор класса. Поля класса"""
    def __init__(self):
        self.wifi_name = "Gleeson55"
        self.wifi_pass = "Brendan19"


    def wifiscan(self):
        allSSID = Cell.all('wlan0')
        allSSID_list = list(allSSID)
        print(allSSID_list)   # prints all available WIFI SSIDs
        myssid= 'Cell(ssid = {0})'.format(self.wifi_name)   # vivekHome is my wifi name
        myssidA = None
        for i in range(len(allSSID_list)):
            if str(allSSID_list[i]) == myssid:
                a = i
                myssidA = allSSID_list[a]
                print("myssidA: " + myssidA)
                break
            else:
                print("getout")

        # Creating Scheme with my SSID.
        myssid = Scheme.for_cell('wlan0', 'home', myssidA, self.wifi_pass)   # vive1234 is the password to my wifi myssidA is the wifi name

        print(myssid)
        myssid.save()
        myssid.activate()



