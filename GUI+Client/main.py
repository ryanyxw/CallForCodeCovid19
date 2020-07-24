from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.properties import ObjectProperty
from kivy.storage.jsonstore import JsonStore
from kivy.utils import platform
from kivy.logger import Logger
from kivy.logger import LoggerHistory
from kivy.clock import Clock
import kivy.config
#Changes the window size
from kivy.core.window import Window
import kivy.metrics
Window.size = (kivy.metrics.mm(72.3), kivy.metrics.mm(157.8)) #Height, Width
#MAC
import subprocess
import os
from pathlib import Path
import datetime
import sys
#Regular Expressions
import re
#Client
import client
#network interfaces
import netifaces
#Logging
import logging
import logging.handlers
#WHen return from server, remember type
#os.platform used to identify the os
#Client secret key
#Guiunicorn
#Using a for loop to continue requests if the request failed
#Status bar change color if there is an error
this = sys.modules[__name__]
if platform != 'android':
    if os.path.isdir(Path.home()):
        this.appPath = str(Path.home()) + os.sep + '/.CovidContactTracer'
        if not os.path.isdir(this.appPath):
            os.mkdir(this.appPath)
    else:
        raise OSError
else:
    this.appPath = os.path.dirname(__file__)

this.logVerbosity = 50
this.storeName = 'local'

kivy.config.log_dir = this.appPath
if this.logVerbosity < 10:
    kivy.config.log_level = "trace"
elif this.logVerbosity < 20:
    kivy.config.log_level = "debug"
elif this.logVerbosity < 30:
    kivy.config.log_level = "info"
elif this.logVerbosity < 40:
    kivy.config.log_level = "warn"
elif this.logVerbosity < 50:
    kivy.config.log_level = "error"
elif this.logVerbosity == 50:
    kivy.log_level = "critical"
else:
    kivy.config.log_level = "trace"
kivy.config.log_name = "MainGUI_%y-%m-%d_%_.txt"
kivy.config.log_maxfiles = 49

#Manages all permanent storage and adding into the JSON file
this.store = JsonStore(this.appPath + os.sep + this.storeName + '.json')

class storageUnit():

    def __init__(self):
        Logger.info('creating an instance of storageUnit')

#Adds a unknown / new mac address that was not on the previous network into the json file
    def addEntry(self, macAddress, time):
        if macAddress in this.store.get("macDict")["value"]:
            #this.store.get("macDict")["value"][macAddress] += [time]#HEREEEee
            this.store.get("macDict")["value"][macAddress] += ["TEST"]#HEREEE
            this.store.get("recentTen")["value"] = [[time, macAddress]] + this.store.get("recentTen")["value"][:9]
            Logger.info('addEntry updated ' + macAddress + ' met at '+time)
        else:
            this.store.get("numEntries")["value"] += 1
            this.store.get("macDict")["value"][macAddress] = [time]
            this.store.get("recentTen")["value"] = [[time, macAddress]] + this.store.get("recentTen")["value"][:9]
            Logger.info('addEntry added ' + macAddress + ' met at '+time)
#Checks if the previous prevNetwork is the same as foreignSet, which is a set
    def isSamePrevNetwork(self, foreignSet):
        returnArr = []
        for i in foreignSet:
            if i not in this.store.get("prevNetwork")["value"]:
                returnArr += [i]
        Logger.info('isSamePrevNetwork filtered ' + repr(foreignSet) + ' into ' + repr(returnArr))
        return returnArr

