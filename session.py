from random import randint
from multiprocessing import Process, Manager

man = Manager()
sessions = man.dict() # sessionId -> {token, username, pass}

bgfiles = man.dict()

def genNewSessionId():
	result = randint(0, 100000)
	
	while result in sessions:
		result = randint(0, 100000)
	
	return result

def new(msToken, username, password):
	newSessionId = genNewSessionId()
	
	sessions[newSessionId] = man.dict({ 'token': msToken, 'username': username, 'password': password })
	print(len(sessions))
	return newSessionId

def getToken(sessionId):
	return sessions[sessionId]['token']

def getUser(sessionId):
	return sessions[sessionId]['username']

def getPass(sessionId):
	return sessions[sessionId]['password']

def _newFileEntry(inId, projUid, fileUid, token, content):
	return man.dict({
		'inid': inId,
		'puid': projUid,
		'fuid': fileUid,
		'token': token,
		'mt': False,
		'done': False,
		'content': None,
		'numToTranslate': None,
		'numDone': None,
		'msInfo': content
		})

def _fileKeyFromUids(puid, fuid):
	return puid + "+" + fuid

def _getFileByUids(user, puid, fuid):
	key = _fileKeyFromUids(puid, fuid)
	inid = bgfiles[user]['map'][key]
	return bgfiles[user][inid]

def internalFileId(sessionId, projUid, fileUid, fileContent):
	user = getUser(sessionId)
	token = getToken(sessionId)
	
	fileKey = _fileKeyFromUids(projUid, fileUid)
	
	if user in bgfiles:
		if fileKey in bgfiles[user]['map']:
			return bgfiles[user]['map'][fileKey]
		else:
			newId = len(bgfiles[user]) + 1
			bgfiles[user][newId] = _newFileEntry(newId, projUid, fileUid, token, fileContent)
			bgfiles[user]['map'][fileKey] = newId
			
			return newId
	else:
		bgfiles[user] = man.dict({ 1: _newFileEntry(1, projUid, fileUid, token, fileContent), 'map': man.dict({fileKey: 1}) })
		return 1

def getFileByKey(user, key):
	return bgfiles[user][key]

def getFileBySKey(sessionId, key):
	user = getUser(sessionId)
	return getFileByKey(user, key)
