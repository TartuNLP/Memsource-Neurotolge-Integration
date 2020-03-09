import memsource
import session
import json
import html
import requests
import xml.dom.minidom as dom
import multiprocessing as mp

from urllib.parse import quote
from datetime import datetime

def _elem2txt(elem):
	return html.unescape(elem.toxml())[8:-9]

def _getInputSnts(content):
	doc = dom.parseString(content)
	
	outLang = doc.getElementsByTagName('file')[0].getAttribute('target-language')
	
	#return { _elem2txt(e) for e in doc.getElementsByTagName('source') }, outLang
	
	res = set()
	
	for tu in doc.getElementsByTagName('trans-unit'):
		tgtNodes = [t for t in tu.childNodes if t.localName == 'target']
		
		assert(len(tgtNodes) == 1)
		
		if not tgtNodes[0].hasChildNodes():
			src = _elem2txt(tu.getElementsByTagName('source')[0])
			res.add(src)
	
	return res, outLang

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

def _translateBatches(inputs, outLang, user, fileId, batchSize = 16):
	inputList = list(inputs)
	translations = []
	
	for b in _batches(inputList, batchSize):
		bt = _translate(b, outLang)
		translations += bt
		session.bgfiles[user][fileId]['numDone'] = len(translations)
	
	return dict(zip(inputList, translations))

def _translate(inputSet, outLang):
	inputs = list(inputSet)
	
	text = "|".join(inputs)
	
	assert (outLang in ('et', 'lv', 'lt'))
	
	print("\ntranslating", outLang, text, datetime.now())
	rawRes = requests.post("https://api.neurotolge.ee/v1.1/translate", data = {'auth': 'affinephoneearsinterlex', 'conf': outLang, 'src': text })
	print("translated:", rawRes.text, datetime.now())
	
	jsonRes = json.loads(rawRes.text)
	
	translations = jsonRes['tgt'].split("|")
	
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
				print("ADDED ALT")
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
	
	p = mp.Process(target=translateXml, args=[user, fileId])
	p.start()
	
#def translateXml(sessionId, puid, fuid):
def translateXml(user, fileId):	
	fileInfo = session.getFileByKey(user, fileId)
	
	token = fileInfo['token']
	puid = fileInfo['puid']
	fuid = fileInfo['fuid']
	
	d0 = datetime.now()
	content = memsource.getFileContent(token, puid, fuid)
	
	d1 = datetime.now()
	inputSet, outLang = _getInputSnts(content)
	
	session.bgfiles[user][fileId]['numToTranslate'] = len(inputSet)
	session.bgfiles[user][fileId]['numDone'] = 0
	
	d2 = datetime.now()
	trDict = _translateBatches(inputSet, outLang, user, fileId)
	
	d3 = datetime.now()
	newContent = _fillTranslations(content, trDict, session.bgfiles[user][fileId]['msInfo'][1]['owner']['id'])
	
	d4 = datetime.now()
	
	r = memsource.putFileContent(token, newContent)
	print("DONE, {0} / {1} / {2}".format(len(trDict), d3 - d2, r))
	#print(newContent)
	
	session.bgfiles[user][fileId]['done'] = True

def fileStatus(fields):
	if fields['done']:
		return 'valmis!'
	elif fields['numToTranslate']:
		return "{0} / {1} segmendi tõlgitud".format(fields['numDone'], fields['numToTranslate'])
	else:
		return "käivitamas"
