import session
import neurotolge
import enginespecs
import memsource
import html
from datetime import datetime

from flask import request

langDesc = { 'et': 'eesti', 'lv': 'läti', 'lt': 'leedu', 'ru_ru': 'vene', 'ru': 'vene', 'de': 'saksa', 'fi': 'soome', 'en': 'inglise' }

shortenLang = { 'est': 'et', 'eng': 'en', 'lit': 'lt', 'lav': 'lv', 'rus': 'ru', 'ger': 'de', 'deu': 'de', 'fin': 'fi' }

def _sanitize(inputString):
	if inputString:
		return html.escape(inputString)
	else:
		return inputString

def _start():
	return """<html><body><center>"""

def _end():
	return """</center></body></html>"""

def _logoutPara(sessionId):
	return """<p><a href="/?s=-{0}">Logi välja</a></p>""".format(sessionId)

def _beautifulEngineName(engineName):
	if engineName == 'tt':
		return 'TT'
	else:
		return engineName.capitalize()

def _translationEngineSelect(sessionId):
	username = session.retrieveValue(sessionId, 'username')
	
	selectedEngine = session.retrieveValue(sessionId, 'translator')
	
	engines = list(enginespecs.userExtraEngineAccess[username])
	
	if len(engines) == 1:
		return engines[0] + """<input type="hidden" name="translator" value="{0}"/>""".format(engines[0])
	else:
		res = """<select name="translator" id="translator" onchange="fltform.submit()">"""
		
		for engine in engines:
			selectedText = " selected=\"y\"" if engine == selectedEngine else ""
			
			res += """<option value="{0}"{1}>{2}</option>""".format(engine, selectedText, _beautifulEngineName(engine))
		
		res += "</select>"
		
		return res

def _maybeRenderDomainSelect(sessionId):
	selectedEngine = session.retrieveValue(sessionId, 'translator')
	
	selectedDomain = session.retrieveValue(sessionId, 'domain')
	spec = session.retrieveValue(sessionId, 'engineSpec')
	availDomains = spec['domains'] if spec and 'domains' in spec else None
	
	if availDomains and selectedDomain:
		res = """<p>Tekstivaldkond: <select name="domain" id="domain" onchange="fltform.submit()">"""
		
		for dom in availDomains:
			domCode = dom['code']
			domName = dom['name']
			selTxt = " selected=\"y\"" if domCode == selectedDomain else ""
			
			res += """<option value="{0}"{1}>{2}</option>""".format(domCode, selTxt, domName)
			
		res += "</select></p>"
		return res
	else:
		return ""

def _filelistHeader(sessionId):
	return """<h1>MemSource ja Neurot&otilde;lke integratsioon</h1>
		<p style="width:800px;text-align:left">Siin
		saab käivitada masintõlget valitud tööde jaoks.
		Pärast masintõlkimise lõpetamist saavad failid
		tagasi MemSource'i üles laetud, kusjuures tühjad
		väljundiväljad saavad masintõlke väljundiga eeltäidetud.</p>
	
		<form id="fltform" action="/?s={0}" method="post">
	
		<p>T&otilde;lkemootor: {1}</p>
		{2}
		""".format(sessionId, _translationEngineSelect(sessionId), _maybeRenderDomainSelect(sessionId))

def getDomLangs(engineSpec, domain):
	if not engineSpec or not domain:
		return None, None
	
	dommap = { dom['code']: dom for dom in engineSpec['domains'] }
	
	srcTgtLangsRaw = zip(*[lp.split('-') for lp in dommap[domain]['languages']])
	
	return [list(set([shortenLang[l] for l in ldef])) for ldef in srcTgtLangsRaw]

def _langunion(allowed, proj):
	return list(set(allowed) & set(proj))

