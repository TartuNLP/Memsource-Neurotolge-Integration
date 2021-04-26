import memsource
import re
import session
import html
import requests
import xml.dom.minidom as dom
import multiprocessing as mp

from urllib.parse import quote
from datetime import datetime

from enginespecs import engines, userExtraEngineAccess

# very old API:
#rawResponse = requests.post("https://api.neurotolge.ee/v1.1/translate?auth={0}&conf={1}&src={2}".format(authToken, outLang, "|".join(inputs)))
#rawResult = rawResponse.json()['tgt'].split("|")

#######################

def _requestV20(passcode, text = None, outLang = None, inLang = None, dom = None):
	"""
	communicate with TartuNLP API via protocol v2.0
	"""
	authHeaders = { 'x-api-key': passcode, 'application': 'memsource' }
	
	url = "https://api.tartunlp.ai/translation/v2"
	
	if (text and outLang):
		jsonData = { 'text': text, 'tgt': outLang }
		
		if inLang:
			jsonData['src'] = inLang
		if dom:
			jsonData['domain'] = dom
		
		reqMethod = requests.post
	else:
		jsonData = None
		
		reqMethod = requests.get
	
	#print("DEBUG", reqMethod, jsonData, authHeaders)
	raw = reqMethod(url, headers = authHeaders, json = jsonData)
	
	try:
		return raw.json()
	except Exception as e:
		print(raw)
		raise e

#######################

def _requestV12(passcode, text = None, outLang = None):
	"""
	communicate with TartuNLP API via protocol v1.2
	"""
	
	if (text and outLang):
		jsonData = { 'text': text }
		url = "https://api.tartunlp.ai/v1.2/translate?auth={0}&olang={1}".format(passcode, outLang)
		reqMethod = requests.post
	else:
		jsonData = None
		url = "https://api.tartunlp.ai/v1.2/translate/support?auth={0}".format(passcode)
		reqMethod = requests.get
	
	#print("DEBUG", reqMethod, jsonData, url)
	raw = reqMethod(url, json = jsonData)
	
	try:
		return raw.json()
	except Exception as e:
		print(raw)
		raise e

def _request(engineId, text = None, outLang = None, inLang = None, domain = None):
	passcode, useOld = engines[engineId]
	
	return _requestV12(passcode, text, outLang) if useOld else _requestV20(passcode, text, outLang, inLang, domain)

def getEngineSpec(engineId):
	spec = _request(engineId)
	
	try:
		#just so that the exception is thrown
		_ = spec['domains']
		
		return spec
	except KeyError:
		#THIS IS AN UGLY HACK
		#FIXME
		#the KeyError is raised for v1.2 engines that return domains in a different format
		#however, currently the 3 engines with v1.2 have no domain choice, while
		#both v2 engines have multiple domains -- so, currently this function only returns
		#correct domains for v2 engines and None for v1.2
		 
		#how to fix -- either eventually and soon all our engines will be v2, or if there is a
		#multi-domain v1.2 engine then the format has to be checked and this code updated
		return None

def _elem2txt(elem):
	return html.unescape(elem.toxml())[8:-9]

def _getInputSnts(content):
	doc = dom.parseString(content)
	
	outLang = doc.getElementsByTagName('file')[0].getAttribute('target-language')
	
	inLang = doc.getElementsByTagName('file')[0].getAttribute('source-language')
	
	#return { _elem2txt(e) for e in doc.getElementsByTagName('source') }, outLang
	
	res = set()
	
	for tu in doc.getElementsByTagName('trans-unit'):
		tgtNodes = [t for t in tu.childNodes if t.localName == 'target']
		
		assert(len(tgtNodes) == 1)
		
		if not tgtNodes[0].hasChildNodes():
			src = _elem2txt(tu.getElementsByTagName('source')[0])
			res.add(src)
	
	return res, outLang, inLang

def _batches(data, size):
	start = 0
	end = size
	
	while end < len(data):
		yield data[start:end]
		start = end
		end = start + size
	
	end = len(data)
	if end > start:
		yield data[start:end]

def _translateBatches(translatorEngine, inputs, outLang, user, fileId, batchSize = 8, inLang = None, dom = None):
	inputList = list(inputs)
	translations = []
	
	for b in _batches(inputList, batchSize):
		bt = _translate(translatorEngine, b, outLang, inLang, dom)
		translations += bt
		session.bgfiles[user][fileId]['numDone'] = len(translations)
	
	return dict(zip(inputList, translations))

