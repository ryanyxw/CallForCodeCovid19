from kivy.app import App
from kivy.lang import Builder
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.widget import Widget
from kivy.uix.gridlayout import GridLayout
from kivy.uix.label import Label
from kivy.properties import ObjectProperty
from kivy.storage.jsonstore import JsonStore
#Changes the window size
from kivy.core.window import Window
import kivy.metrics
Window.size = (kivy.metrics.mm(72.3), kivy.metrics.mm(157.8)) #Height, Width
#MAC
import subprocess
import os
import datetime
import sys
#Regular Expressions
import re
#Client
import client
#network interfaces
import netifaces
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

this.logVerbosity = 20
this.storeName = 'local'

#Manages all permanent storage and adding into the JSON file
this.store = JsonStore(this.appPath + os.sep + this.storeName + '.json')
logger = logging.getLogger('MainGUI')
logger.setLevel(0)
rotHandle = logging.handlers.RotatingFileHandler(this.appPath + os.sep + 'main.log', maxBytes=10485760, backupCount=10)
rotHandle.setLevel(this.logVerbosity)
logger.addHandler(rotHandle)

class storageUnit():

    def __init__(self):
        self.logger = logging.getLogger('MainGUI.storageUnit')
        self.logger.info('creating an instance of storageUnit')

#Adds a unknown / new mac address that was not on the previous network into the json file
    def addEntry(self, macAddress, time):
        if macAddress in this.store.get("macDict")["value"]:
            #this.store.get("macDict")["value"][macAddress] += [time]#HEREEEee
            this.store.get("macDict")["value"][macAddress] += ["TEST"]#HEREEE
            this.store.get("recentTen")["value"] = [[time, macAddress]] + this.store.get("recentTen")["value"][:9]
            self.logger.info('addEntry updated ' + macAddress + ' met at '+time)
        else:
            this.store.get("numEntries")["value"] += 1
            this.store.get("macDict")["value"][macAddress] = [time]
            this.store.get("recentTen")["value"] = [[time, macAddress]] + this.store.get("recentTen")["value"][:9]
            self.logger.info('addEntry added ' + macAddress + ' met at '+time)
#Checks if the previous prevNetwork is the same as foreignSet, which is a set
    def isSamePrevNetwork(self, foreignSet):
        returnArr = []
        for i in foreignSet:
            if i not in this.store.get("prevNetwork")["value"]:
                returnArr += [i]
        self.logger.info('isSamePrevNetwork filtered ' + foreignSet + ' into ' + returnArr)
        return returnArr

#This entire class is meant for macAddress collection
class GetMacAdd():
    def __init__(self, **kwargs):
        #super(HomePage, self).__init__(**kwargs)
        print("enter GetMacAdd")
        self.storage = storageUnit()

        self.supported = None  #  Documents whether our mac address collection method is supported

        self.logger = logging.getLogger('MainGUI.GetMacAdd')
        self.logger.info('creating an instance of GetMacAdd')


    def pressed(self, instance):
        macList = self.getMac()
        self.label3.text = "SelfMac : " + macList
        self.logger.info('Button pressed')

    def getString(self, recentTen):
        returnStr = ""
        for i in recentTen:
            returnStr += repr(i)+ "\n"
        self.logger.info('getString returned ' returnStr + ' from input ' + recentTen)
        return returnStr

    def getMacSelf(self):
        selfMac = []
        isContractionStart = re.compile(r'^([\da-fA-F]):')
        isContractionMid = re.compile(r':([\da-fA-F]):')
        isContractionEnd = re.compile(r':([\da-fA-F])$')
        for interface in netifaces.interfaces():
            self.logger.info('getMacSelf checking interface ' + interface + '')
            try:
                mac = netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]['addr']
                self.logger.info('getMacSelf:' + interface + ' has MAC addr ' + )
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
            except KeyError:
                pass
            except ValueError:
                pass

        if selfMac == []:
            raise OSError
        else:
            return selfMac

    def tryGetMac(self):

        fails = 0
        if os.path.isfile(os.sep+"proc"+os.sep+"net"+os.sep+"arp"):
            if os.access(os.sep+"proc"+os.sep+"net"+os.sep+"arp", os.R_OK):
                f=open(os.sep+"proc"+os.sep+"net"+os.sep+"arp", "r")
                result = f.read()
                self.supported = True  #  Documents whether our mac address collection method is supported
                return result
            else:
                fails = fails + 1
        else:
            fails = fails + 1
        try:
            result = subprocess.run(['arp', '-a'], stdout=subprocess.PIPE)
            self.supported = True #  Documents whether our mac address collection method is supported
            return result
        except subprocess.CalledProcessError:
            fails = fails + 1
            pass
        self.supported = False #  Documents whether our mac address collection method is supported
        return ""

    def getMac(self):
        result = self.tryGetMac()

        macInitStr = result

        macInitStr = repr(macInitStr)
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


        compareSet = set(macList)
        diffArr = self.storage.isSamePrevNetwork(compareSet)
        if len(diffArr) == 0:
            return self.getString(self.storage.store.get("recentTen")["value"])
        else:
            for macAdd in diffArr:
                self.storage.addEntry(macAdd, str(datetime.datetime.now()))

            self.storage.store.put("prevNetwork", value = dict.fromkeys(compareSet, 0))
            return self.getString(self.storage.store.get("recentTen")["value"])