#This entire class is meant for macAddress collection
class GetMacAdd():
    def __init__(self, **kwargs):
        #super(HomePage, self).__init__(**kwargs)
        self.storage = storageUnit()

        self.supported = None  #  Documents whether our mac address collection method is supported


        Logger.info('creating an instance of GetMacAdd')


    def pressed(self, instance):
        macList = self.getMac()
        self.label3.text = "SelfMac : " + macList
        Logger.info('Button pressed')

    def getString(self, recentTen):
        returnStr = ""
        for i in recentTen:
            returnStr += repr(i)+ "\n"
        Logger.info('getString returned ' + repr(returnStr) + ' from input ' + repr(recentTen))
        return returnStr

    def getMacSelf(self):
        selfMac = []
        isContractionStart = re.compile(r'^([\da-fA-F]):')
        isContractionMid = re.compile(r':([\da-fA-F]):')
        isContractionEnd = re.compile(r':([\da-fA-F])$')
        for interface in netifaces.interfaces():
            Logger.info('getMacSelf checking interface ' + interface)
            try:
                mac = netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']
                Logger.info('getMacSelf:' + interface + ' has MAC addr ' + mac)
                if re.search(isContractionStart,mac) is not None:
                    digit = re.search(isContractionStart,mac).group(1)
                    mac = re.sub(isContractionStart,digit + "0:",mac)
                if re.search(isContractionEnd,mac) is not None:
                    digit = re.search(isContractionEnd,mac).group(1)
                    mac = re.sub(isContractionEnd,":" + digit + "0",mac)
                while re.search(isContractionMid,mac) is not None:
                    digit = re.search(isContractionMid,mac).group(1)
                    mac = re.sub(isContractionMid,":" + digit + "0:",mac)
                if mac != "00:00:00:00:00:00":
                    selfMac.append(mac)
                    Logger.info('getMacSelf:' + mac + ' has been appended to output of function')
            except KeyError:
                pass
            except ValueError:
                pass

        if selfMac == []:
            raise OSError
        else:
            Logger.info('getMacSelf returned ' + str(selfMac))
            return selfMac

    def tryGetMac(self):

        fails = 0
        if os.path.isfile(os.sep+"proc"+os.sep+"net"+os.sep+"arp"):
            if os.access(os.sep+"proc"+os.sep+"net"+os.sep+"arp", os.R_OK):
                f=open(os.sep+"proc"+os.sep+"net"+os.sep+"arp", "r")
                result = f.read()
                self.supported = True  #  Documents whether our mac address collection method is supported
                Logger.debug('tryGetMac: read proc/net/arp successfully and got ' + result)
                return result
            else:
                fails = fails + 1
        else:
            fails = fails + 1
        try:
            result = subprocess.run(['arp', '-a'], stdout=subprocess.PIPE)
            self.supported = True #  Documents whether our mac address collection method is supported
            Logger.debug('tryGetMac: executed arp -a successfully and got ' + str(result))
            return result
        except subprocess.CalledProcessError:
            fails = fails + 1
            pass
        self.supported = False #  Documents whether our mac address collection method is supported
        Logger.debug('tryGetMac: all MAC address scanning methods failed')
        return ""

    def getMac(self):
        macInitStr = self.tryGetMac()
        macInitStr = repr(macInitStr)
        Logger.debug('getMac: recieved ' + macInitStr)
        isMacAddr = re.compile(r"([\da-fA-F]{1,2}:[\da-fA-F]{1,2}:[\da-fA-F]{1,2}:[\da-fA-F]{1,2}:[\da-fA-F]{1,2}:[\da-fA-F]{1,2})")
        shortMacList = re.findall(isMacAddr,macInitStr)
        isContractionStart = re.compile(r'^([\da-fA-F]):')
        isContractionMid = re.compile(r':([\da-fA-F]):')
        isContractionEnd = re.compile(r':([\da-fA-F])$')
        macList = []
        for mac in shortMacList:
            if re.search(isContractionStart,mac) is not None:
                digit = re.search(isContractionStart,mac).group(1)
                mac = re.sub(isContractionStart,digit + "0:",mac)
            if re.search(isContractionEnd,mac) is not None:
                digit = re.search(isContractionEnd,mac).group(1)
                mac = re.sub(isContractionEnd,":" + digit + "0",mac)
            while re.search(isContractionMid,mac) is not None:
                digit = re.search(isContractionMid,mac).group(1)
                mac = re.sub(isContractionMid,":" + digit + "0:",mac)
            macList.append(mac)

        Logger.debug('getMac: filtered into ' + repr(macList))
        compareSet = set(macList)
        diffArr = self.storage.isSamePrevNetwork(compareSet)
        if len(diffArr) == 0:
            Logger.debug('getMac: No new MAC Addr found')
            return self.getString(this.store.get("recentTen")["value"])
        else:
            for macAdd in diffArr:
                self.storage.addEntry(macAdd, str(datetime.datetime.now()))
            this.store.put("prevNetwork", value = dict.fromkeys(compareSet, 0))
            return self.getString(this.store.get("recentTen")["value"])


