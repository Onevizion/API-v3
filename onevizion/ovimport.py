import onevizion
from onevizion.Import import Import

class OVImport(object):
	"""Wrapper for calling OneVizion Imports.  We have the
	following properties:

	Attributes:
		URL: A string representing the website's main URL for instance "trackor.onevizion.com".
		userName: the username used to login to the system
		password: the password used to gain access to the system
		impSpecId: the numeric identifier for the Import this file is to be applied to
		action: "INSERT_UPDATE", "INSERT", or "UPDATE"
		comments: Comments to add tot the Import
		incemental: Optional value to pass to incremental import parameter
		file: the path and file name of the file to be imported

		errors: array of any errors encounterd
		request: the requests object of call to the web api
		data: the json data converted to python array
		processId: the system processId returned from the API call
	"""

	def __init__(self, URL=None, userName=None, password=None, impSpecId=None, file=None, action='INSERT_UPDATE', comments=None, incremental=None, paramToken=None, isTokenAuth=False):
		self.URL = URL
		self.userName = userName
		self.password = password
		self.impSpecId = impSpecId
		self.file = file
		self.action = action
		self.comments = comments
		self.incremental = incremental
		self.errors = []
		self.request = {}
		self.jsonData = {}
		self.processId = None
		self.isTokenAuth = isTokenAuth

		if paramToken is not None:
			if self.URL is None:
				self.URL = onevizion.Config["ParameterData"][paramToken]['url']
			if self.userName is None:
				self.userName = onevizion.Config["ParameterData"][paramToken]['UserName']
			if self.password is None:
				self.password = onevizion.Config["ParameterData"][paramToken]['Password']

		# If all info is filled out, go ahead and run the query.
		if self.URL != None and self.userName != None and self.password != None and self.impSpecId != None and self.file != None:
			self.makeCall()

	def makeCall(self):

		self.Import = Import(
			URL=self.URL,
			userName=self.userName,
			password=self.password,
			impSpecId=self.impSpecId,
			file=self.file,
			action=self.action,
			comments=self.comments,
			incremental=self.incremental,
			isTokenAuth=self.isTokenAuth
			)
		self.errors = self.Import.errors
		if len(self.Import.errors) == 0:
			self.request = self.Import.request
			self.jsonData = self.Import.jsonData
			self.processId = self.Import.processId