#Class for the homepage screen
class HomePage(Screen, Widget):
    def __init__(self, **kwargs):
        super(HomePage, self).__init__(**kwargs)

        #DELETE IN THE END ONLYU USED TO DEBUG
        self.macClass = GetMacAdd()
        self.selfMacAddress = str(self.macClass.getMacSelf()[0])





#Determines if the server initiation is correct (should only be a one time thing)
        isSuccessful = True

        client.init(this.appPath + os.sep + "client.log", this.logVerbosity)
        #self.macClass = GetMacAdd()
#Checks if there is a file. If there is not, initiate all 4 necessary parts
        self.statusLabel = ObjectProperty(None)

        if (not this.store.exists('numEntries')):
            #this.store.put("selfMac", value = self.macClass.getMacSelf()[0])
            this.store.put("selfMac", value = "a1:4f:43:92:25:2e")
            tempSecret = client.initSelf(this.store.get("selfMac")["value"])
            if (tempSecret == 2):
                self.statusLabel.text = "Status: Server Error, Please quit the app and try again (2)"
                isSuccessful = False
            elif (tempSecret == 3):
                isSuccessful = False
                self.statusLabel.text = "Status: User already initiated (3)"
            elif (tempSecret == 4):
                isSuccessful = False
                self.statusLabel.text = "Status: Invalid Mac Address, Please quit the app and try again (4)"
            else:
                this.store.put("secretKey", value = tempSecret)
                this.store.put("numEntries", value = 0)
                this.store.put("macDict", value = dict())
                this.store.put("recentTen", value = list())
                this.store.put("prevNetwork", value = dict())
#                self.statusLabel.text = "Status: Account Registered"
                this.store.put("statusLabel", home = "Status: Account Registered", quitapp = "Status: Click to delete all data", senddata = "Status: Click to report infected")
        if (isSuccessful):
            self.options = ObjectProperty(None)
#macClass variable is just used as a reference to be able to call the getMac class
            self.macClass = GetMacAdd()
            self.selfMacAddress = str(self.macClass.getMacSelf()[0]) #Assumes the first mac address is self mac address
            self.actualMac = self.macClass.getMac()



    def coronaCatcherButtonClicked(self):

        print("coronaCatcherButton clicked")
        returnVal = client.queryMyMacAddr(this.store.get("selfMac")["value"], this.store.get("secretKey")["value"])
        if (returnVal == -1):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", you have contacted someone with the virus. Please quarantine"
        elif (returnVal == 0):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", you are still safe!"
        elif (returnVal == 2):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Server Error, please quit the app and retry (2)"
        elif (returnVal == 3):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Incorrect secret key, you're kinda screwed (3)"
        elif (returnVal == 4):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Invalid mac address, you're kinda screwed (4)"
        elif (returnVal == 5):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Server Overload. Please do not click button twice"
        else:
            self.statusLabel.text = "1 returned"




