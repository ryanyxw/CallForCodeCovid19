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

isMacAddr = re.compile(r"([\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2}:[\da-fA-F]{2})")
isFloodAddr = re.compile("FF:FF:FF:FF:FF:FF",re.I)
OPERATORS = re.compile('SELECT|UPDATE|INSERT|DELETE|\*|OR|=', re.IGNORECASE)

ip_ban_list = ExpiringDict(max_len=50*50000, max_age_seconds=15*60)
mac_ban_list = ExpiringDict(max_len=25*50000, max_age_seconds=15*60)
key_ban_list = ExpiringDict(max_len=25*1230, max_age_seconds=15*60)

ccm.init()

app = flask.Flask(__name__)
@app.before_request
def block_method():
	ip = request.environ.get('REMOTE_ADDR')
	data = request.get_json(force=True)
	if 'Self' in data:
		mac = parseMacAddr(data['Self'][0])
	else:
		mac = None
	if 'Secret' in data:
		secretKey = data['Secret']
	else:
		secretKey = None
	if ip in ip_ban_list.keys():
		if ip_ban_list[ip] >= 3:
			strike(ip,mac,secretKey,1)
			abort(403)
	elif mac in mac_ban_list.keys():
		if mac_ban_list[mac] >= 3:
			strike(ip,mac,secretKey,1)
			abort(403)
	elif secretKey in key_ban_list.keys():
		if key_ban_list[secretKey] >= 3:
			strike(ip,mac,secretKey,1)
			abort(403)
	elif re.search(OPERATORS,repr(mac)+repr(secretKey)) is not None:
		strike(ip,mac,secretKey,3)
		abort(403)
	elif 'COVIDContactTracerApp' not in request.user_agent.string and creds.adminAgent not in request.user_agent.string:
		strike(ip,mac,secretKey,3)
		abort(403)

#  Takes in a POST request with a json object containing a SINGLE MAC address
#  Returns a secret key based on the MAC address and a HTTP Code 201
#  Stores a copy of secret in the local database
@app.route('/InitSelf', methods=["POST"])
def initSelf():
	data = request.get_json(force=True)
	if 'Self' not in data:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)
		return 'Improper Request', 400
	self = data['Self']
	selfList = parseMacAddr(self)
	if not selfList:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)
		return 'Bad MAC Address!', 400
	secret = initNewUser(selfList)
	if secret == "":
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)
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
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)
		return 'Bad MAC Address!', 400
	valid = verifySecret(self[0],secret)
	if valid:
		markPositive(metAddrList, self)
		return jsonify(
			msg = "Get well soon. "
		), status.HTTP_201_CREATED
	else:
		strike(None,self[0],secret,1)
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
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)
		return 'Bad MAC Address!', 400
	if not verifySecret(addrList[0],secret):
		strike(None,addrList[0],secret,1)
		return 'Bad Request Key', 403
	if not passRateLimit(addrList[0]):
		strike(None,addrList[0],secret,1)
		return 'Too many query requests', 429
	state = queryAddr(addrList)
	if state == 1:
		updateRateLimit(addrList[0])
		return jsonify(
			 atRisk = True
			 ), status.HTTP_200_OK
	elif state == 0:
		updateRateLimit(addrList[0])
		return jsonify(
				 atRisk = False
				 ), status.HTTP_200_OK
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
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)
		return 'Improper Request', 400
	self = data['Self']
	secret = data['Secret']
	addr = parseMacAddr(self)
	if not addr:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)
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
		strike(None,addr[0],secret,1)


@app.route('/ForgetMe', methods=["POST"])
def forgetSelf():
	data = request.get_json(force=True)
	if 'Self' not in data or 'Secret' not in data:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)
		return 'Improper Request', 400
	self = data['Self']
	secret = data['Secret']
	addr = parseMacAddr(self)
	if not addr:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)
		return 'Bad MAC Address!', 400
	valid = verifySecret(addr[0],secret)
	if valid:
		deleteUser(addr[0],secret)
		return jsonify(
			msg = "Goodbye. "
		), status.HTTP_201_CREATED
	else:
		strike(request.environ.get('REMOTE_ADDR'),addr[0],secret,1)
		return 'Incorect Secret Key', 403


def initNewUser(selfList):
	addr = selfList[0]
	secret = ""
	time = datetime.datetime.fromisoformat('2011-11-04 00:05:23.283')
	if not ccm.personExists(addr):
		secret = hashlib.sha224((addr+str(os.urandom(128))+creds.salt).encode('utf-8')).hexdigest()
		success = ccm.addPerson(addr,4,secret,time)  # States: 1. Recovered, 2. Positive, 3. Contacted, 4. Neutral
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


def markPositive(addrList, self):
	for positive in addrList:
		if ccm.personExists(positive):  # Change state if person exists
			# retry the write to the database up to 10 times if it fails
			attempt = 1
			while attempt <= 10:
				success = ccm.changeState(positive,3)
				time.sleep(1)  # Delay to prevent reaching free tier IBM Cloudant limits
				if success:
					break
				else:
					attempt = attempt + 1
		else:
			# if person not exist, create an unintiated Person with state
			attempt = 1
			while attempt <= 10:
				success = ccm.addPerson(positive,3,"",datetime.datetime.fromisoformat('2011-11-04 00:05:23.283'))
				time.sleep(1)  # Delay to prevent reaching free tier IBM Cloudant limits
				if success:
					break
				else:
					attempt = attempt + 1

	for positive in self:
		if ccm.personExists(positive):  # Change state if person exists
			# retry the write to the database up to 10 times if it fails
			attempt = 1
			while attempt <= 10:
				success = ccm.changeState(positive,2)
				time.sleep(1)  # Delay to prevent reaching free tier IBM Cloudant limits
				if success:
					break
				else:
					attempt = attempt + 1
		else:
			# if person not exist, create an unintiated Person with state
			attempt = 1
			while attempt <= 10:
				success = ccm.addPerson(positive,2,"",datetime.datetime.fromisoformat('2011-11-04 00:05:23.283'))
				time.sleep(1)  # Delay to prevent reaching free tier IBM Cloudant limits
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
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)
		return "Permission Denied",403
	data = request.get_json(force=True)
	if 'key' not in data:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)
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
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)
		return "Permission Denied",403
	data = request.get_json(force=True)
	if 'key' not in data:
		strike(request.environ.get('REMOTE_ADDR'),None,None,1)
		return "Permission Denied",403
	if data['key'] == creds.resetAuth:
		ip_ban_list = []
		mac_ban_list = []
		key_ban_list = []
		return "Action Completed", 202
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


@atexit.register
def shutdown():
	ccm.cloudantCleanup()


port = int(os.getenv('PORT', 8000))
if __name__ == '__main__':
	app.run(host='0.0.0.0', port=port, debug=False, ssl_context='adhoc')