#Class for the homepage screen
class HomePage(Screen, Widget):
    def __init__(self, **kwargs):
        super(HomePage, self).__init__(**kwargs)

        #DELETE IN THE END ONLYU USED TO DEBUG
        self.store = this.store
        self.macClass = GetMacAdd()
        self.selfMacAddress = str(self.macClass.getMacSelf()[0])
        Logger.info('creating an instance of HomePage')
#Determines if the server initiation is correct (should only be a one time thing)
        isSuccessful = True

        if not os.path.isfile(this.appPath + os.sep + "client.log"):
            f = open(this.appPath + os.sep + "client.log", "w")
            f.close()
        client.init(this.appPath + os.sep + "client.log", this.logVerbosity)
        #self.macClass = GetMacAdd()
#Checks if there is a file. If there is not, initiate all 4 necessary parts
        self.statusLabel = ObjectProperty(None)
        print("isExist before = " + repr(this.store.exists('numEntries')))
        if (not this.store.exists('numEntries')):
            #this.store.put("selfMac", value = self.macClass.getMacSelf()[0])
            Logger.info('Self Mac Address set to ' + self.macClass.getMacSelf()[0])
            this.store.put("selfMac", value = self.macClass.getMacSelf()[0])
            tempSecret = client.initSelf(this.store.get("selfMac")["value"])
            if type(tempSecret) == str:
                if (len(tempSecret) == 56):
                    Logger.info('Secret Key set to ' + tempSecret)
                    this.store.put("secretKey", value = tempSecret)
                    this.store.put("numEntries", value = 0)
                    this.store.put("macDict", value = dict())
                    this.store.put("recentTen", value = list())
                    this.store.put("prevNetwork", value = dict())
#                self.statusLabel.text = "Status: Account Registered"
                    this.store.put("homeLabel", value = "Status: Account Registered")
                    this.store.put("quitAppLabel", value = "Status: Click to delete all data")
                    this.store.put("sendDataLabel", value = "Status: Click to report infected")
            elif (tempSecret == 2):
                this.store.put("homeLabel", value = "Status: Server Error, Please quit the app and try again (2)")
                isSuccessful = False
            elif (tempSecret == 3):
                this.store.put("homeLabel", value = "Status: User already initiated (3)")
                isSuccessful = False
            elif (tempSecret == 4):
                this.store.put("homeLabel", value = "Status: Invalid Mac Address, Please quit the app and try again (4)")
                isSuccessful = False
            else:
                this.store.put("homeLabel", value = "Status: Unknown error occurred. Please restart the app. If this persists, please contact developers. ")
                isSuccessful = False

        if (isSuccessful):
            self.options = ObjectProperty(None)
#macClass variable is just used as a reference to be able to call the getMac class
            self.macClass = GetMacAdd()
            self.selfMacAddress = str(self.macClass.getMacSelf()[0]) #Assumes the first mac address is self mac address
            self.actualMac = self.macClass.getMac()
            
            #The line of code that calls the function runTimeFunction every 0.5 seconds
            Clock.schedule_interval(self.runTimeFunction, 0.5)
            
    def runTimeFunction(self, deltaT):
        print("hello")

    def coronaCatcherButtonClicked(self):
        Logger.info('coronaCatcherButtonClicked ')
        returnVal = client.queryMyMacAddr(this.store.get("selfMac")["value"], this.store.get("secretKey")["value"])
        if (returnVal == -1):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", you have contacted someone with the virus. Please quarantine"
            this.store.put("homeLabel", value = "Checked by " + str(datetime.datetime.now()) + ", you have contacted someone with the virus. Please quarantine")
        elif (returnVal == 0):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", you are still safe!"
            this.store.put("homeLabel", value = "Checked by " + str(datetime.datetime.now()) + ", you are still safe!")
        elif (returnVal == 2):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Server Error, please quit the app and retry (2)"
            this.store.put("homeLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Server Error, please quit the app and retry (2)")
        elif (returnVal == 3):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Incorrect secret key, you're kinda screwed (3)"
            this.store.put("homeLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Incorrect secret key, you're kinda screwed (3)")
        elif (returnVal == 4):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Invalid mac address, you're kinda screwed (4)"
            this.store.put("homeLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Invalid mac address, you're kinda screwed (4)")
        elif (returnVal == 5):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Server Overload. Please do not click button twice"
            this.store.put("homeLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Server Overload. Please do not click button twice")
            print("TRUEEE")
        else:
            self.statusLabel.text = "1 returned"
            this.store.put("homeLabel", value = "Checked by " + str(datetime.datetime.now()) + ", 1 returned")