#This method is used when we click the button to check our current network mac
    def calculateMac(self):
        self.actualMac = self.macClass.getMac()
        self.coronaCatcherButtonClicked()
        return self.actualMac

    #This calculates the offset accordingly (topLeftH and topLeftW are both in terms of proportions)
    def findCoordinates(self, percentage, topLeftWidth, topLeftHeight):
        smallDim = min(Window.size)
        offSet = smallDim * percentage
        xCoor = topLeftWidth * Window.size[1] + offSet#Windows: (Height, Width)
        yCoor = topLeftHeight * Window.size[0] - self.options.size[0] - offSet
        print(xCoor / Window.size[1])
        print(yCoor / Window.size[0])
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
        super(QuitAppPage, self).__init__(**kwargs)
        print("ENTER QuitApp INIT")

        self.statusLabel = ObjectProperty(None)
    def deleteDataAndQuitButtonClicked(self):

        print("DeleteData button Clicked")

        returnValue = client.forgetUser(this.store.get("selfMac")["value"], this.store.get("secretKey")["value"])
        if (returnValue == 0):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Sucess! You may quit the app"
        elif (returnValue == 2):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Server Error (2)"
        elif (returnValue == 3):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", incorrect secret key (3)"
        elif (returnValue == 4):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", invalid mac addr of self (4)"
        elif (returnValue == 1):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", 1 is returned (1)"
        else:
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", server returned unknown command : " + str(returnValue)

    pass

#SendData class page (reference my.kv file)
class SendDataPage(Screen):
    def __init__(self, **kwargs):
        super(SendDataPage, self).__init__(**kwargs)
        print("ENTER SENDDATA INIT")

        self.statusLabel = ObjectProperty(None)
    def getCSVString(self):
        returnStr = this.store.get("selfMac")["value"] + ","
        macDictionary = this.store.get("macDict")["value"]
        for key in macDictionary:
            returnStr += key + ","
        return returnStr

    def imInfectedButtonClicked(self):
        print("imInfected button clicked")

        returnVal = client.positiveReport(this.store.get("selfMac")["value"], this.store.get("secretKey")["value"], self.getCSVString())
        if (returnVal == 2):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Retry is needed(server error). Restart app and try again (2)"
        elif (returnVal == 3):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Incorrect Secret Key. Restart app and try again (3)"
        elif (returnVal == 4):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Invalid CSV. Restart app and contact admin"
        else:
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Request sucess! Get well soon!"

    def iJustRecoveredButtonClicked(self):
        print("iJustRecovered button clicked")

        returnVal = client.negativeReport(this.store.get("selfMac")["value"], this.store.get("secretKey")["value"])
        if (returnVal == 2):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Retry is needed(server error). Restart app and try again (2)"
        elif (returnVal == 3):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Incorrect Secret Key. Restart app and try again (3)"
        elif (returnVal == 4):
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Invalid MAC Address of self. Restart app and contact admin (4)"
        else:
            self.statusLabel.text = "Checked by " + str(datetime.datetime.now()) + ", Request sucess! Good job recovering! "

    pass

#SeeDataPage class page (reference my.kv file)
class SeeDataPage(Screen):
    def __init__(self, **kwargs):
        super(SeeDataPage, self).__init__(**kwargs)
        print("ENTER SEEDATAPAGE INIT")

#Used for future reference and changing the data in the table
        self.data = [0] * 20
#Stores the recentTen aspect of the json file
        self.recentTen = this.store.get("recentTen")["value"]
#Creates the grid used to display the information
        self.table = GridLayout()
        self.table.cols = 2


        print("BEFORE ASSIGN VALUES")
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
        print("renew clicked")
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
        print(Window.size)
        print(type(Window.size))
#        store = JsonStore(this.storeName + '.json')
#        print(store.exists('numEntries'))
#        if (not store.exists('numEntries')):
#            print("enter")
#            store.put("numEntries", value = 0)
#            store.put("macDict", value = dict())
#            store.put("recentTen", value = list())
 #           store.put("prevNetwork", value = dict())
        return kv


if __name__ == "__main__":
    print("ENTER MOST OUTSIDE")
    MyMainApp().run()
    client.freeResources()
    exit()
