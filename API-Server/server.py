import flask
from flask import request, jsonify, session, abort
from flask_api import status
import re
import json
import hashlib
import os
import time
import datetime
import atexit
from expiringdict import ExpiringDict

import CustomCloudantModules as ccm
import creds

"""
Version: 2.2.3
Features:

1. Security:
	1. The server automatically bans anyone who attempts to access the admin
	section without the correct password by IP for 15 minutes
	2. Users who repeatedly conduct behaviors that seek to gain illegitimate
	access, such as SQL injection, password spraying, or spam,
	will be blocked for 15 minutes if they conduct 3 of such actions within the
	span of 15 minutes. Ban time is reset to 15 minutes upon
	every further attempt.
	3. Every user is granted a 52 letter random secret key to prevent user impersonation
	by others that is paired with their own MAC addresses
	4. Hospitals are granted a 52 letter password that is then hashed to verify
	their identity, to prevent inpersonation in case of database leakage
	4. Most forms of USER input is strictly validated against regular expressions
	to prevent attack vectors.
	5. Administration tasks require a special user agent to further prevent
	admin inpersonation
	6. All credentials are stored in a seperate file called creds.py and not
	stored in the online Github repository, to prevent leakage of secret key

2. Privacy:
	1. Only information stored from the user is their MAC addresses. Only one of
	such addresses is initially stored.
	2. Users can only access information regarding their own addresses. They
	cannot see the information of others without another person's 52 letter secret key.
	3. When the user reports that they have tested positive for COVID-19, they
	report to the server the MAC addresses they had encountered and their own MAC addresses.
	4. All MAC addresses encountered by someone who reported to be positive are
	marked on the server. Records are created independent of each other with no
	data indicating correlation. In the case of complete compromise of the database,
	attackers will not be able to know which persons had met each other.
	5. No identifiable information of the user is ever shared with others at any point.

3. Scalability:
	1. This server is written in flask and supports multithreading and could easily
	be upscaled without any impact.
	2. Cloudant database tombstones (leftover records from deletions of user data)
	could be cleared periodically by setting the server to maintenance mode via
	the admin api, allowing it to pause service and give admins the opportunity
	to clear databases with 0 data loss. The server will answer requests with 503
	(code for Service Temporarily Unavailable), prompting the client to retry shortly.
"""

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

# Regular expressions to filter user input
isMacAddr = re.compile(r"([\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2})")
isFloodAddr = re.compile("FF:FF:FF:FF:FF:FF",re.I)
OPERATORS = re.compile('SELECT|UPDATE|INSERT|DELETE|\*|OR|=', re.IGNORECASE)
# Initiate lists of banned entities
ip_ban_list = ExpiringDict(max_len=50*50000, max_age_seconds=15*60)
mac_ban_list = ExpiringDict(max_len=25*50000, max_age_seconds=15*60)
key_ban_list = ExpiringDict(max_len=25*1230, max_age_seconds=15*60)
# Set maintenance mode to false
maintenance = False
# Initiation of custom cloudant manipulation library, IAM signin and database integrity checks
ccm.init()
app = flask.Flask(__name__)


@app.errorhandler(404)
def page_not_found(e):
	ip = request.environ.get('REMOTE_ADDR')
	if ip == '127.0.0.1' or ip == '0.0.0.0' or ip == '0.0.0.0.0.0':
		ip = request.environ.get('HTTP_X_REAL_IP')
	strike(ip,None,None,2)
	return 404

