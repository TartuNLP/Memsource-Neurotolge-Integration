#!/usr/bin/env python3

import simpleRender as render
import session
import memsource
import neurotolge

from flask import Flask, request

app = Flask('MemSourceMT')

def _login():
	username = request.form['username']
	password = request.form['password']
	
	try:
		token = memsource.login(username, password)
		sessId = session.new(token, username, password)
		return sessId
		
	except Exception as e:
		print("Exception", e)
		
		return False

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

@app.route('/', methods=['POST', 'GET'])
def appRoot():
	sessionId = _tryLoginOrRetrieveSession()
	
	sessionId = _maybeLogout(sessionId)
	
	_maybeStartTranslation(sessionId)
	
	if sessionId:
		return render.filelist(sessionId)
	else:
		try:
			return render.loginForm()
		except Exception as e:
			print(e)
			return "ERR"

@app.route('/list', methods=['POST'])
def appListProj():
	sessionId = int(request.args.get('s'))
	name = request.args.get('n')
	lang = request.args.get('l')
	
	try:
		uid = int(request.args.get('i'))
	except:
		uid = None
	
	token = session.getToken(sessionId)
	
	if uid:
		rawres = [ memsource.getProjectById(token, uid) ]
	else:
		rawRes = memsource.getProjects(token, name = name, targetLang = lang)
	
	#TODO put list in session
	
	#return list
	
@app.route('/prfiles', methods=['POST'])
def appProjFiles():
	sessionId = int(request.args.get('s'))
	projInId = int(request.args.get('p'))
	
	projId = session.getProjId(sessionId, projInId)
	token = session.getToken(sessionId)
	
	fileList = memsource.getProjJobs(token, projId)
	
	#TODO put list in session
	
	#return list

@app.route('/viewfile', methods=['GET', 'POST'])
def appViewFile():
	sessionId = int(request.args.get('s'))
	fileKey = int(request.args.get('fk'))
	
	fille = session.getFileByKey(session.getUser(sessionId), fileKey)
	
	token = fille['token']
	puid = fille['puid']
	fuid = fille['fuid']
	
	return render.showFile(token, puid, fuid)

@app.route('/translatefile', methods=['GET', 'POST'])
def appTranslateFile():
	sessionId = int(request.args.get('s'))
	projUid = request.args.get('puid')
	fileUid = request.args.get('fuid')
	res = neurotolge.translateXml(sessionId, projUid, fileUid)
	return res

if __name__ == '__main__':
	app.run(port=80, host='193.40.154.224')
