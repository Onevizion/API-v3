"""Utility functions for the OneVizion API wrapper.

This module provides common utility functions used across the OneVizion package:
    - URL encoding and JSON encoding helpers
    - Message and trace logging functions
    - Parameter file loading and validation
    - EFile (base64) encoding for file fields
    - Python 2/3 compatibility helpers

Functions:
    - Message(): Print messages based on verbosity level
    - TraceMessage(): Log messages to global trace dictionary
    - URLEncode(): URL-encode strings for query parameters
    - JSONEncode() / JSONEndValue(): Encode values for JSON payloads
    - GetParameters(): Load parameters from JSON file
    - CheckParameters(): Validate required parameter keys
    - EFileEncode(): Base64-encode files for EFile fields
    - LogErrorToTrace(): Centralized error logging helper
    - getUrlContainingScheme(): Ensure URL has http:// or https://
    - utcnow(): Python 2.7-compatible UTC datetime

Example:
    >>> from onevizion.util import URLEncode, Message
    >>> encoded = URLEncode("name with spaces")
    >>> print(encoded)  # "name+with+spaces"
    >>>
    >>> import onevizion
    >>> onevizion.Config["Verbosity"] = 2
    >>> Message("Debug info", Level=2)  # Prints if Verbosity >= 2
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import base64
import json
import os
import sys
from datetime import date, datetime

import onevizion

HTTPS = "https://"
HTTP = "http://"


def utcnow():
	"""Get current UTC time in a Python 2.7 compatible way.

	Returns datetime.datetime in UTC. Uses datetime.utcnow() for Python 2.7
	compatibility, even though it's deprecated in Python 3.12+.

	Returns:
		datetime: Current datetime in UTC

	Note:
		In Python 3.12+, datetime.utcnow() is deprecated in favor of
		datetime.now(UTC), but we must maintain Python 2.7 compatibility.
	"""
	# Python 2.7 doesn't have timezone.utc, so we use utcnow() for compatibility
	# Suppress the deprecation warning in Python 3.12+ since we need Py2.7 support
	import warnings
	with warnings.catch_warnings():
		warnings.filterwarnings("ignore", category=DeprecationWarning)
		return datetime.utcnow()


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
		Tag = utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f')
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

	with open(parameterFile,"r") as ParameterFile:
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
	try:
		from urllib.parse import quote_plus
	except Exception:
		from urllib import quote_plus

	return quote_plus(strToEncode)



def JSONEncode(strToEncode):
	if strToEncode is None:
		return ""
	return strToEncode.replace('\\', '\\\\').replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r').replace('\b', '\\b').replace('\t', '\\t').replace('\f', '\\f')


def JSONValue(strToEncode):
	if strToEncode is None:
		return 'null'
	if isinstance(strToEncode, (int, float, complex)):
		return str(strToEncode)
	return '"'+JSONEncode(strToEncode)+'"'

def JSONEndValue(objToEncode):
	if objToEncode is None:
		return None
	if isinstance(objToEncode, (int, float)):
		return objToEncode
	if isinstance(objToEncode, datetime):
		return objToEncode.strftime('%Y-%m-%dT%H:%M:%S')
	if isinstance(objToEncode, date):
		return objToEncode.strftime('%Y-%m-%d')
	return str(objToEncode)

def EFileEncode(FilePath,NewFileName=None):
	if NewFileName is None:
		FileName = os.path.basename(FilePath)
	else:
		FileName = NewFileName
	File={"file_name": FileName}
	with open(FilePath,"rb") as f:
		EncodedFile = base64.b64encode(f.read())

	#python3 compatibility - in Python 3, b64encode returns bytes, in Python 2 it returns str
	if sys.version_info[0] >= 3:
		File["data"]=EncodedFile.decode()
	else:
		File["data"]=EncodedFile

	return File


def LogErrorToTrace(ov_call, url, trace_tag_prefix="", post_body=None, extra_data=None):
	"""Log API call errors to the global trace and error flags.

	This helper function consolidates the duplicated error handling pattern
	used throughout the API wrapper classes. It logs error details to the
	global Config["Trace"] dictionary and sets the Config["Error"] flag.

	Args:
		ov_call: The curl instance with request/error information
		url: The URL that was called
		trace_tag_prefix: Optional prefix for the trace tag (default: timestamp)
		post_body: Optional POST body to include in trace
		extra_data: Optional dict of extra data to log (e.g., {"FileName": "test.csv"})

	Returns:
		str: The TraceTag that was used for logging

	Example:
		>>> trace_tag = LogErrorToTrace(self.OVCall, url, post_body={"fields": {...}})
	"""
	import onevizion

	if trace_tag_prefix:
		TraceTag = trace_tag_prefix
	else:
		TraceTag = "{TimeStamp}:".format(TimeStamp=utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))

	onevizion.Config["Trace"][TraceTag + "-URL"] = url

	if post_body is not None:
		import json
		onevizion.Config["Trace"][TraceTag + "-PostBody"] = json.dumps(post_body, indent=2)

	if extra_data is not None:
		for key, value in extra_data.items():
			onevizion.Config["Trace"][TraceTag + "-" + key] = value

	try:
		TraceMessage("Status Code: {StatusCode}".format(StatusCode=ov_call.request.status_code), 0, TraceTag + "-StatusCode")
		TraceMessage("Reason: {Reason}".format(Reason=ov_call.request.reason), 0, TraceTag + "-Reason")
		TraceMessage("Body:\n{Body}".format(Body=ov_call.request.text), 0, TraceTag + "-Body")
	except Exception:
		import json
		TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(ov_call.errors, indent=2)), 0, TraceTag + "-Errors")

	onevizion.Config["Error"] = True

	return TraceTag