def _memsourceFiles(sessionId):
	res = "<h2>Memsource projektid/failid</h2>"
	
	user = session.getUser(sessionId)
	token = session.getToken(sessionId)
	
	textProjFilter = session.retrieveValue(sessionId, 'textProjFilter') or ""
	numProjFilter = session.retrieveValue(sessionId, 'numProjFilter') or ""
	
	currEngineSpec = session.retrieveValue(sessionId, 'engineSpec')
	currDom = session.retrieveValue(sessionId, 'domain')
	
	#print("DDDDBBBBGGGG", currEngineSpec, currDom)
	allowedSrcLangs, allowedTgtLangs = getDomLangs(currEngineSpec, currDom)
	print(allowedSrcLangs, "--", allowedTgtLangs)
	
	res += """<p><input type="hidden" name="reqtyp" value="filter"/>
		<input type="hidden" name="numProjFilter" value=""/>
		<input type="text" id="textProjFilter" name="textProjFilter" value="{1}" size="90"
		   placeholder="filtreeri projekti nime j&auml;rgi"/>
		<input type="submit" value="Filtreeri" name="filterButton"/>
		</p></form>""".format(numProjFilter, textProjFilter)
	
	projects = memsource.getProjects(token, name = textProjFilter, numflt = numProjFilter, srcLangs = allowedSrcLangs, tgtLangs = allowedTgtLangs)
	#print("DEBUUGGGGG", len(projects['content']))
	
	res += """<form action="/?s={0}" method="post"><input type="hidden" name="reqtyp" value="translate"/>""".format(sessionId)
	
	res += """<table border="0" width="800px">"""
	
	for p in sorted(projects['content'], key=lambda x: x['internalId']):
		srcLang = p['sourceLang']
		if srcLang in langDesc:
			srcLang = langDesc[srcLang]
		
		jobList = []
		
		if allowedTgtLangs:
			for tgtLang in _langunion(allowedTgtLangs, p['targetLangs']):
				fl = memsource.getProjJobs(token, p['uid'], urlext = '&targetLang=' + tgtLang)
				jobList += fl['content']
		else:
			fl = memsource.getProjJobs(token, p['uid'])
			jobList = fl['content']
		
		for f in jobList:
			#print("JOB LOG", f)
			inId = session.internalFileId(sessionId, p['uid'], f['uid'], [f, p])
			
			if not session.getFileBySKey(sessionId, inId)['mt']:
				res += "<tr><td width=\"50px\"><input type=\"checkbox\" name=\"cb" + str(inId) + "\"/></td>"
				tgtLang = f['targetLang']
				if tgtLang in langDesc:	
					tgtLang = langDesc[tgtLang]
				res += "<td><b>" + str(p['internalId']) + "/" +  p['name'] + "</b>/" + f['filename'] + " (" + srcLang + "&rarr;" + tgtLang + ")</td>"
				#res += "<td width=\"1\"><a href=\"/viewfile?s={0}&fk={1}\">(MXLF)</a></td>".format(sessionId, inId)
	
	res += """</table><input type="submit" value="Tõlgi" name="mtbutton"/></form>"""
	
	return res

def _translatingFiles(sessionId):
	res = "<h2>Masintõlgitavad failid</h2>"
	
	try:
		res += """<table border="0" width="800px">"""
		
		user = session.getUser(sessionId)
		
		for fileId in set(session.bgfiles[user].keys()) - {'map'}:
			f = session.bgfiles[user][fileId]
			if f['mt']:
				filename = f['msInfo'][1]['name'] + "/" + f['msInfo'][0]['filename']
				status = neurotolge.fileStatus(f)
				res += "<tr><td>{0} ({1})</td></tr>".format(filename, status)
			
		res += "</table>"
	except:
		res += "ajutine tõrge"
	
	return res

def _finalButtons(sessionId):
	return """<p><a href="/?s={0}">Värskenda</a></p>""".format(sessionId) + _logoutPara(sessionId)

def filelist(sessionId):
	res = _start()
	
	res += _filelistHeader(sessionId)
	
	res += _memsourceFiles(sessionId)
	
	res += _translatingFiles(sessionId)
	
	res += _finalButtons(sessionId)
	
	res += _end()
	
	return res

def _loginForm(failed, prevUser, prevPass):
	return """<p style="padding-top:200px">{0}</p>
	<form action="/" method="post">
	<table border="0" width="400px">
	<tr><td width="400px">
		<input placeholder="Kasutajanimi" type="text" name="username" style="width:100%" value="{1}"/>
	</td></tr>
	<tr><td width="400px">
		<input placeholder="Salas&otilde;na" type="password" name="password" style="width:100%" value="{2}"/>
	</td></tr>
	<tr><td colspan="2" align="center">
		<input type="submit" value="Sisse!" name="loginbtn""/>
	</td></tr>
	</table>
	</form>""".format("Sisselogimine ei õnnestunud, proovige uuesti" if failed else "Sisenege oma Memsource kasutajakontosse", prevUser, prevPass)

def loginForm():
	try:
		prevUser = _sanitize(request.form['username'])
		prevPass = _sanitize(request.form['password'])
	except:
		prevUser = ""
		prevPass = ""
	
	failed = prevUser or prevPass
	
	return _start() + _loginForm(failed, prevUser, prevPass) + _end()

def showFile(token, projectUid, fileUid):
	content = memsource.getFileContent(token, projectUid, fileUid)
	#return "<html><body><pre>" + html.escape(content) + "</pre></body></html>"
	return content
