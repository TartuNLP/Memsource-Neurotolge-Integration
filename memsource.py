import requests
import json

baseurl = 'https://cloud.memsource.com/web/api2/v1/'

def memsrc(shorturl, data = None, jdata = None, log = False, get = False, put = False, skipjson = False):
    url = baseurl + shorturl
    
    f = requests.get if get else requests.put if put else requests.post
    x = f(url, data = data, json = jdata)
    
    if log:
        print(url, data, jdata, f, x)
    
    try:
        if skipjson:
            return x.text
        else:
            return json.loads(x.text)
    except json.JSONDecodeError as e:
        print("Exc", e)
        return None

def login(user, password):
    res = memsrc('auth/login', jdata = { 'userName': user, 'password': password })
    return res['token']

def logout(token):
    memsrc('auth/logout?token=' + token)

def getProjectById(token, uid):
    res = memsrc("projects/{0}?token={1}".format(uid, token), get = True)
    return res

def getProjects(token, name = '', pageSize = 10):
    projlist = memsrc("projects?token={0}&name={1}&pageSize={2}".format(token, name, pageSize), get = True)
    return projlist

def getProjJobs(token, projUid):
    filelist = memsrc("projects/{0}/jobs?token={1}".format(projUid, token), get = True)
    return filelist

def getFileContent(token, projUid, fileUid):
    content = memsrc("projects/{0}/jobs/bilingualFile?token={1}".format(projUid, token), jdata = { 'jobs': [ {'uid': fileUid}] }, skipjson = True)
    return content

def putFileContent(token, newContent):
    res = memsrc("bilingualFiles?token={0}".format(token), data = newContent.encode('utf8'), put = True)
    return res
