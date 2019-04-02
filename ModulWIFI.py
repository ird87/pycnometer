# -*- coding: utf-8 -*-
import os
import time

import wifi
from wifi import Cell, Scheme


def Search():
    wifilist = []

    cells = wifi.Cell.all('wlan0')

    for cell in cells:
        wifilist.append(cell)

    return wifilist

def SearchNames():
    wifilist = Search()
    wifi_networks = []
    for wifi_network in wifilist:
        network = str(wifi_network)
        network = network.replace('Cell(ssid=', '')
        network = network[:-1]
        if not network in wifi_networks:
            wifi_networks.append(network)
    return wifi_networks

def SearchSSID(name):
    allSSID = Search()
    print("allSSID: " + str(allSSID))
    myssid = 'Cell(ssid={0})'.format(name)   # vivekHome is my wifi name
    print("myssid: " + myssid)
    for i in range(len(allSSID)):
        print("{0}: {1}".format(i, str(allSSID[i])))
        if str(allSSID[i]) == myssid:
            a = i
            myssidA = allSSID[a]
            print("myssidA: " + str(myssidA))
            return myssidA
        else:
            print("getout")
    return None

def addSSID(ssid, password):
    myssid = Scheme.for_cell('wlan0', 'home', ssid, password)
    try:
        myssid.save()
        return True
    except Exception:
        print("NO addSSID")
        return False

def deleteSSID(ssid, password):
    myssid = Scheme.for_cell('wlan0', 'home', ssid, password)
    try:
        myssid.delete()
        print("deleteSSID addSSID")
        return True
    except Exception:
        return False

def _disconnect_all(_iface):
    """
    Disconnect all wireless networks.
    """
    lines = os.system("wpa_cli -i %s list_networks" % _iface)
    if lines:
        for line in lines[1:-1]:
            os.system("wpa_cli -i %s remove_network %s" % (_iface, line.split()[0]))

def connect_to_network(_iface, _ssid, _type, _pass=None):
    """
    Associate to a wireless network. Support _type options:
    *WPA[2], WEP, OPEN
    """
    _disconnect_all(_iface)
    time.sleep(1)
    if os.system("wpa_cli -i %s add_network" % _iface) == "0\n":
        if os.system('wpa_cli -i %s set_network 0 ssid \'"%s"\'' % (_iface, _ssid)) == "OK\n":
            if _type == "OPEN":
                os.system("wpa_cli -i %s set_network 0 auth_alg OPEN" % _iface)
                os.system("wpa_cli -i %s set_network 0 key_mgmt NONE" % _iface)
            elif _type == "WPA" or _type == "WPA2":
                os.system('wpa_cli -i %s set_network 0 psk "%s"' % (_iface, _pass))
            elif _type == "WEP":
                os.system("wpa_cli -i %s set_network 0 wep_key %s" % (_iface, _pass))
            else:
                print("Unsupported type")

                os.system("wpa_cli -i %s select_network 0" % _iface)


# def FindFromSearchList(ssid):
#     wifilist = Search()
#
#     for cell in wifilist:
#         if cell.ssid == ssid:
#             return cell
#
#     return False
#
#
# def FindFromSavedList(ssid):
#     cell = wifi.Scheme.find('wlan0', ssid)
#
#     if cell:
#         return cell
#
#     return False
#
#
# def Connect(ssid, password=None):
#     cell = FindFromSearchList(ssid)
#
#     if cell:
#         savedcell = FindFromSavedList(cell.ssid)
#
#         # Already Saved from Setting
#         if savedcell:
#             savedcell.activate()
#             return cell
#
#         # First time to conenct
#         else:
#             if cell.encrypted:
#                 if password:
#                     scheme = Add(cell, password)
#
#                     try:
#                         scheme.activate()
#
#                     # Wrong Password
#                     except wifi.exceptions.ConnectionError:
#                         Delete(ssid)
#                         return False
#
#                     return cell
#                 else:
#                     return False
#             else:
#                 scheme = Add(cell)
#
#                 try:
#                     scheme.activate()
#                 except wifi.exceptions.ConnectionError:
#                     Delete(ssid)
#                     return False
#
#                 return cell
#
#     return False
#
#
# def Add(cell, password=None):
#     if not cell:
#         return False
#
#     scheme = wifi.Scheme.for_cell('wlan0', cell.ssid, cell, password)
#     scheme.save()
#     return scheme
#
#
# def Delete(ssid):
#     if not ssid:
#         return False
#
#     cell = FindFromSavedList(ssid)
#
#     if cell:
#         cell.delete()
#         return True
#
#     return False