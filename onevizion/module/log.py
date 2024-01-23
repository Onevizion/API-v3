import requests
import json
# "deprecated" has been used since version 3.13.
from warnings import warn
from onevizion.util import *
from onevizion.curl import curl
from onevizion.module.loglevel import LogLevel
from onevizion.httpbearer import HTTPBearerAuth
import onevizion


class ModuleLog(object):
	"""Wrapper for adding logs to the OneVizion.

	Attributes:
		processId: the system processId
		URL: A string representing the website's main URL for instance "trackor.onevizion.com".
		userName: the username or the OneVizion API Security Token Access Key that is used to login to the system
		password: the password or the OneVizion API Security Token Secret Key that is used to gain access to the system
		logLevel: log level name (Info, Warning, Error, Debug) for logging module actions

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
			url_log = "{URL}/api/v3/modules/runs/{ProcessID}/logs".format(URL=self._URL, ProcessID=self._processId)
			OVCall = curl('POST', url_log, data=jsonData, headers=headers, auth=self._auth)
			if len(OVCall.errors) > 0:
				raise Exception(OVCall.errors)
			return OVCall.jsonData


# deprecated has been used since version 3.13
# @deprecated("Use ModuleLog instead")
class IntegrationLog(object):
	"""Wrapper for adding logs to the OneVizion.
	
	This class is deprecated. Use ModuleLog instead.
	"""

	def __init__(self, processId, URL="", userName="", password="", paramToken=None, isTokenAuth=False, logLevelName="Error"):
		"""This throws a deprecation warning on initialization."""
		warn(f'{self.__class__.__name__} is deprecated. Use ModuleLog instead.', DeprecationWarning, stacklevel=2)

		self._module_log = ModuleLog(processId, URL, userName, password, paramToken, isTokenAuth, logLevelName)
 

	def add(self, logLevel, message, description=""):
		self._module_log.add(logLevel, message, description)