# Test if user is banned (had 3 strikes) or is committing a bannable offense (SQL injection, admin inpersonation)
# This is designed to slow down and discourage attackers without affecting users.
@app.before_request
def before_request():
	global maintenance
	# Test if server in maintenance mode and if it is an admin trying to toggle maintenance mode
	if maintenance and request.path != '/maintenance':
		abort(503)  # return 503 unavailable if it is in maintainance mode and NOT an admin exiting maintenance mode
	# Get identifying information to test against ban list
	ip = request.environ.get('REMOTE_ADDR')
	if ip == '127.0.0.1' or ip == '0.0.0.0' or ip == '0.0.0.0.0.0':
		ip = request.environ.get('HTTP_X_REAL_IP')
	data = request.get_json(force=True)
	if 'Self' in data:
		macList = parseMacAddr(data['Self'])
		if macList == []:
			mac = None
		else:
			mac = macList[0]
	else:
		mac = None
	secretKey = data.get('Secret')
	# Proccess if User is on any ban list
	if ip_ban_list.get(ip) is not None:
		if ip_ban_list.get(ip) >= 3:
			strike(ip,mac,secretKey,1) # +1 strike to renew ban
			abort(403)
	elif mac_ban_list.get(mac) is not None:
		if mac_ban_list.get(mac) >= 3:
			strike(ip,mac,secretKey,1) # +1 strike to renew ban
			abort(403)
	elif key_ban_list.get(secretKey) is not None:
		if key_ban_list.get(secretKey) >= 3:
			strike(ip,mac,secretKey,1) # +1 strike to renew ban
			abort(403)
	# Test if user is attempting to input malicious data
	elif re.search(OPERATORS,repr(mac)+repr(secretKey)) is not None:
		strike(ip,mac,secretKey,3) # 3 strikes for major offense, HIGHLY UNLIKELY to be of user error or application error
		abort(403)
	# test if user is using an invalid (unofficial) User Agent
	elif 'COVIDContactTracerApp' not in request.user_agent.string and creds.adminAgent not in request.user_agent.string:
		strike(ip,mac,secretKey,3) # 3 strikes for major offense, HIGHLY UNLIKELY to be of user error or application error
		abort(403)


#  Takes in a POST request with a json object containing a SINGLE MAC address
#  Returns a secret key based on the MAC address and a HTTP Code 201
#  Stores a copy of secret in the local database
@app.route('/InitSelf', methods=["POST"])
def initSelf():
	data = request.get_json(force=True)
	if 'Self' not in data:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Improper Request', 400
	self = data['Self']
	selfList = parseMacAddr(self)
	if not selfList:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Bad MAC Address!', 400
	secret = initNewUser(selfList)
	if secret == "":
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Already Initiated. ', 403
	elif secret is None:
		return status.HTTP_500_INTERNAL_SERVER_ERROR
	else:
		return jsonify(
			Secret = secret
		), status.HTTP_201_CREATED


#  Takes in a POST request with a json object containing a SINGLE MAC address and a secret key
#  Returns a HTTP 201 and a msg = "Get well soon." message in JSON
@app.route('/positiveReport', methods=["POST"])
def receivePositiveReport():
	data = request.get_json(force=True)
	if not ('Self' in data and 'Secret' in data and 'MetAddrList' in data):
		return 'Improper Request', 400
	self = data['Self']
	secret = data['Secret']
	metAddrList = data['MetAddrList']
	self = parseMacAddr(self)
	metAddrList = parseMacAddr(metAddrList)
	if not metAddrList or not self:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Bad MAC Address!', 400
	valid = verifySecret(self[0],secret)
	if valid:
		markPositive(metAddrList, self)
		return jsonify(
			msg = "Get well soon. "
		), status.HTTP_201_CREATED
	else:
		strike(None,self[0],secret,1)  # 1 strike for suspicious behavior, mac address and secret key banned if 3 strikes in 15 minutes, to prevent password guessing
		return 'Incorect Secret Key', 403


#  Takes in a POST request string with MAC addresses in CSV format
#  Returns a Boolean atRisk status in JSON
@app.route('/QueryMyMacAddr', methods=["POST"])
def receiveQueryMyMacAddr():
	data = request.get_json(force=True)
	if 'Self' not in data or 'Secret' not in data:
		return 'Improper Request', 400
	self = data['Self']
	secret = data['Secret']
	addrList = parseMacAddr(self)
	if not addrList:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Bad MAC Address!', 400
	if not verifySecret(addrList[0],secret):
		strike(None,addrList[0],secret,1)   # 1 strike for suspicious behavior, mac address and secret key banned if 3 strikes in 15 minutes, to prevent password guessing
		return 'Bad Request Key', 403
	if not passRateLimit(addrList[0]):
		strike(None,addrList[0],secret,1)
		return 'Too many query requests', 429
	state = queryAddr(addrList)
	if state == 2:
		updateRateLimit(addrList[0])
		return "At risk, but unauthorative", 221 #Custom response code for at-risk unauthorative
	elif state == 1:
		updateRateLimit(addrList[0])
		return "At risk, but unauthorative", 211 #Custom response code for at-risk unauthorative
	elif state == 0:
		updateRateLimit(addrList[0])
		return "Not at risk", status.HTTP_200_OK
	elif state == -1:
		updateRateLimit(addrList[0])
		strike(request.environ.get('REMOTE_ADDR'),addrList[0],secret,1)
		return 'No such user or invalid keys', 403
	else:
		return status.HTTP_500_INTERNAL_SERVER_ERROR


