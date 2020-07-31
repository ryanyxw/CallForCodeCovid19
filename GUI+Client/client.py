from kivy.network.urlrequest import UrlRequest
from kivy.logger import Logger
from kivy.logger import LoggerHistory
import sys
import json
import re
import os
from kivy.config import Config
import time

"""
License:

   Copyright 2020 Ryan Wang and Tyllis Xu

   Licensed under the Apache License, Version 2.0 (the "License");
   you may not use this file except in compliance with the License.
   You may obtain a copy of the License at

       http://www.apache.org/licenses/LICENSE-2.0

   Unless required by applicable law or agreed to in writing, software
   distributed under the License is distributed on an "AS IS" BASIS,
   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
   See the License for the specific language governing permissions and
   limitations under the License.
"""

class NoInternetException(Exception):
    pass
class TimeoutException(Exception):
    pass

this = sys.modules[__name__]

def init(logDir,verbosityLevel):
    this.__completed__ = False
    this.__code__ = None
    this.__body__ = None
    this.__header__ = {"Content-type": "application/x-www-form-urlencoded","Accept": "*/*", "User-Agent": "COVIDContactTracerApp/1.0", "Content-Length": 1}
    this.__baseURL__ = "http://covidcontacttracer-appreciative-civet-qu.mybluemix.net/"
    this.logVerbosity = verbosityLevel
    if this.logVerbosity < 10:
        this.log_level = "trace"
    elif this.logVerbosity < 20:
        this.log_level = "debug"
    elif this.logVerbosity < 30:
        this.log_level = "info"
    elif this.logVerbosity < 40:
        this.log_level = "warn"
    elif this.logVerbosity < 50:
        this.log_level = "error"
    elif this.logVerbosity == 50:
        this.log_level = "critical"
    else:
        kivy.config.log_level = "trace"
    if os.path.isdir(logDir):
        Config.set('kivy', 'log_level', this.log_level)
        Config.set('kivy', 'log_dir', logDir)
        Config.set('kivy', 'log_name', "CovidContactTracerClient_%y-%m-%d_%_.log")
        Config.set('kivy', 'log_maxfiles', 49)
        Config.write()
        return True
    else:
        return False



#  PURPOSE: Delcares the user to the server.
#  INPUT: True MAC address of user as a string
#  RETURN: A secret key to be used in other requests as a string
#  ERROR: returns 2 when a retry is needed (server error) and a 3 if the user is already initiated, return 4 for invalid MAC Address
#  CATCH-ALL: Returns a 1 for other errors.
def initSelf(MacAddrSelf):
    d = {}
    d["Self"] = MacAddrSelf
    # Form data must be provided already urlencoded.
    postfields = json.dumps(d)
    # Sets request method to POST,
    # Content-Type header to application/x-www-form-urlencoded
    # and data to send in request body.
    Logger.info("initSelf:postfields=" + postfields)
    try:
        httpReq(this.__baseURL__+"InitSelf",postfields,this.__header__,60,"POST")
    except NoInternetException:
        return 2
    except TimeoutException:
        return 2
    code = this.__code__
    if type(code) is not int:
        Logger.error("initSelf:Unknown Error: No response")
        return 2
    body = repr(this.__body__)

    Logger.info("initSelf: Code = " + str(code) + " Msg: " + body)
    if "Initiated." not in body and code == 201:
        try:
            secretPattern = re.compile(r'(\S{56})')

            jdata = json.loads(body.replace("\'", "\""))
            secret = jdata["Secret"]
            secret = secretPattern.match(secret).group(1)  # sanitization
        except KeyError:
            return 1
    if code == 201:
        Logger.debug("initSelf: Recieved key:"+secret+" extracted from: "+body)
        return secret
    elif code >= 500:
        #  Retry
        Logger.warning("initSelf:Server Error: " + str(code) + " msg: " + body)
        return 2
    elif code == 400:
        Logger.warning("initSelf:400 Error:msg: " + body)
        return 4
    elif code == 403:
        Logger.warning("initSelf:403 Error:msg: " + body)
        return 3  # Permission denied due to initiated
    else:
        #  Unknown Error
        Logger.error("initSelf:Unknown Error: " + str(code) + " msg: " + body)
        return 1