#This method is used when we click the button to check our current network mac
    def calculateMac(self):
        self.actualMac = self.macClass.getMac()
        self.coronaCatcherButtonClicked()
        Logger.info('Calculated MAC Addr to be ' + self.actualMac)
        return self.actualMac

    #This calculates the offset accordingly (topLeftH and topLeftW are both in terms of proportions)
    def findCoordinates(self, percentage, topLeftWidth, topLeftHeight):
        smallDim = min(Window.size)
        offSet = smallDim * percentage
        xCoor = topLeftWidth * Window.size[1] + offSet#Windows: (Height, Width)
        yCoor = topLeftHeight * Window.size[0] - self.options.size[0] - offSet
        Logger.info('findCoordinates returned X:' + repr(xCoor / Window.size[1]) + ' and Y:'+repr(yCoor / Window.size[0]))
        return (xCoor / Window.size[1], yCoor / Window.size[0])

    pass

#SideBar class page (reference my.kv file)
class SideBarPage(Screen):
    pass

#AboutUs class page (reference my.kv file)
class AboutUsPage(Screen):
    pass

#QuitApp class page (reference my.kv file)
class QuitAppPage(Screen):
    def __init__(self, **kwargs):
        Logger.info('creating an instance of QuitAppPage')
        self.store = this.store
        super(QuitAppPage, self).__init__(**kwargs)

        self.statusLabel = ObjectProperty(None)


    def deleteDataAndQuitButtonClicked(self):
        Logger.info('Delete data and quit clicked')
        returnValue = client.forgetUser(this.store.get("selfMac")["value"], this.store.get("secretKey")["value"])
        if (returnValue == 0):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Sucess! You may quit the app"
            this.store.put("quitAppLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Sucess! You may quit the app")
        elif (returnValue == 2):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Server Error (2)"
            this.store.put("quitAppLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Server Error (2)")
        elif (returnValue == 3):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", incorrect secret key (3)"
            this.store.put("quitAppLabel", value = "Checked by " + str(datetime.datetime.now()) + ", incorrect secret key (3)")
        elif (returnValue == 4):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", invalid mac addr of self (4)"
            this.store.put("quitAppLabel", value = "Checked by " + str(datetime.datetime.now()) + ", invalid mac addr of self (4)")
        elif (returnValue == 1):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", 1 is returned (1)"
            this.store.put("quitAppLabel", value = "Checked by " + str(datetime.datetime.now()) + ", 1 is returned (1)")
        else:
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", server returned unknown command : " + str(returnValue)
            this.store.put("quitAppLabel", value = "Checked by " + str(datetime.datetime.now()) + ", server returned unknown command : " + str(returnValue))

    pass

