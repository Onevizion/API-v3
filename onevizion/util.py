import urllib
import os
import json
import base64
from datetime import datetime, date
import onevizion

HTTPS = "https://"
HTTP = "http://"
ParameterExample = """Parameter File required.  Example:
{
	"SMTP": {
		"UserName": "mgreene@onevizion.com",
		"Password": "IFIAJKAFJBJnfeN",
		"Server": "mail.onevizion.com",
		"Port": "587",
		"Security": "STARTTLS",
		"From": "mgreene@onevizion.com",
		"To":['jsmith@onevizion.com','mjones@onevizion.com'],
		"CC":['bbrown@xyz.com','eric.goete@xyz.com']
	},
	"trackor.onevizion.com": {
		"url": "trackor.onevizion.com",
		"UserName": "mgreene",
		"Password": "YUGALWDGWGYD"
	},
	"sftp.onevizion.com": {
		"UserName": "mgreene",
		"Root": ".",
		"Host": "ftp.onevizion.com",
		"KeyFile": "~/.ssh/ovftp.rsa",
		"Password": "Jkajbebfkajbfka"
	},
}"""
PasswordExample = ParameterExample

def Message(Msg,Level=0):
	"""Prints a message depending on the verbosity level set on the command line"""
	if Level <= onevizion.Config["Verbosity"]:
		print (Msg)

def TraceMessage(Msg,Level=0,TraceTag=None):
	if TraceTag is None:
		Tag = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')
	else:
		Tag = TraceTag
	Message(Msg,Level)
	onevizion.Config["Trace"][Tag]=Msg


def getUrlContainingScheme(url):
	if not url:
		return ""

	return url if url.lower().startswith((HTTP, HTTPS)) else HTTPS + url

def GetPasswords(passwordFile=None):
	return GetParameters(passwordFile)

def GetParameters(parameterFile=None):
	if parameterFile is None:
		parameterFile = onevizion.Config["ParameterFile"]
	if not os.path.exists(parameterFile):
		print (ParameterExample)
		quit()

	with open(parameterFile,"rb") as ParameterFile:
		ParameterData = json.load(ParameterFile)
	onevizion.Config["ParameterData"] = ParameterData
	onevizion.Config["ParameterFile"] = parameterFile

	return ParameterData

def CheckPasswords(PasswordData,TokenName,KeyList, OptionalList=[]):
	return CheckParameters(PasswordData,TokenName,KeyList, OptionalList)

def CheckParameters(ParameterData,TokenName,KeyList, OptionalList=[]):
	Missing = False
	msg = ''
	if TokenName not in ParameterData:
		Missing = True
	else:
		for key in KeyList:
			if key not in ParameterData[TokenName]:
				Missing = True
				break
	if Missing:
		msg = "Parameters.json section required:\n"
		msg = msg + "\t'%s': {" % TokenName
		for key in KeyList:
			msg = msg + "\t\t'%s': 'xxxxxx',\n" % key
		if len(OptionalList) > 0:
			msg = msg + "\t\t'  optional parameters below  ':''"
			for key in OptionalList:
				msg = msg + "\t\t'%s': 'xxxxxx',\n" % key
		msg = msg.rstrip('\r\n')[:-1] + "\n\t}"

	return msg


def URLEncode(strToEncode):
	if strToEncode is None:
		return ""
	else:
		try:
			from urllib.parse import quote_plus
		except Exception as e:
			from urllib import quote_plus

		return quote_plus(strToEncode)



def JSONEncode(strToEncode):
	if strToEncode is None:
		return ""
	else:
		return strToEncode.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\b', '\\b').replace('\t', '\\t').replace('\f', '\\f')


def JSONValue(strToEncode):
	if strToEncode is None:
		return 'null'
	elif isinstance(strToEncode, (int, float, complex)):
		return str(strToEncode)
	else:
		return '"'+JSONEncode(strToEncode)+'"'

def JSONEndValue(objToEncode):
	if objToEncode is None:
		return None
	elif isinstance(objToEncode, (int, float)):
		return objToEncode
	elif isinstance(objToEncode, datetime):
		return objToEncode.strftime('%Y-%m-%dT%H:%M:%S')
	elif isinstance(objToEncode, date):
		return objToEncode.strftime('%Y-%m-%d')
	else:
		return str(objToEncode)

def EFileEncode(FilePath,NewFileName=None):
	if NewFileName is None:
		FileName = os.path.basename(FilePath)
	else:
		FileName = NewFileName
	File={"file_name": FileName}
	with open(FilePath,"rb") as f:
		EncodedFile = base64.b64encode(f.read())

	#python3 compatibility
	if isinstance(EncodedFile, bytes):
	   File["data"]=EncodedFile.decode()
	else:
	   File["data"]=EncodedFile

	return File