#  Takes in a POST request with a json object containing a SINGLE MAC address and a secret key
#  Returns a HTTP 201 and a msg = "Stay healthy." message in JSON
@app.route('/negativeReport', methods=["POST"])
def receiveNegativeReport():
	data = request.get_json(force=True)
	if 'Self' not in data or 'Secret' not in data:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Improper Request', 400
	self = data['Self']
	secret = data['Secret']
	addr = parseMacAddr(self)
	if not addr:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Bad MAC Address!', 400
	valid = verifySecret(addr[0],secret)
	if valid:
		strike(None,addr[0],secret,1)
		markNegative(addr[0], secret)
		return jsonify(
			msg = "Stay healthy. "
		), status.HTTP_201_CREATED
	else:
		return 'Incorect Secret Key', 403
		strike(None,addr[0],secret,1)  # 1 strike for suspicious behavior, mac address and secret key banned if 3 strikes in 15 minutes, to prevent password guessing


@app.route('/ForgetMe', methods=["POST"])
def forgetSelf():
	data = request.get_json(force=True)
	if 'Self' not in data or 'Secret' not in data:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Improper Request', 400
	self = data['Self']
	secret = data['Secret']
	addr = parseMacAddr(self)
	if not addr:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Bad MAC Address!', 400
	valid = verifySecret(addr[0],secret)
	if valid:
		deleteUser(addr[0],secret)
		return jsonify(
			msg = "Goodbye. "
		), status.HTTP_201_CREATED
	else:
		strike(request.environ.get('REMOTE_ADDR'),addr[0],secret,1)   # 1 strike for suspicious behavior, mac address and secret key banned if 3 strikes in 15 minutes, to prevent password guessing
		return 'Incorect Secret Key', 403


def initNewUser(selfList):
	addr = selfList[0]
	secret = ""
	time = datetime.datetime.fromisoformat('2011-11-04 00:05:23.283')
	if not ccm.personExists(addr):
		secret = hashlib.sha224((addr+str(os.urandom(128))+creds.salt).encode('utf-8')).hexdigest()
		success = ccm.addPerson(addr,4,secret,time)  # States: 1. Recovered, 2. Positive, 3. Contacted, 4. Neutral, 5. Confirmed Recovery, 6. Confirmed Positive, 7. Confirmed Contact
		if not success:
			raise cloudant.error.CloudantDatabaseException
	else: #person, exists, but may not be initiated. This only occurs if person contacted a person marked positive
		if (ccm.getState(addr) == 3 or ccm.getState(addr) == 2 or ccm.getState(addr) == 1) and ccm.getSecretKey(addr) == "":
			secret = hashlib.sha224((addr+str(os.urandom(128))).encode('utf-8')).hexdigest()
			success1 = ccm.changeSecretKey(addr,secret)
			success2 = ccm.changeTimeOfLastAccess(addr,time)
			if not success1 or not success2:
				raise cloudant.error.CloudantDatabaseException
	return secret


def verifySecret(addr, secret):
	safetyCheck = re.compile(r'^([a-z0-9]{56})$')
	try:
		safeSecret = safetyCheck.fullmatch(str(secret)).group(1)
	except AttributeError:
		return False
	if not ccm.personExists(addr):
		return False
	if not safeSecret:
		return False
	if secret == ccm.getSecretKey(addr):
		return True
	else:
		return False


# States: 1. Recovered, 2. Positive, 3. Contacted, 4. Neutral, 5. Confirmed Recovery, 6. Confirmed Positive, 7. Confirmed Contact
def markPositive(addrList, self):
	if ccm.getState(self[0]) == 6:
		selfState = 6
		metState = 7
	else:
		selfState = 2
		metState = 3
	for positive in addrList:
		if ccm.personExists(positive):  # Change state if person exists
			# retry the write to the database up to 10 times if it fails
			attempt = 1
			while attempt <= 10:
				if ccm.getState(positive) < metState:
					success = ccm.changeState(positive,metState)
				else:
					success = True
				time.sleep(0.1)  # Delay to prevent reaching free tier IBM Cloudant limits
				if success:
					break
				else:
					attempt = attempt + 1
		else:
			# if person not exist, create an unintiated Person with state
			attempt = 1
			while attempt <= 10:
				success = ccm.addPerson(positive,metState,"",datetime.datetime.fromisoformat('2011-11-04 00:05:23.283'))
				time.sleep(0.1)  # Delay to prevent reaching free tier IBM Cloudant limits
				if success:
					break
				else:
					attempt = attempt + 1

	for positive in self:
		if ccm.personExists(positive):  # Change state if person exists
			# retry the write to the database up to 10 times if it fails
			attempt = 1
			while attempt <= 10:
				success = ccm.changeState(positive,selfState)
				time.sleep(0.1)  # Delay to prevent reaching free tier IBM Cloudant limits
				if success:
					break
				else:
					attempt = attempt + 1
		else:
			# if person not exist, create an unintiated Person with state
			attempt = 1
			while attempt <= 10:
				success = ccm.addPerson(positive,selfState,"",datetime.datetime.fromisoformat('2011-11-04 00:05:23.283'))
				time.sleep(0.1)  # Delay to prevent reaching free tier IBM Cloudant limits
				if success:
					break
				else:
					attempt = attempt + 1


