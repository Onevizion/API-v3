import requests
import json
from onevizion.util import *
from onevizion.curl import curl
from onevizion.integration.loglevel import LogLevel
from onevizion.httpbearer import HTTPBearerAuth
import onevizion

class IntegrationLog(object):
	"""Wrapper for adding logs to the OneVizion.

	Attributes:
		processId: the system processId
		URL: A string representing the website's main URL for instance "trackor.onevizion.com".
		userName: the username or the OneVizion API Security Token Access Key that is used to login to the system
		password: the password or the OneVizion API Security Token Secret Key that is used to gain access to the system
		logLevel: log level name (Info, Warning, Error, Debug) for logging integration actions

	Exception can be thrown for method 'add'
	"""

	def __init__(self, processId, URL="", userName="", password="", paramToken=None, isTokenAuth=False, logLevelName="Error"):
		self._URL = URL
		self._userName = userName
		self._password = password
		self._processId = processId

		if paramToken is not None:
			if self._URL == "":
				self._URL = onevizion.Config["ParameterData"][paramToken]['url']
			if self._userName == "":
				self._userName = onevizion.Config["ParameterData"][paramToken]['UserName']
			if self._password == "":
				self._password = onevizion.Config["ParameterData"][paramToken]['Password']

		self._URL = getUrlContainingScheme(self._URL)

		if isTokenAuth:
			self._auth = HTTPBearerAuth(self._userName, self._password)
		else:
			self._auth = requests.auth.HTTPBasicAuth(self._userName, self._password)

		self._ovLogLevel = LogLevel.getLogLevelByName(logLevelName)
 

	def add(self, logLevel, message, description=""):
		if logLevel.logLevelId <= self._ovLogLevel.logLevelId:
			parameters = {'message': message, 'description': description, 'log_level_name': logLevel.logLevelName}
			jsonData = json.dumps(parameters)
			headers = {'content-type': 'application/json'}
			url_log = "{URL}/api/v3/integrations/runs/{ProcessID}/logs".format(URL=self._URL, ProcessID=self._processId)
			OVCall = curl('POST', url_log, data=jsonData, headers=headers, auth=self._auth)
			if len(OVCall.errors) > 0:
				raise Exception(OVCall.errors)
			return OVCall.jsonData
