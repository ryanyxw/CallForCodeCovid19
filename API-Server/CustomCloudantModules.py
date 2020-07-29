import cloudant
from cloudant.client import Cloudant
from cloudant.document import Document
from cloudant.error import CloudantException
from cloudant.result import Result, ResultByKey
import json
import sys
import datetime
import creds

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


this = sys.modules[__name__]
this.__username__ = creds.username
this.__apiKey__ = creds.apiKey
this.__client__ = None
this.__userDatabase__ = None
this.userDatabaseName = "persons_db"
this.hospitalDatabaseName = "hospitals_db"


def init():
    client = Cloudant.iam(this.__username__, this.__apiKey__)
    client.connect()

    userDatabase = client.create_database(this.userDatabaseName)
    if not userDatabase.exists():
        #  IDK, raise some error or panic
        client.create_database(this.userDatabaseName)
    hospitalDatabase = client.create_database(this.hospitalDatabaseName)
    if not userDatabase.exists():
        #  IDK, raise some error or panic
        client.create_database(this.hospitalDatabaseName)
    this.__client__ = client
    this.__userDatabase__ = userDatabase
    this.__hospitalDatabase__ = hospitalDatabase


def personExists(MAC_Addr):
    client = this.__client__
    userDatabase = this.__userDatabase__
    if not Document(userDatabase, MAC_Addr).exists():
        return False
    else:
        try:
            if getSecretKey(MAC_Addr) != "":
                return True
            else:
                return False
        except KeyError:
            return False


def addPerson(MAC_Addr,state,secretKey,time):
    #  Add a person if not already created
    client = this.__client__
    userDatabase = this.__userDatabase__
    if not personExists(MAC_Addr):
        data = {}
        data['_id'] = MAC_Addr
        data['State'] = state
        data['SecretKey'] = secretKey
        data['TimeOfLastAccess'] = time.strftime('%Y-%m-%d_%H:%M:%S.%f')
        try:
            document = userDatabase.create_document(data, throw_on_exists=True)
            return True
        except cloudant.error.CloudantDatabaseException:
            changeState(MAC_Addr,state)
            changeSecretKey(MAC_Addr,secretKey)
            return True
    return False


def changeState(MAC_Addr,newState):
    # Edit or add user state
    client = this.__client__
    userDatabase = this.__userDatabase__
    if Document(userDatabase, MAC_Addr).exists():
        with Document(userDatabase, MAC_Addr) as document:
            document.field_set(document, 'State', newState)
            return True
    else:
        return False


def changeSecretKey(MAC_Addr,secretKey):
    # Edit or add user Secret Key
    client = this.__client__
    userDatabase = this.__userDatabase__
    if Document(userDatabase, MAC_Addr).exists():
        with Document(userDatabase, MAC_Addr) as document:
            document.field_set(document, 'SecretKey', secretKey)
            return True
    else:
        return False


def changeTimeOfLastAccess(MAC_Addr,time):
    # Edit or add user time of last access
    client = this.__client__
    userDatabase = this.__userDatabase__
    if Document(userDatabase, MAC_Addr).exists():
        with Document(userDatabase, MAC_Addr) as document:
            document.field_set(document, 'TimeOfLastAccess', time.strftime('%Y-%m-%d_%H:%M:%S.%f'))
            return True
    else:
        return False


def getState(MAC_Addr):
    client = this.__client__
    userDatabase = this.__userDatabase__
    if Document(userDatabase, MAC_Addr).exists():
        with Document(userDatabase, MAC_Addr) as document:
            document.fetch()
            return document['State']
    else:
        return None


def getSecretKey(MAC_Addr):
    client = this.__client__
    userDatabase = this.__userDatabase__
    if Document(userDatabase, MAC_Addr).exists():
        with Document(userDatabase, MAC_Addr) as document:
            document.fetch()
            return document['SecretKey']
    else:
        return None


def getTimeOfLastAccess(MAC_Addr):
    client = this.__client__
    userDatabase = this.__userDatabase__
    if Document(userDatabase, MAC_Addr).exists():
        with Document(userDatabase, MAC_Addr) as document:
            document.fetch()
            if 'TimeOfLastAccess' in document:
                strTime = document['TimeOfLastAccess']
                time = datetime.datetime.strptime(strTime, '%Y-%m-%d_%H:%M:%S.%f')
            else:
                time = datetime.datetime.fromisoformat('2011-11-04 00:05:23.283')
            return time
    else:
        return None


def removePerson(MAC_Addr):
    client = this.__client__
    userDatabase = this.__userDatabase__
    if Document(userDatabase, MAC_Addr).exists():
        with Document(userDatabase, MAC_Addr) as document:
            document.delete()
            return True
    else:
        return False

def cloudantCleanup():
    client = this.__client__
    if client:
        client.disconnect()

def resetDatabase(key):
    client = this.__client__
    if key == creds.adminPass:
        client.delete_database(this.userDatabaseName)
        this.__userDatabase__ = client.create_database(this.userDatabaseName)
        client.delete_database(this.hospitalDatabaseName)
        this.__hospitalDatabase__ = client.create_database(this.hospitalDatabaseName)
        return True
    else:
        return False


def hospitalExists(ID):
    client = this.__client__
    userDatabase = this.__hospitalDatabase__
    if not Document(userDatabase, ID).exists():
        return False
    return True


def addHospital(ID,password):
    #  Add a person if not already created
    client = this.__client__
    userDatabase = this.__hospitalDatabase__
    if not hospitalExists(ID):
        data = {}
        data['_id'] = ID
        data['Password'] = password
        try:
            document = userDatabase.create_document(data, throw_on_exists=True)
            return True
        except cloudant.error.CloudantDatabaseException:
            return False


def getHospitalPassword(ID):
    client = this.__client__
    userDatabase = this.__hospitalDatabase__
    if Document(userDatabase, ID).exists():
        with Document(userDatabase, ID) as document:
            document.fetch()
            return document['Password']
    else:
        return None


def revokeHospital(ID):
    client = this.__client__
    userDatabase = this.__hospitalDatabase__
    if Document(userDatabase, ID).exists():
        with Document(userDatabase, ID) as document:
            document.delete()
            return True
    else:
        return False


def testCloudant():
    init()
    print("exists? \n")
    print(personExists("ab:bc:cd:de:ef:99"))
    print("add person \n")
    print(addPerson("ab:bc:cd:de:ef:99",4,""))
    print("exists? \n")
    print(personExists("ab:bc:cd:de:ef:99"))
    print(changeSecretKey("ab:bc:cd:de:ef:99", "supersecret"))
    print("get status \n")
    print(getState("ab:bc:cd:de:ef:99"))
    print(getSecretKey("ab:bc:cd:de:ef:99"))
    print(removePerson("ab:bc:cd:de:ef:99"))
    cloudantCleanup()

#testCloudant()
