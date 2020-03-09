import session
import neurotolge
import memsource
import html

from flask import request

langDesc = { 'et': 'eesti', 'lv': 'läti', 'lt': 'leedu', 'ru_ru': 'vene' }

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

def _filelistHeader():
	return """<h1>Interlex'i masintõlge</h1>
	<p style="width:800px;text-align:left">Siin saab käivitada masintõlget valitud tööde jaoks. Pärast masintõlkimise lõpetamist saavad failid tagasi MemSource'i üles laetud, kusjuures tühjad väljundiväljad saavad masintõlke väljundiga eeltäidetud.</p>"""

def _memsourceFiles(sessionId):
	res = "<h2>Memsource projektid/failid</h2>"
	
	user = session.getUser(sessionId)
	token = session.getToken(sessionId)
	
	projects = memsource.getProjects(token)
	
	res += """<form action="/?s={0}" method="post">""".format(sessionId)
	
	res += """<table border="0" width="800px">"""
	
	for p in projects['content']:
		#res += "<p style=\"text-align:left;width:800px\"><b>Projekt: " + p['name'] + "</b></p>"
		print("PROJ LOG", p)
		
		#if owner == 'InterlexPM':
		if True:
			fl = memsource.getProjJobs(token, p['uid'])
			
			for f in fl['content']:
				print("JOB LOG", f)
				inId = session.internalFileId(sessionId, p['uid'], f['uid'], [f, p])
				
				if not session.getFileBySKey(sessionId, inId)['mt']:
					res += "<tr><td width=\"50px\"><input type=\"checkbox\" name=\"cb" + str(inId) + "\"/></td>"
					tgtLang = f['targetLang']
					if tgtLang in langDesc:	
						tgtLang = langDesc[tgtLang]
					res += "<td><b>" + str(p['internalId']) + "/" +  p['name'] + "</b>/" + f['filename'] + " (" + tgtLang + "&nbsp;keelde)</td>"
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
	
	res += _filelistHeader()
	
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
