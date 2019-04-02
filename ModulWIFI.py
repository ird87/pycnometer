# -*- coding: utf-8 -*-

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
    myssid = 'Cell(ssid={0})'.format(name)   # vivekHome is my wifi name
    # print("myssid: " + myssid)
    for i in range(len(allSSID)):
        # print("{0}: {1}".format(i, str(allSSID[i])))
        if str(allSSID[i]) == myssid:
            a = i
            myssidA = allSSID[a]
            print("myssidA: " + str(myssidA))
            return myssid
        else:
            print("getout")
            return None

def addSSID(ssid, password):
    myssid = Scheme.for_cell('wlan0', 'home', ssid, password)
    try:
        myssid.save()
        return True
    except Exception:
        return False

def deleteSSID(ssid, password):
    myssid = Scheme.for_cell('wlan0', 'home', ssid, password)
    try:
        myssid.delete()
        return True
    except Exception:
        return False



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