#  PURPOSE: Reports the user as positive and the potential contacted persons.
#  INPUT: True MAC address of user(string), the secret key(string), and list of MAC Addresses (CSV string). The CSV list cannot be empty.
#  RETURN: 0 on success
#  ERROR: returns 2 when a retry is needed (server error), return 3 for incorrect secret key, return 4 for empty/invalid CSV contacted list.
#  CATCH-ALL: Returns a 1 for other errors.
def positiveReport(MacAddrSelf,secretKey,metAddrList):
    d = {}
    d['Self'] = MacAddrSelf
    d['MetAddrList'] = metAddrList
    d['Secret'] = secretKey
    # Form data must be provided already urlencoded.
    postfields = json.dumps(d)
    # Sets request method to POST,
    # Content-Type header to application/x-www-form-urlencoded
    # and data to send in request body.
    Logger.info("positiveReport:postfields="+postfields)
    try:
        httpReq(this.__baseURL__+'positiveReport',postfields,this.__header__,300,'POST')
    except NoInternetException:
        return 2
    except TimeoutException:
        return 2
    code = this.__code__
    if type(code) is not int:
        Logger.error("positiveReport:Unknown Error: No response")
        return 2
    body = repr(this.__body__)


    if code == 201 and "Get well soon. " in body:
        #  Server Ack Success
        return 0
    elif code >= 500:
        #  Retry
        Logger.warning("positiveReport:Server Error: " + str(code) + " msg: " + body)
        return 2
    elif code == 400:
        Logger.warning("positiveReport:400 Error:msg: " + body)
        return 4
    elif code == 403:
        Logger.warning("positiveReport:403 Error:msg: " + body)
        return 3  # Permission denied due to initiated
    else:
        #  Unknown Error
        Logger.error("positiveReport:Unknown Error: " + str(code) + " msg: " + body)
        return 1


#  PURPOSE: Reports the user as negative.
#  INPUT: True MAC address of user(string), the secret key(string)
#  RETURN: 0 on success
#  ERROR: returns 2 when a retry is needed (server error), return 3 for incorrect secret key, return 4 for empty/invalid MAC addr of self.
#  CATCH-ALL: Returns a 1 for other errors.
def negativeReport(MacAddrSelf,secretKey):
    d = {}
    d['Self'] = MacAddrSelf
    d['Secret'] = secretKey
    # Form data must be provided already urlencoded.
    postfields = json.dumps(d)
    # Sets request method to POST,
    # Content-Type header to application/x-www-form-urlencoded
    # and data to send in request body.
    Logger.info("negativeReport:postfields="+postfields)
    try:
        httpReq(this.__baseURL__+'negativeReport',postfields,this.__header__,30,'POST')
    except NoInternetException:
        return 2
    except TimeoutException:
        return 2
    code = this.__code__
    if type(code) is not int:
        Logger.error("negativeReport:Unknown Error: No response")
        return 2
    body = repr(this.__body__)


    if code == 201 and "Stay healthy." in body:
        #  Server Ack Success
        return 0
    elif code >= 500:
        #  Retry
        Logger.warning("negativeReport:Server Error: " + str(code) + " msg: " + body)
        return 2
    elif code == 400:
        Logger.warning("negativeReport:400 Error:msg: " + body)
        return 4
    elif code == 403:
        Logger.warning("negativeReport:403 Error:msg: " + body)
        return 3  # Permission denied due to initiated
    else:
        #  Unknown Error
        Logger.error("negativeReport:Unknown Error: " + str(code) + " msg: " + body)
        return 1


#  PURPOSE: Gets the state of the user from the server.
#  INPUT: MAC address of user(string), the secret key(string)
#  INPUT (Android 10 Only): A string of MAC addresses with the user's true MAC Address first as a CSV string, the user's secret key
#  RETURN: -1 if user has contacted someone with the virus, 0 if the user has not
#  ERROR: returns 2 when a retry is needed (server error), return 3 for incorrect secret key, return 4 for empty/invalid MAC addr of self, return 5 if more than 1 request in 8 hours
#  CATCH-ALL: Returns a 1 for other errors.
def queryMyMacAddr(self,secret):
    d = {}
    d['Self'] = self
    d['Secret'] = secret
    # Form data must be provided already urlencoded.
    postfields = json.dumps(d)
    # Sets request method to POST,
    # Content-Type header to application/x-www-form-urlencoded
    # and data to send in request body.
    Logger.debug("QueryMyMacAddr:postfields="+postfields)
    try:
        httpReq(this.__baseURL__+'QueryMyMacAddr',postfields,this.__header__,30,'POST')
    except NoInternetException:
        return 2
    except TimeoutException:
        return 2
    code = this.__code__
    if type(code) is not int:
        Logger.error("QueryMyMacAddr:Unknown Error: No response")
        return 2
    body = repr(this.__body__)

    if code == 221:
        return -2
    elif code == 211:
        #  Contacted Positive MAC Addr
        return -1
    elif code == 200:
        #  No Match
        return 0
    elif code >= 500:
        #  Retry
        Logger.warning("queryMyMacAddr:Server Error: " + str(code) + " msg: " + body)
        return 2
    elif code == 400:
        Logger.warning("queryMyMacAddr:400 Error:msg: " + body)
        return 4
    elif code == 403:
        Logger.warning("queryMyMacAddr:403 Error:msg: " + body)
        return 3  # Permission denied due to initiated
    elif code == 429:
        Logger.warning("queryMyMacAddr:429 Error:msg: " + body)
        return 5  # Permission denied due to initiated
    else:
        #  Unknown Error
        Logger.error("queryMyMacAddr:Unknown Error: " + str(code) + " msg: " + body)
        return 1


