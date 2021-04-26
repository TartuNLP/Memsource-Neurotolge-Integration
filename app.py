#!/usr/bin/env python3

import simpleRender as render
import session
import memsource
import neurotolge
import enginespecs

from flask import Flask, request

app = Flask('MemSourceMT')

###################################
######## Handling requests ########
###################################

@app.route('/', methods=['POST', 'GET'])
def appRoot():
	sessionId = _tryLoginOrRetrieveSession()
	
	sessionId = _maybeLogout(sessionId)
	
	_maybeStartTranslation(sessionId)
	
	_maybeStoreParams(sessionId)
	
	if sessionId:
		return render.filelist(sessionId)
	else:
		try:
			return render.loginForm()
		except Exception as e:
			print(e)
			return "ERR"

@app.route('/viewfile', methods=['GET', 'POST'])
def appViewFile():
	sessionId = int(request.args.get('s'))
	fileKey = int(request.args.get('fk'))
	
	fille = session.getFileByKey(session.getUser(sessionId), fileKey)
	
	token = fille['token']
	puid = fille['puid']
	fuid = fille['fuid']
	
	return render.showFile(token, puid, fuid)

#@app.route('/translatefile', methods=['GET', 'POST'])
#def appTranslateFile():
#	sessionId = int(request.args.get('s'))
#	projUid = request.args.get('puid')
#	fileUid = request.args.get('fuid')
#	res = neurotolge.translateXml(sessionId, projUid, fileUid)
#	return res

###################################
######## Helper functions #########
###################################

def _login():
	username = request.form['username']
	password = request.form['password']
	
	#try:
	token = memsource.login(username, password)
	sessId = session.new(token, username, password)
	
	engines = list(enginespecs.userExtraEngineAccess[username])
	session.storeValue(sessId, 'translator', engines[0])
	_reloadDomains(engines[0], sessId)
	
	return sessId
		
	#except Exception as e:
	#	print("ExceptionXXX", e)
	#	
	#	return False

def _currSession():
	raws = request.args.get('s')
	
	s = int(raws) if raws else None
	
	if s in session.sessions:
		return s
	else:
		return None

def _tryLoginOrRetrieveSession():
	if ('username' in request.form and 'password' in request.form):
		sessionId = _login()
	else:
		sessionId = _currSession()
	
	return sessionId

def _maybeLogout(sessionId):
	#logout request is signalled by passing the session ID multiplied by -1
	if sessionId is not None and sessionId < 0:
		memsource.logout(session.getToken(-sessionId))
		
		return False
	else:
		return sessionId

def _maybeStartTranslation(sessionId):
	if sessionId and 'mtbutton' in request.form:
		for k in request.form:
			if k.startswith('cb'):
				inid = int(k[2:])
				neurotolge.translateFileOnBg(sessionId, inid)

def _reloadDomains(engineId, sessionId):
	spec = neurotolge.getEngineSpec(engineId)
	domains = spec['domains'] if spec and 'domains' in spec else None
	
	session.storeValue(sessionId, 'engineSpec', spec)
	
	if domains:
		session.storeValue(sessionId, 'domain', domains[0]['code'])
	else:
		session.storeValue(sessionId, 'domain', None)

def _maybeStoreParams(sessionId):
	if sessionId and 'reqtyp' in request.form and request.form['reqtyp'] == 'filter':
		oldTr = session.retrieveValue(sessionId, 'translator')
		
		for k, v in request.form.items():
			if k not in { 'reqtyp', 'filterButton' }:
				session.storeValue(sessionId, k, v)
		
		newTr = session.retrieveValue(sessionId, 'translator')
		if oldTr != newTr:
			_reloadDomains(newTr, sessionId)

###################################
########### Start app #############
###################################

if __name__ == '__main__':
	app.run(port=80, host='193.40.154.224')