def markNegative(negative,secret):
	if not verifySecret(negative,secret):  # Do nothing if secret key does not match
		return None
	ccm.changeState(negative,1)  # Mark person as recovered


def deleteUser(user, secret):
	if not verifySecret(user,secret):  # Do nothing if secret key does not match
		return None
	ccm.removePerson(user)


def queryAddr(addrList):
	for addr in addrList:
		if ccm.getState(addr) == 3 or  ccm.getState(addr) == 2:
			return 1
		elif ccm.getState(addr) == 6 or  ccm.getState(addr) == 7:
			return 2
	return 0


def parseMacAddr(AddrStr):
	#sanitization of all input
	addrList = re.findall(isMacAddr,AddrStr)
	addrFound = []
	for addr in addrList:
		if re.match(isFloodAddr,addr) is None:
			addrFound.append(addr.upper())
	return addrList


def passRateLimit(macAddr):
	currentTime = datetime.datetime.now()
	lastAccess = ccm.getTimeOfLastAccess(macAddr)
	allowedTime = lastAccess + datetime.timedelta(hours=8)
	if allowedTime < currentTime:
		return True
	else:
		return False


def updateRateLimit(macAddr):
	currentTime = datetime.datetime.now()
	ccm.changeTimeOfLastAccess(macAddr,currentTime)


@app.route('/resetDatabase', methods=["POST"])
def databaseReset():
	if creds.adminAgent not in request.user_agent.string:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return "Permission Denied",403
	data = request.get_json(force=True)
	if 'key' not in data:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return "Permission Denied",403
	key = data['key']
	if ccm.resetDatabase(key):
		return "Action Completed", 202
	else:
		strike(request.environ.get('REMOTE_ADDR'),None,None,3)
		return "Permission Denied", 403


@app.route('/clearCache',methods=["POST"])
def clearCache():
	if creds.adminAgent not in request.user_agent.string:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return "Permission Denied",403
	data = request.get_json(force=True)
	if 'key' not in data:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return "Permission Denied",403
	if data['key'] == creds.adminPass:
		ip_ban_list = []
		mac_ban_list = []
		key_ban_list = []
		return "Action Completed", 202
	else:
		strike(request.environ.get('REMOTE_ADDR'),None,None,3)
		return "Permission Denied", 403


@app.route('/getCache',methods=["POST"])
def getCache():
	if creds.adminAgent not in request.user_agent.string:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return "Permission Denied",403
	data = request.get_json(force=True)
	if 'key' not in data:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return "Permission Denied",403
	if data['key'] == creds.adminPass:
		caches = "IP: " + repr(ip_ban_list) + ", MAC: " + repr(mac_ban_list) + ", Secrets: " + repr(key_ban_list)
		return caches, 200
	else:
		strike(request.environ.get('REMOTE_ADDR'),None,None,3)
		return "Permission Denied", 403


def strike(ip,mac,secretKey,strikes):
	if ip is not None:
		if ip in ip_ban_list:
			newEntry = ip_ban_list[ip] + strikes
			ip_ban_list[ip] = newEntry
		else:
			ip_ban_list[ip] = strikes
	if mac is not None:
		if mac in mac_ban_list:
			newEntry = mac_ban_list[mac] + strikes
			mac_ban_list[mac] = newEntry
		else:
			mac_ban_list[mac] = strikes
	if secretKey is not None:
		if secretKey in key_ban_list:
			newEntry = key_ban_list[secretKey]+ strikes
			key_ban_list[secretKey] = newEntry
		else:
			key_ban_list[secretKey] = strikes