#SendData class page (reference my.kv file)
class SendDataPage(Screen):
    def __init__(self, **kwargs):
        self.store = this.store
        super(SendDataPage, self).__init__(**kwargs)
        Logger.info('creating an instance of SendDataPage')

        self.statusLabel = ObjectProperty(None)
    def getCSVString(self):
        returnStr = this.store.get("selfMac")["value"] + ","
        macDictionary = this.store.get("macDict")["value"]
        for key in macDictionary:
            returnStr += key + ","
        return returnStr

    def imInfectedButtonClicked(self):
        Logger.info('imInfected button clicked')

        returnVal = client.positiveReport(this.store.get("selfMac")["value"], this.store.get("secretKey")["value"], self.getCSVString())
        if (returnVal == 2):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Retry is needed(server error). Restart app and try again (2)"
            this.store.put("sendDataLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Retry is needed(server error). Restart app and try again (2)")
        elif (returnVal == 3):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Incorrect Secret Key. Restart app and try again (3)"
            this.store.put("sendDataLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Incorrect Secret Key. Restart app and try again (3)")
        elif (returnVal == 4):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Invalid CSV. Restart app and contact admin"
            this.store.put("sendDataLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Invalid CSV. Restart app and contact admin")
        else:
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Request sucess! Get well soon!"
            this.store.put("sendDataLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Request sucess! Get well soon!")

    def iJustRecoveredButtonClicked(self):
        Logger.info('iJustRecovered button clicked')

        returnVal = client.negativeReport(this.store.get("selfMac")["value"], this.store.get("secretKey")["value"])
        if (returnVal == 2):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Retry is needed(server error). Restart app and try again (2)"
            this.store.put("sendDataLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Retry is needed(server error). Restart app and try again (2)")
        elif (returnVal == 3):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Incorrect Secret Key. Restart app and try again (3)"
            this.store.put("sendDataLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Incorrect Secret Key. Restart app and try again (3)")
        elif (returnVal == 4):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Invalid MAC Address of self. Restart app and contact admin (4)"
            this.store.put("sendDataLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Invalid MAC Address of self. Restart app and contact admin (4)")
        else:
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Request sucess! Good job recovering! "
            this.store.put("sendDataLabel", value = "Checked by " + str(datetime.datetime.now()) + ", Request sucess! Good job recovering! ")

    pass

#SeeDataPage class page (reference my.kv file)
class SeeDataPage(Screen):
    def __init__(self, **kwargs):
        super(SeeDataPage, self).__init__(**kwargs)
        Logger.info('creating an instance of SeeDataPage')
        self.store = this.store
#Used for future reference and changing the data in the table
        self.data = [0] * 20
#Stores the recentTen aspect of the json file
        self.recentTen = this.store.get("recentTen")["value"]
#Creates the grid used to display the information
        self.table = GridLayout()
        self.table.cols = 2

        Logger.info("BEFORE ASSIGN VALUES")
#Initiates the table by first creating a label into the self.data array, and
#then adding them to the grid
        for i in range(len(self.recentTen)):
            self.data[2 * i] = Label(text = self.recentTen[i][1])
            self.data[2 * i + 1] = Label(text = self.recentTen[i][0])
            self.table.add_widget(self.data[2 * i])
            self.table.add_widget(self.data[2 * i + 1])
        self.add_widget(self.table)

#This method changes the self.data so that it reflects the new recentTen
    def renewRecentTen(self):
        Logger.info('Renew Recent Ten button clicked')
        self.recentTen = this.store.get("recentTen")["value"]
        for i in range(len(self.recentTen)):
            self.data[2 * i].text = self.recentTen[i][1]
            self.data[2 * i + 1].text = self.recentTen[i][0]
    pass

#Represent the transitions between the windows above
class WindowManager(ScreenManager):
    pass

kv = Builder.load_file("my.kv")

class MyMainApp(App):
    def build(self):
#        store = JsonStore(this.storeName + '.json')
#        if (not store.exists('numEntries')):
#            store.put("numEntries", value = 0)
#            store.put("macDict", value = dict())
#            store.put("recentTen", value = list())
 #           store.put("prevNetwork", value = dict())
        return kv


if __name__ == "__main__":
    try:
        Logger.info('App Started')
        MyMainApp().run()
        Logger.info('App Exiting')
        client.freeResources()
        f = open(this.appPath + os.sep + "main.log", "a")
        for log in LoggerHistory.history:
            f.write(repr(log) +'\n')
        f.close()
        exit()
    except KeyboardInterrupt:
        Logger.critical('App Exiting')
        f = open(this.appPath + os.sep + "main.log", "a")
        for log in LoggerHistory.history:
            f.write(repr(log) +'\n')
        f.close()
        client.freeResources()
        exit()
    except Exception as e:
        Logger.critical("Exception occurred", exc_info=True)