def _fixTags(translation):
	# fix broken tags: replace '{2 > silte < 2}' with '{2>silte<2}'
	tmpRes = re.sub(r'{\s*([0-9biu])\s*>\s*', r'{\1>', translation)
	res = re.sub(r'\s*<\s*([0-9biu])\s*}', r'<\1}', tmpRes)
	return res

def _fixTagsList(translList):
	#print("AAAADdEBUG", translList)
	
	return [_fixTags(x) for x in translList]

def _translate(translatorEngine, inputSet, outLang, inLang = None, domain = None):
	inputs = list(inputSet)
	
	#text = "|".join(inputs)
	text = inputs
	
	assert (outLang in ('et', 'lv', 'lt', 'de', 'en', 'fi', 'ru'))
	
	authToken, useOldAPI = engines[translatorEngine]
	
	print("\ntranslating", translatorEngine, outLang, inLang, domain, text, datetime.now())
	
	try:
		if useOldAPI:
			response = _requestV12(authToken, text, outLang)
		else:
			response = _requestV20(authToken, text, outLang, inLang, domain)
			
		rawResult = response['result']
	except KeyError:
		rawResult = ''
	
	print("translated:", translatorEngine, rawResult, datetime.now())
	
	translations = _fixTagsList(rawResult)
	
	#return dict(zip(inputs, translations))
	return translations

def _fillTranslations(oldContent, trDict, userId):
	doc = dom.parseString(oldContent)
	
	for tu in doc.getElementsByTagName('trans-unit'):
		src = _elem2txt(tu.getElementsByTagName('source')[0])
		
		if src in trDict:
			transl = trDict[src]
			
			tgtNodesX = [t for t in tu.getElementsByTagName('target') if t.parentNode.getAttribute('origin') == "machine-trans"]
			
			assert(len(tgtNodesX) == 1)
			
			if not tgtNodesX[0].hasChildNodes():
				#print("ADDED ALT")
				tgtNodesX[0].appendChild(doc.createTextNode(transl))
			
			tgtNodes = [t for t in tu.childNodes if t.localName == 'target']
			
			assert(len(tgtNodes) == 1)
			
			if not tgtNodes[0].hasChildNodes():
				tgtNodes[0].appendChild(doc.createTextNode(transl))
				tu.setAttribute('m:trans-origin', "mt")
				tu.setAttribute('m:created-by', str(userId))
				tu.setAttribute('m:modified-by', str(userId))
				epoch = str(int(datetime.now().timestamp()))
				tu.setAttribute('m:created-at', epoch)
				tu.setAttribute('m:modified-at', epoch)
	
	return doc.toxml()

def translateFileOnBg(sessionId, fileId):
	f = session.getFileBySKey(sessionId, fileId)
	
	f['mt'] = True
	user = session.getUser(sessionId)
	translator = session.retrieveValue(sessionId, 'translator')
	domain = session.retrieveValue(sessionId, 'domain')
	
	#this should be impossible to do, but for extra security:
	if not translator in set(userExtraEngineAccess[user]):
		raise Exception("AAA, what do we do: " + str(translator) + ", " + str(userExtraEngineAccess[user]) + ".")
	
	p = mp.Process(target=translateXml, args=[user, translator, domain, fileId])
	p.start()
	
def translateXml(user, translatorEngine, domain, fileId):
	fileInfo = session.getFileByKey(user, fileId)
	
	token = fileInfo['token']
	puid = fileInfo['puid']
	fuid = fileInfo['fuid']
	
	d0 = datetime.now()
	content = memsource.getFileContent(token, puid, fuid)
	
	d1 = datetime.now()
	inputSet, outLang, inLang = _getInputSnts(content)
	
	session.bgfiles[user][fileId]['numToTranslate'] = len(inputSet)
	session.bgfiles[user][fileId]['numDone'] = 0
	
	d2 = datetime.now()
	trDict = _translateBatches(translatorEngine, inputSet, outLang, user, fileId, inLang = inLang, dom = domain)
	#print("DEBUGGGGGX", trDict)
	
	d3 = datetime.now()
	newContent = _fillTranslations(content, trDict, session.bgfiles[user][fileId]['msInfo'][1]['owner']['id'])
	#print("DEBUGGGGG", newContent)
	
	d4 = datetime.now()
	
	r = memsource.putFileContent(token, newContent)
	print("DONE, {0} / {1}".format(len(trDict), d3 - d2))
	#print(newContent)
	
	session.bgfiles[user][fileId]['done'] = True

def fileStatus(fields):
	if fields['done']:
		return 'valmis!'
	elif fields['numToTranslate']:
		return "{0} / {1} segmendi tõlgitud".format(fields['numDone'], fields['numToTranslate'])
	else:
		return "käivitamas"