@app.route('/hospitalReport',methods=["POST"])
def medConfirm():
	data = request.get_json(force=True)
	if not ('ID' in data and 'Password' in data and 'Positives' in data):
		return 'Improper Request', 400
	ID = data['ID']
	password = data['Password']
	positives = data['Positives']
	positives = parseMacAddr(positives)
	if not positives:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Bad MAC Addresses!', 400
	valid = verifyHospital(ID,password)
	if valid:
		confirmPositive(positives)
		return jsonify(
			msg = "Input recorded"
		), status.HTTP_201_CREATED
	else:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Incorect Key', 403


def verifyHospital(ID,password):
	safetyCheck = re.compile(r'^([a-z0-9]{56})$')
	try:
		safePass = safetyCheck.fullmatch(str(password)).group(1)
	except AttributeError:
		return False
	if not ccm.hospitalExists(ID):
		return False
	if not safePass:
		return False
	if hashlib.sha224(safePass.encode('utf-8')).hexdigest() == ccm.getHospitalPassword(ID):
		return True
	else:
		return False


# States: 1. Recovered, 2. Positive, 3. Contacted, 4. Neutral, 5. Confirmed Recovery, 6. Confirmed Positive, 7. Confirmed Contact
def confirmPositive(positives):
	for positive in positives:
		if ccm.personExists(positive):  # Change state if person exists
			# retry the write to the database up to 10 times if it fails
			attempt = 1
			while attempt <= 10:
				success = ccm.changeState(positive,6)
				time.sleep(0.1)  # Delay to prevent reaching free tier IBM Cloudant limits
				if success:
					break
				else:
					attempt = attempt + 1
		else:
			# if person not exist, create an unintiated Person with state
			attempt = 1
			while attempt <= 10:
				success = ccm.addPerson(positive,6,"",datetime.datetime.fromisoformat('2011-11-04 00:05:23.283'))
				time.sleep(0.1)  # Delay to prevent reaching free tier IBM Cloudant limits
				if success:
					break
				else:
					attempt = attempt + 1


@app.route('/addHospital',methods=["POST"])
def addHostpital():
	data = request.get_json(force=True)
	if 'ID' not in data or 'AdminPass' not in data:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Improper Request', 400
	ID = data['ID']
	if data['AdminPass'] != creds.addHospitalPass:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Invalid admin password. ', 403
	password = initNewHospital(ID)
	if password == "":
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Already Added. ', 403
	elif password is None:
		return status.HTTP_500_INTERNAL_SERVER_ERROR
	else:
		return jsonify(
			Password = password
		), status.HTTP_201_CREATED


def initNewHospital(ID):
	password = ""
	if not ccm.hospitalExists(ID):
		password = hashlib.sha224((ID+str(os.urandom(128))+creds.salt).encode('utf-8')).hexdigest()
		success = ccm.addHospital(ID,hashlib.sha224(password.encode('utf-8')).hexdigest())  # States: 1. Recovered, 2. Positive, 3. Contacted, 4. Neutral, 5. Confirmed Recovery, 6. Confirmed Positive, 7. Confirmed Contact
		if not success:
			raise cloudant.error.CloudantDatabaseException
	return password


@app.route('/revokeHospital',methods=["POST"])
def revokeHostpital():
	data = request.get_json(force=True)
	if 'ID' not in data or 'AdminPass' not in data:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Improper Request', 400
	ID = data['ID']
	if data['AdminPass'] != creds.rmHospitalPass:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Invalid admin password. ', 403
	ccm.revokeHospital(ID)
	return 'Hospital removed', 202


@app.route('/maintenance',methods=['POST'])
def pauseServer():
	global maintenance
	data = request.get_json(force=True)
	if 'AdminPass' not in data:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Improper Request', 400
	if creds.adminAgent not in request.user_agent.string:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return "Permission Denied",403
	if data['AdminPass'] != creds.adminPass:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)  # 1 strike for suspicious behavior, ip banned if 3 strikes in 15 minutes
		return 'Invalid admin password. ', 403
	if maintenance != True:
		maintenance = True
		return 'Maintenance  mode on', 200
	else:
		maintenance = False
		return 'Maintenance mode off', 200


@app.route('/networkTest', methods=["GET"])
def isHere():
	return "ACK", 200


@atexit.register
def shutdown():
	ccm.cloudantCleanup()


port = int(os.getenv('PORT', 8000))
if __name__ == '__main__':
	app.run(host='0.0.0.0', port=port, debug=False, ssl_context='adhoc')