#  PURPOSE: Marks the users MAC address for deletion and removes the user's state and secret key.
#  INPUT: MAC address of user(string), the secret key(string), and list of MAC Addresses (CSV string)
#  RETURN: 0 on success
#  ERROR: returns 2 when a retry is needed (server error), return 3 for incorrect secret key, return 4 for empty/invalid MAC addr of self.
#  CATCH-ALL: Returns a 1 for other errors.
def forgetUser(MacAddrSelf, secretKey):
    d = {}
    d['Self'] = MacAddrSelf
    d['Secret'] = secretKey
    # Form data must be provided already urlencoded.
    postfields = json.dumps(d)
    Logger.info("forgetUser:postfields="+postfields)
    # Sets request method to POST,
    # Content-Type header to application/x-www-form-urlencoded
    # and data to send in request body.
    try:
        httpReq(this.__baseURL__+'ForgetMe',postfields,this.__header__,30,'POST')
    except NoInternetException:
        return 2
    except TimeoutException:
        return 2
    code = this.__code__
    if type(code) is not int:
        Logger.error("ForgetMe:Unknown Error: No response")
        return 2
    body = repr(this.__body__)


    if code == 201 and "Goodbye. " in body:
        #  Server Ack Success
        return 0
    elif code >= 500:
        #  Retry
        Logger.warning("forgetUser:Server Error: " + str(code) + " msg: " + body)
        return 2
    elif code == 400:
        Logger.warning("forgetUser:400 Error:msg: " + body)
        return 4
    elif code == 403:
        Logger.warning("forgetUser:403 Error:msg: " + body)
        return 3  # Permission denied due to initiated
    else:
        #  Unknown Error
        Logger.error("forgetUser:Unknown Error: " + str(code) + " msg: " + body)
        return 1


def on_complete(request,req):
    Logger.info("Request Completed")
    this.__completed__ = True
    Logger.info(str(type(req)))
    if str(type(req)) in ["<class 'socket.gaierror'>","<class 'OSError'>","<class 'Exception'>"]:
        raise NoInternetException
    elif str(type(req)) in ["<class 'socket.timeout'>"]:
        raise TimeoutException
    return None


def httpReq(url,body,headers,timeout,method):
    if body is not None:
        this.__header__["Content-Length"] = len(body)
    else:
        this.__header__["Content-Length"] = 0
    Logger.info(repr(url) + repr(body) + repr(headers) + repr(timeout) + repr(method))
    req = UrlRequest(url, req_body=body,req_headers=headers,timeout=timeout,method=method,debug=False,on_error=on_complete,on_redirect=on_complete,on_failure=on_complete)
    req.wait()
    if req.resp_status is not None:
        this.__code__ = req.resp_status
        this.__body__ = req.result
    else:
        this.__code__ = 500
        this.__body__ = ""

#  Function to reset resources within this module, do not call
def resetResources():
    pass


#  Function to free all resources used, call when exiting
def freeResources():
    pass



def testInternetConnection():
    try:
        httpReq(this.__baseURL__+"networkTest","{}",this.__header__,10,'GET')
    except NoInternetException:
        return False
    except TimeoutException:
        return False
    if this.__code__ != 500:
        return True
    else:
        return False


#  test function, do not call
def tests():
    print("initiating program")

    print(init("logFile",0)==False)

    print("Test Internet Connection")
    if testInternetConnection():
        print("True")
    else:
        raise OSError

    self = "FF:11:2E:7A:5B:6A"
    others = "4F:11:2E:7A:5B:6A, 4F:1A:2E:7A:5B:6A, 4F:11:77:7A:5B:6A"
    person2 = "4F:11:2E:7A:5B:6A"
    print("\ninitiating 2 users")
    secret1 = initSelf(self)
    secret2 = initSelf(person2)

    print("\ntesting secret key")
    print(len(secret1)==56)

    print("\nMimicking normal behavior")
    print(queryMyMacAddr(self,secret1)==0)
    print(positiveReport(self,secret1,others)==0)
    print(queryMyMacAddr(person2,secret2)==-1)
    print(negativeReport(self,secret1)==0)
    print(queryMyMacAddr(self,secret1)==5)

    print("\nTrying invalid inputs")
    print(initSelf("invalid input")==4)
    print(queryMyMacAddr("invalid input",secret2)==4)
    print(positiveReport(self,secret1,"invalid input")==4)
    print(positiveReport("invalid input",secret1,others)==4)
    print(negativeReport("invalid input",secret1)==4)
    print(forgetUser("invalid input", secret1)==4)

    print("\ntrying to create existing user")
    print(initSelf(self)==3)

    print("\ntrying invalid secret keys")
    print(queryMyMacAddr(self,secret2)==3)
    print(queryMyMacAddr(self,"not a key")==3)
    print(positiveReport(self,secret2,others)==3)
    print(positiveReport(self,"not a key",others)==3)
    print(negativeReport(self,secret2)==3)
    print(negativeReport(self,"not a key")==3)
    print(forgetUser("4F:11:77:7A:5B:6A", secret1)==3)  #  Non-initiated user
    print(forgetUser(self, secret2)==3)
    print(forgetUser(self, "not a key")==3)

    print("\nRemoving users")
    print(forgetUser(self, secret1)==0)
    print(forgetUser(person2, secret2)==0)
    freeResources()


if __name__ == '__main__':
    tests()
