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
#Using a for loop to continue requests if the request failed
#Status bar change color if there is an error


#Make sure to make selfMac a csv string of mac addressses
this = sys.modules[__name__]
if platform != 'android':
    if os.path.isdir(Path.home()):
        this.appPath = str(Path.home()) + os.sep + '.CovidContactTracer'
        if not os.path.isdir(this.appPath):
            os.mkdir(this.appPath)
    else:
        raise OSError
else:
    this.appPath = os.path.dirname(__file__)
this.versionNumber = '1.0.0'
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
            tempNewMacDict = this.store.get("macDict")["value"]
            tempNewMacDict[macAddress] = time
            this.store.put("macDict", value = tempNewMacDict)
            tempNewMacDict = 0

            tempNewRecentTen = this.store.get("recentTen")["value"]
            tempNewRecentTen = [[time, macAddress]] + tempNewRecentTen[:9]
            this.store.put("recentTen", value = tempNewRecentTen)
            tempNewRecentTen = 0
            Logger.info('addEntry updated ' + macAddress + ' met at '+time)
        else:
            tempNewNumEntries = this.store.get("numEntries")["value"]
            tempNewNumEntries += 1
            this.store.put("numEntries", value = tempNewNumEntries)
            tempNewNumEntries = 0

            tempNewMacDict = this.store.get("macDict")["value"]
            tempNewMacDict[macAddress] = time
            this.store.put("macDict", value = tempNewMacDict)
            tempNewMacDict = 0

            tempNewRecentTen = this.store.get("recentTen")["value"]
            tempNewRecentTen = [[time, macAddress]] + tempNewRecentTen[:9]
            this.store.put("recentTen", value = tempNewRecentTen)
            tempNewRecentTen = 0

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


    def getString(self, recentTen):
        returnStr = ""
        for i in recentTen:
            returnStr += repr(i)+ "\n"
        Logger.info('getString returned ' + repr(returnStr) + ' from input ' + repr(recentTen))
        return returnStr

#Gets my own self mac address
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

#Attempts to arp the mac address. If not, logger records a critical message
    def tryGetMac(self):
        Logger.debug("We have entered tryGetMac")
        fails = 0
        if os.path.isfile(os.sep+"proc"+os.sep+"net"+os.sep+"arp"):
            if os.access(os.sep+"proc"+os.sep+"net"+os.sep+"arp", os.R_OK):
                f=open(os.sep+"proc"+os.sep+"net"+os.sep+"arp", "r")
                result = f.read()
                self.supported = True  #  Documents whether our mac address collection method is supported
                Logger.info('tryGetMac: read proc/net/arp successfully and got ' + result)
                return result
            else:
                Logger.warning("read /proc/net/arp failed")
                fails = fails + 1
        else:
            fails = fails + 1
            Logger.warning("read /proc/net/arp failed")
        try:
            result = subprocess.run(['arp', '-a'], stdout=subprocess.PIPE)
            self.supported = True #  Documents whether our mac address collection method is supported
            Logger.info('tryGetMac: executed arp -a successfully and got ' + repr(result))
            return result
        except subprocess.CalledProcessError:
            fails = fails + 1
            Logger.warning("arp -a failed")
            pass
        self.supported = False #  Documents whether our mac address collection method is supported
        Logger.critical('tryGetMac: all MAC address scanning methods failed')
        return ""

#Gets the mac address. Returns the previous (current) network mac address
    def getMac(self):
        macInitStr = self.tryGetMac()
        Logger.debug("We have entered getMac")
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

#macList is the list of mac addresses that was returned by the arp-a
        compareSet = set(macList)
        diffArr = self.storage.isSamePrevNetwork(compareSet)
        if len(diffArr) == 0:
            Logger.debug('getMac: No new MAC Addr found')
            return self.getString(this.store.get("prevNetwork")["value"])
        else:
