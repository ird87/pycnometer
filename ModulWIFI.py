from wifi import Cell, Scheme

class WIFI(object):
    """Конструктор класса. Поля класса"""
    def __init__(self):
        self.wifi_name = ""
        self.wifi_pass = ""


    def wifiscan(self):
       allSSID = Cell.all('wlan0')
       print(allSSID)   # prints all available WIFI SSIDs
       myssid= 'Cell(ssid = vivekHome)'   # vivekHome is my wifi name
       myssidA = None
       for i in range(len(list(allSSID))):
            if str(allSSID[i]) == myssid:
                    a = i
                    myssidA = allSSID[a]
                    print(myssidA)
                    break
            else:
                    print("getout")

       # Creating Scheme with my SSID.
       myssid= Scheme.for_cell('wlan0', 'home', myssidA, 'vivek1234')   # vive1234 is the password to my wifi myssidA is the wifi name

       print(myssid)
       myssid.save()
       myssid.activate()