#Appends on a new mac address if it does not exist
            for macAdd in diffArr:
                self.storage.addEntry(macAdd, datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S'))
            this.store.put("prevNetwork", value = dict.fromkeys(compareSet, 0))
            return self.getString(this.store.get("prevNetwork")["value"])

#A method used for testing. Same as getMac, but adds on a new mac to test
    def testGetMac(self):
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
        macList += ["44:44:44:44:44:44"]
        compareSet = set(macList)
        diffArr = self.storage.isSamePrevNetwork(compareSet)
        if len(diffArr) == 0:
            Logger.debug('getMac: No new MAC Addr found')
            return self.getString(this.store.get("recentTen")["value"])
        else:
            for macAdd in diffArr:
                print("TRUE == " + repr(macAdd))
                self.storage.addEntry(macAdd, datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S'))
            this.store.put("prevNetwork", value = dict.fromkeys(compareSet, 0))
            return self.getString(this.store.get("recentTen")["value"])


#Class for the homepage screen
class HomePage(Screen, Widget):
    def __init__(self, **kwargs):
        super(HomePage, self).__init__(**kwargs)

        #Store for all the permanent storage
        self.store = this.store
        #variable used to reference the getMac class
        self.macClass = GetMacAdd()
        #Variable used to record your own personal macAddress
        self.selfMacAddress = self.macClass.getMacSelf()[0]
        Logger.info('creating an instance of HomePage')
#Determines if the server initiation is correct (should only be a one time thing)
        isSuccessful = True

        if not os.path.isfile(this.appPath + os.sep + "client.log"):
            f = open(this.appPath + os.sep + "client.log", "w")
            f.close()
        client.init(this.appPath + os.sep + "client.log", this.logVerbosity)
        #self.macClass = GetMacAdd()
#Checks if there is a file. If there is not, initiate all 4 necessary parts

        #Variable that stores what the status is for the user. This is just initialization
        self.statusLabel = ObjectProperty(None)
        #Variable that stores what the mac addresses are printed on. This is just initialization
        self.macDisplay = ObjectProperty(None)
        print("isExist before = " + repr(this.store.exists('numEntries')))
#If this is a new user
        if (not this.store.exists('numEntries')):
            #First initiates everything within the json file
            this.store.put("numEntries", value = 0)
            this.store.put("macDict", value = dict())
            this.store.put("recentTen", value = list())
            this.store.put("prevNetwork", value = dict())
#                self.statusLabel.text = "Status: Account Registered"
            this.store.put("homeLabel", value = "Status: Account Registered")
            this.store.put("quitAppLabel", value = "Status: Click to delete all data")
            this.store.put("sendDataLabel", value = "Status: Click to report infected")
            #Sets the secretCode to be empty screen
            Logger.info('Secret Key set to ' + 'empty string')
            this.store.put("secretKey", value = '')
            #this.store.put("selfMac", value = self.macClass.getMacSelf()[0])
            Logger.info('Self Mac Address set to ' + self.macClass.getMacSelf()[0])
            #Stores the personal mac address in the JSOn file
            this.store.put("selfMac", value = self.macClass.getMacSelf()[0])
            #Stores the returned secret key in tempSecret
            tempSecret = client.initSelf(this.store.get("selfMac")["value"])
            if type(tempSecret) == str:
                if (len(tempSecret) == 56):
                    #All initialization
                    Logger.info('Secret Key set to ' + tempSecret)
                    this.store.put("secretKey", value = tempSecret)
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
#macClass variable is just used as a reference to be able to call the getMac class
            #Stores self mac address in selfMacAddress
            self.selfMacAddress = self.store.get("selfMac")["value"] #Assumes the first mac address is self mac address
            #Stores the actual mac addresses that we get from getMac into actualMac. This is used to display the network mac addresses the first time users
            #Open the app
            self.actualMac = self.macClass.getMac()
            #self.actualmac = self.calculateMac()
            cutoff = datetime.datetime.now() - datetime.timedelta(days=14)
            macDict = this.store.get("macDict")["value"]
            for mac in macDict.keys():
                strTime = macDict[mac]
                dateSeen = datetime.datetime.strptime(strTime, '%Y-%m-%d_%H:%M:%S')
                if dateSeen < cutoff:
                    del macDict[mac]
            this.store.put("macDict", value = macDict)
            del macDict
        else:
            #This should at least guarantee the gui to run but set everything to empty.
            self.selfMacAddress = ""
            self.actualMac = ""

    #The line of code that calls the function runTimeFunction every 0.5 seconds
        Clock.schedule_interval(self.runTimeFunction, 10)

    def runTimeFunction(self, deltaT):
        pass


    def coronaCatcherButtonClicked(self):
        Logger.info('coronaCatcherButtonClicked ')
        if "LastQueryTime" in this.store:
            lastAccess = this.store.get("LastQueryTime")['value']
            lastAccess = datetime.datetime.strptime(lastAccess, '%Y-%m-%d_%H:%M:%S.%f')
        else:
            lastAccess = datetime.datetime.fromisoformat('2011-11-04 00:05:23.283')
        allowedTime = lastAccess + datetime.timedelta(hours=8)
        currentTime = datetime.datetime.now()
        if allowedTime < currentTime:
            returnVal = client.queryMyMacAddr(this.store.get("selfMac")["value"], this.store.get("secretKey")["value"])
            now = datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S.%f')
            this.store.put("LastQueryTime", value = now)
            if (returnVal == -1):
                self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nyou have contacted someone with the virus. Please quarantine"
                this.store.put("homeLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nyou have contacted someone with the virus. Please quarantine")
            elif (returnVal == 0):
                self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nyou are still safe!"
                this.store.put("homeLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nyou are still safe!")
            elif (returnVal == 2):
                self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nServer Error, please quit the app and retry (2)"
                this.store.put("homeLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nServer Error, please quit the app and retry (2)")
            elif (returnVal == 3):
                self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nIncorrect secret key, you're kinda screwed (3)"
                this.store.put("homeLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nIncorrect secret key, you're kinda screwed (3)")
            elif (returnVal == 4):
                self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nInvalid mac address, you're kinda screwed (4)"
                this.store.put("homeLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nInvalid mac address, you're kinda screwed (4)")
            elif (returnVal == 5):
                self.statusLabel.text = "Please only check once every 8 hours."
                this.store.put("homeLabel", value = "Please only check once every 8 hours.")
            else:
                self.statusLabel.text = "1 returned"
                this.store.put("homeLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \n1 returned")
        else:
            self.statusLabel.text = "Please only check once every 8 hours. Feel free \nto return at " + str(allowedTime)
            this.store.put("homeLabel", value = "Please only check once every 8 hours. Feel free \nto return at " + str(allowedTime))

    #This test function is used to mimic adding a new mac to the batch
    def testFunction(self): #Delete kivy line 75 - 79
        #actualMac is the variable that stores the current network after arp-a again
        self.actualMac = self.macClass.testGetMac()
        #This changes the displayed text into the current network by formatting it with the getString method in the macClass
        self.macDisplay.text = self.macClass.getString(self.store.get("prevNetwork")["value"])
        return self.actualMac

#This method is used when we click the button to check our current network mac and confirm with the server
    def calculateMac(self):
        #actualMac is the variable that stores the current network after arp-a again
        self.actualMac = self.macClass.getMac()
        #This line checks with the server to see if user has already contacted infected individual
        self.coronaCatcherButtonClicked()
        Logger.info('Calculated MAC Addr to be ' + self.actualMac)
        Logger.info(self.macClass.getString(self.store.get("prevNetwork")["value"]))
        #This changes the displayed text into the current network by formatting it with the getString method in the macClass
        self.macDisplay.text = self.macClass.getString(self.store.get("prevNetwork")["value"])
        return self.actualMac


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
            os.remove(this.appPath + os.sep + this.storeName + '.json')
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nSucess! You may quit the app"
            this.store.put("quitAppLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nSucess! You may quit the app")
        elif (returnValue == 2):
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nServer Error (2)"
            this.store.put("quitAppLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nServer Error (2)")
        elif (returnValue == 3):
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nincorrect secret key (3)"
            this.store.put("quitAppLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nincorrect secret key (3)")
        elif (returnValue == 4):
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \ninvalid mac addr of self (4)"
            this.store.put("quitAppLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \ninvalid mac addr of self (4)")
        elif (returnValue == 1):
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \n1 is returned (1)"
            this.store.put("quitAppLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \n1 is returned (1)")
        else:
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nserver returned unknown command : " + str(returnValue)
            this.store.put("quitAppLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nserver returned unknown command : " + str(returnValue))

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
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nRetry is needed(server error). Restart app and try again (2)"
            this.store.put("sendDataLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nRetry is needed(server error). Restart app and try again (2)")
        elif (returnVal == 3):
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nIncorrect Secret Key. Restart app and try again (3)"
            this.store.put("sendDataLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nIncorrect Secret Key. Restart app and try again (3)")
        elif (returnVal == 4):
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nInvalid CSV. Restart app and contact admin"
            this.store.put("sendDataLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nInvalid CSV. Restart app and contact admin")
        else:
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nRequest sucess! Get well soon!"
            this.store.put("sendDataLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nRequest sucess! Get well soon!")

    def iJustRecoveredButtonClicked(self):
        Logger.info('iJustRecovered button clicked')

        returnVal = client.negativeReport(this.store.get("selfMac")["value"], this.store.get("secretKey")["value"])
        if (returnVal == 2):
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nRetry is needed(server error). Restart app and try again (2)"
            this.store.put("sendDataLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nRetry is needed(server error). Restart app and try again (2)")
        elif (returnVal == 3):
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nIncorrect Secret Key. Restart app and try again (3)"
            this.store.put("sendDataLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nIncorrect Secret Key. Restart app and try again (3)")
        elif (returnVal == 4):
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nInvalid MAC Address of self. Restart app and contact admin (4)"
            this.store.put("sendDataLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nInvalid MAC Address of self. Restart app and contact admin (4)")
        else:
            self.statusLabel.text = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nRequest sucess! Good job recovering! "
            this.store.put("sendDataLabel", value = "Checked by " + datetime.datetime.now().strftime('%Y-%m-%d_%H:%M:%S') + ", \nRequest sucess! Good job recovering! ")

    pass

#SeeDataPage class page (reference my.kv file)
class SeeDataPage(Screen):
    def __init__(self, **kwargs):
        super(SeeDataPage, self).__init__(**kwargs)
        Logger.info('creating an instance of SeeDataPage')
        self.store = this.store

#Stores the recentTen aspect of the json file, used for the first initiation of the user
        self.recentTen = this.store.get("recentTen")["value"]

        #This variable references the label within the page (used for potentially changing the top10 by renewing)
        self.displayTen = ObjectProperty(None)


        Logger.info("BEFORE ASSIGN VALUES")


#This method changes the self.data so that it reflects the new recentTen
    def renewRecentTen(self):
        Logger.info('Renew Recent Ten button clicked')
        self.recentTen = this.store.get("recentTen")["value"]
        self.displayTen.text = self.convertRecentTenToStr()


    def convertRecentTenToStr(self):
        returnStr = ""
        for pair in self.recentTen:
            returnStr += "Time: " + pair[0] + " - Mac: " + pair[1] + "\n\n\n"
        return returnStr






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
