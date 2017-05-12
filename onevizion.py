import requests
import urllib
import json
import smtplib
import os
import datetime
from collections import OrderedDict


class curl(object):
	"""Wrapper for requests.request() that will handle Error trapping and try to give JSON for calling.
	If URL is passed on Instantiation, it will automatically run, else, it will wait for you to set 
	properties, then run it with runQuery() command.  Erors should be trapped and put into "errors" array.
	If JSON is returned, it will be put into "data" as per json.loads

	Attributes:
		method: GET, PUT, POST, PATCH, DELETE methods for HTTP call
		url: URL to send the request
		**kwargs:  any other arguments to send to the request
	"""

	def __init__(self, method='GET', url=None, **kwargs):
		self.method = method
		self.url = url
		self.params = None
		self.data = None
		self.headers = None
		self.cookies = None
		self.files = None
		self.auth = None
		self.timeout = None
		self.allow_redirects = True
		self.proxies = None
		self.hooks = None
		self.stream = None
		self.verify = None
		self.cert = None
		self.json = None
		self.request = None
		self.errors = []
		self.jsonData = {}
		self.args = {}
		self.duration = None
		for key, value in kwargs.items():
			self.args[key] = value
			setattr(self, key, value)

		if self.url is not None:
			self.runQuery()



	def setArg(self, key, value):
		if value is not None:
			self.args[key] = value

	def runQuery(self):
		self.setArg('params', self.params)
		self.setArg('data', self.data)
		self.setArg('headers', self.headers)
		self.setArg('cookies', self.cookies)
		self.setArg('files', self.files)
		self.setArg('auth', self.auth)
		self.setArg('timeout', self.timeout)
		self.setArg('allow_redirects', self.allow_redirects)
		self.setArg('proxies', self.proxies)
		self.setArg('hooks', self.hooks)
		self.setArg('stream', self.stream)
		self.setArg('verify', self.verify)
		self.setArg('cert', self.cert)
		self.setArg('json', self.json)

		self.errors = []
		self.jsonData = {}
		before = datetime.datetime.utcnow()
		try:
			self.request = requests.request(self.method, self.url, **self.args)
		except Exception as e:
			self.errors.append(str(e))
		else:
			if self.request.status_code not in range(200,300):
				self.errors.append(str(self.request.status_code)+" = "+self.request.reason+"\n"+str(self.request.text))
			try:
				self.jsonData = json.loads(self.request.text)
			except Exception as err:
				pass
		after = datetime.datetime.utcnow()
		delta = after - before
		self.duration = delta.total_seconds()



class OVImport(object):
	"""Wrapper for calling FireTrackor Imports.  We have the
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

	def __init__(self, URL=None, userName=None, password=None, impSpecId=None, file=None, action='INSERT_UPDATE', comments=None, incremental=None):
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

		# If all info is filled out, go ahead and run the query.
		if URL != None and userName != None and password != None and impSpecId != None and file != None:
			self.makeCall()

	def makeCall(self):
		self.ImportURL = "https://" + self.userName + ":" + self.password + "@" + self.URL + "/configimport/SubmitUrlImport.do"
		self.ImportParameters = {'impSpecId': self.impSpecId,'action': self.action}
		if self.comments is not None:
			self.ImportParameters['comments'] = self.comments
		if self.incremental is not None:
			self.ImportParameters['isIncremental'] = self.incremental
		self.ImportFile = {'file': open(self.file,'rb')}
		self.curl = curl('POST',self.ImportURL,files=self.ImportFile,data=self.ImportParameters)
		if len(self.curl.errors) > 0:
			self.errors.append(self.curl.errors)
		elif "userMessages" in self.jsonData and len(self.jsonData["userMessages"]) > 0:
			self.errors.append(self.jsonData["userMessages"])
		else:
			self.processId = self.curl.jsonData["processId"]
		self.request = self.curl.request
		self.jsonData = self.jsonData




class Trackor(object):
	"""Wrapper for calling the FireTrackor API for Trackors.  You can Delete, Read, Update or Create new
		Trackor instances with the like named methods.

	Attributes:
		trackorType: The name of the TrackorType being changed.
		URL: A string representing the website's main URL for instance "trackor.onevizion.com".
		userName: the username used to login to the system
		password: the password used to gain access to the system

		errors: array of any errors encounterd
		OVCall: the requests object of call to the web api
		jsonData: the json data converted to python array
	"""

	def __init__(self, trackorType = "", URL = "", userName="", password=""):
		self.TrackorType = trackorType
		self.URL = URL
		self.UserName = userName
		self.password = password
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl()
		self.request = None



	def delete(self,trackorId):
		""" Delete a Trackor instance.  Must pass a trackorId, the unique DB number.
		"""
		FilterSection = "trackor_id=" + str(trackorId)

		URL = "https://%s:%s@%s/api/v3/trackor_types/%s/trackors?%s" % (self.UserName, self.password, self.URL, self.TrackorType, FilterSection)
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('DELETE',URL)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

	def read(self, 
		trackorId=None, 
		filterOptions=None, 
		filters={}, 
		viewOptions=None, 
		fields=[],
		sort={},
		page=None,
		perPage=1000
		):
		""" Retrieve some field data from a set of Trackor instances. List of Trackors must be 
			identified either by trackorId or filterOptions, and data fields to be retieved must be
			identified either by viewOptions or a list of fields.
			
			fields is an array of strings that are teh Configured Field Names.
		"""
		
		ViewSection = ""
		if viewOptions is None:
			ViewSection = 'fields=' + ",".join(fields)
		else:
			ViewSection = 'view=' + URLEncode(viewOptions)

		FilterSection = ""
		if trackorId is None:
			if filterOptions is None:
				for key,value in filters.items():
					FilterSection = FilterSection + key + '=' + URLEncode(str(value)) + '&'
				FilterSection = FilterSection.rstrip('?&')
			else:
				FilterSection = "filter="+URLEncode(filterOptions)
		else: 
			FilterSection = "trackor_id=" + str(trackorId)

		SortSection=""
		for key,value in sort.items():
			SortSection=SortSection+","+key+":"+value
		if len(SortSection)>0:
			SortSection="&sort="+URLEncode(SortSection.lstrip(','))

		PageSection=""
		if page is not None:
			PageSection = "&page="+str(page)+"&per_page="+str(perPage)


		URL = "https://%s:%s@%s/api/v3/trackor_types/%s/trackors?%s&%s%s%s" % (
			self.UserName, 
			self.password, 
			self.URL, 
			self.TrackorType, 
			FilterSection, 
			ViewSection,
			SortSection,
			PageSection
			)
		self.OVCall = curl('GET',URL)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		self.jsonData = self.OVCall.jsonData


	def update(self, filters={}, fields={}, parents={}, charset=""):
		""" Update data in a list of fields for a Trackor instance.
			"filters" is a list of ConfigFieldName:value pairs that finds the unique 
				Trackor instance to be updated.  Use "TrackorType.ConfigFieldName" to filter
				with parent fields.
			"fields" is a ConfigFieldName:Value pair for what to update.  The Value can either
				be a string, or a dictionary of key:value pairs for parts fo teh field sto be updated
				such as in and EFile field, one can have {"file_name":"name.txt","data":"Base64Encoded Text"}
			"parents" is a list of TrackorType:Filter pairs.
				"Filter" is a list of ConfigFieldName:value exactly like the about "filters"
		"""

		# First build a JSON package from the fields and parents dictionaries given
		JSONObj = {}

		FieldsSection = {}
		for key, value in fields.items():
			if isinstance(value, dict):
				CompundField = {}
				for skey,svalue in value.items():
					CompundField[skey] = svalue
				FieldsSection[key] = CompoundField
			else:
				FieldsSection[key] = value

		ParentsSection = {}
		for key, value in parents.items():
			ParentsSection["trackor_type"] = key
			FilterPart = {}
			for fkey,fvalue in value.items():
				FilterPart[fkey]=fvalue
			ParentsSection["filter"] = FilterPart

		JSONObj["fields"] = FieldsSection
		JSONObj["parents"] = ParentsSection
		JSON = json.dumps(JSONObj)

		# Build up the filter to find the unique Tackor instance
		Filter = '?'
		for key,value in filters.items():
			Filter = Filter + key + '=' + URLEncode(str(value)) + '&'
		Filter = Filter.rstrip('?&')

		URL = "https://%s:%s@%s/api/v3/trackor_types/%s/trackor%s" % (self.UserName, self.password, self.URL, self.TrackorType, Filter)
		#payload = open('temp_payload.json','rb')
		Headers = {'content-type': 'application/x-www-form-urlencoded'}
		if charset != "":
			Headers['charset'] = charset
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('PUT',URL, data=JSON, headers=Headers)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		self.jsonData = self.OVCall.jsonData


	def create(self,fields={},parents={}, charset=""):
		""" Create a new Trackor instance and set some ConfigField and Parent values for it.
			"filters" is a list of ConfigFieldName:value pairs that finds the unique 
				Trackor instance to be updated.  Use "TrackorType.ConfigFieldName" to filter
				with parent fields.
			"fields" is a ConfigFieldName:Value pair for what to update.  The Value can either
				be a string, or a dictionary of key:value pairs for parts fo teh field sto be updated
				such as in and EFile field, one can have {"file_name":"name.txt","data":"Base64Encoded Text"}
			"parents" is a list of TrackorType:Filter pairs.
				"Filter" is a list of ConfigFieldName:value pairs that finds the unique 
					Trackor instance to be updated.  Use "TrackorType.ConfigFieldName" to filter
					with parent fields.
		"""

		# First build a JSON package from the fields and parents dictionaries given
		JSONObj = {}

		FieldsSection = {}
		for key, value in fields.items():
			if isinstance(value, dict):
				CompundField = {}
				for skey,svalue in value.items():
					CompundField[skey] = svalue
				FieldsSection[key] = CompoundField
			else:
				FieldsSection[key] = value

		ParentsSection = {}
		for key, value in parents.items():
			ParentsSection["trackor_type"] = key
			FilterPart = {}
			for fkey,fvalue in value.items():
				FilterPart[fkey]=fvalue
			ParentsSection["filter"] = FilterPart

		JSONObj["fields"] = FieldsSection
		JSONObj["parents"] = ParentsSection
		JSON = json.dumps(JSONObj)

		URL = "https://%s:%s@%s/api/v3/trackor_types/%s/trackor" % (self.UserName, self.password, self.URL, self.TrackorType)
		#payload = open('temp_payload.json','rb')
		Headers = {'content-type': 'application/json'}
		if charset != "":
			Headers['charset'] = charset
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('POST',URL, data=JSON, headers=Headers)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		self.jsonData = self.OVCall.jsonData



class WorkPlan(object):
	"""Wrapper for calling the FireTrackor API for WorkPlans.  You can Read or Update 
		WorkPlan instances with the like named methods.

	Attributes:
		URL: A string representing the website's main URL for instance "trackor.onevizion.com".
		userName: the username used to login to the system
		password: the password used to gain access to the system

		errors: array of any errors encounterd
		OVCall: the requests object of call to the web api
		jsonData: the json data converted to python array
	"""

	def __init__(self, URL = "", userName="", password=""):
		self.URL = URL
		self.UserName = userName
		self.password = password
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl()

	def read(self, workplanId = None, workplanTemplate = "", trackorType = "", trackorId = None):
		""" Retrieve some data about a particular WorkPlan.WorkPlan must be 
			identified either by workplanId or by a WorkPlanTemplate, TrackorType, and TrackorID
		"""
		FilterSection = ""
		if workplanId is None:
			#?wp_template=Augment%20Workplan&trackor_type=SAR&trackor_id=1234
			FilterSection = "?wp_template=%s&trackor_type=%s&trackor_id=%d" % (
				URLEncode(workplanTemplate),
				URLEncode(trackorType),
				trackorId
				)
		else:
			#1234
			FilterSection = str(trackorId)

		URL = "https://%s:%s@%s/api/v3/wps/%s" % (self.UserName, self.password, self.URL, FilterSection)
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('GET',URL)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		self.jsonData = self.OVCall.jsonData


class Task(object):

	def __init__(self, URL = "", userName="", password=""):
		self.URL = URL
		self.UserName = userName
		self.password = password
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl()

	def read(self, taskId = None, workplanId=None, orderNumber=None):
		""" Retrieve some data about a particular WorkPlan Tasks. Tasks must be 
			identified either by workplanId, workplanId and orderNumber or by a taskId
		"""
		if taskId is not None:
			URL = "https://%s:%s@%s/api/v3/tasks/%d" % (self.UserName, self.password, self.URL, taskId)
		elif orderNumber is not None:
			URL = "https://%s:%s@%s/api/v3/tasks?workplan_id=%d&order_number=%d" % (self.UserName, self.password, self.URL, workplanId, orderNumber)
		else:
			URL = "https://%s:%s@%s/api/v3/wps/%d/tasks" % (self.UserName, self.password, self.URL, workplanId)

		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('GET',URL)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		self.jsonData = self.OVCall.jsonData


	def update(self, taskId, fields={}, dynamicDates=[]):

		if len(dynamicDates)>0:
			fields['dynamic_dates'] = dynamicDates

		JSON = json.dumps(fields)

		URL = "https://%s:%s@%s/api/v3/tasks/%d" % (self.UserName, self.password, self.URL, taskId)
		#payload = open('temp_payload.json','rb')
		Headers = {'content-type': 'application/x-www-form-urlencoded'}
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('PUT',URL, data=JSON, headers=Headers)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		self.jsonData = self.OVCall.jsonData


class Import(object):

	def __init__(
		self, 
		URL=None, 
		userName=None, 
		password=None, 
		impSpecId=None, 
		file=None, 
		action='INSERT_UPDATE', 
		comments=None, 
		incremental=None
		):
		self.URL = URL
		self.userName = userName
		self.password = password
		self.impSpecId = impSpecId
		self.file = file
		self.action = action
		self.comments = comments
		self.incremental = incremental
		self.errors = []
		self.warnings = []
		self.request = {}
		self.jsonData = {}
		self.processId = None
		self.status = None
		self.processList = []

		# If all info is filled out, go ahead and run the query.
		if URL != None and userName != None and password != None and impSpecId != None and file != None:
			self.run()

	def run(self):
		self.ImportURL = "https://%s:%s@%s/api/v3/imports/%d/run?action=%s"%(
			self.userName,
			self.password,
			self.URL,
			self.impSpecId,
			self.action
			)
		if self.comments is not None:
			self.ImportURL += '&comments=' + URLEncode(self.comments)
		if self.incremental is not None:
			self.ImportURL += '&is_incremental=' + str(self.incremental)
		self.ImportFile = {'file': open(self.file,'rb')}
		self.OVCall = curl('POST',self.ImportURL,files=self.ImportFile)
		self.request = self.OVCall.request
		self.jsonData = self.OVCall.jsonData
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		else:
			if "error_message" in self.jsonData and len(self.jsonData["error_message"]) > 0:
				self.errors.append(self.jsonData["error_message"])
			if "warnings" in self.jsonData and len(self.jsonData["warnings"]) > 0:
				self.warnings.extend(self.jsonData["warnings"])
			if "process_id" in self.jsonData:
				self.processId = self.jsonData["process_id"]
				self.status = self.jsonData["status"]

	def interrupt(self,ProcessID=None):
		if ProcessID is None:
			PID = self.processId
		else:
			PID = ProcessID
		self.ImportURL = "https://%s:%s@%s/api/v3/imports/runs/%d/interrupt"%(
			self.userName,
			self.password,
			self.URL,
			PID
			)
		self.OVCall = curl('POST',self.ImportURL)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		else:
			self.processId = PID
		self.request = self.OVCall.request
		self.jsonData = self.OVCall.jsonData
		if "status" in self.jsonData:
			self.status = self.jsonData['status']

	def getProcessData(self,
		processId=None,
		status=None,
		comments=None,
		importName=None,
		owner=None,
		isPdf=None
		):
		def addParam(paramName,param):
			if param is not None:
				if not self.ImportURL.endswith("?"):
					self.ImportURL += "&"
				self.ImportURL += paramName + "=" +URLEncode(str(param))

		self.ImportURL = "https://%s:%s@%s/api/v3/imports/runs"%(
			self.userName,
			self.password,
			self.URL
			)
		if status is not None or comments is not None or importName is not None or owner is not None or isPdf is not None:
			self.ImportURL += "?"
			if status is not None:
				self.ImportURL += "status="
				if type(status) is list:
					self.ImportURL += ",".join(status)
				else:
					self.ImportURL += str(status)
			addParam('comments',comments)
			addParam('import_name',importName)
			addParam('owner',owner)
			addParam('is_pdf',comments)
		else:
			if processId is None:
				self.ImportURL += "/"+str(self.processId)
			else:
				self.ImportURL += "/"+str(processId)

		self.OVCall = curl('GET',self.ImportURL)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		else:
			pass
		self.request = self.OVCall.request
		self.jsonData = self.OVCall.jsonData
		if "status" in self.jsonData:
			self.status = self.jsonData['status']
		else:
			self.status = 'No Status'
		return self.jsonData






class Export(object):

	def __init__(
		self, 
		URL=None, 
		userName=None, 
		password=None, 
		trackorType=None,
		filters={},
		fields=[],
		exportMode="CSV",
		delivery="File",
		viewOptions=None,
		filterOptions=None,
		fileFields=None,
		comments=None
		):
		self.URL = URL
		self.userName = userName
		self.password = password
		self.trackorType = trackorType
		self.exportMode = exportMode
		self.delivery = delivery
		self.comments = comments
		self.filters = filters
		self.fields = fields
		self.viewOptions = viewOptions
		self.filterOptions = filterOptions
		self.fileFields = fileFields
		self.errors = []
		self.request = {}
		self.jsonData = {}
		self.status = None
		self.processId = None
		self.processList = []
		self.content = None

		# If all info is filled out, go ahead and run the query.
		if URL is not None and userName is not None and password is not None and trackorType is not None and (viewOptions is not None or len(fields)>0 or fileFields is not None) and (filterOptions is not None or len(filters)>0):
			self.run()

	def run(self):
		self.ImportURL = "https://%s:%s@%s/api/v3/exports/%s/run?export_mode=%s&delivery=%s"%(
			self.userName,
			self.password,
			self.URL,
			self.trackorType,
			self.exportMode,
			self.delivery
			)

		ViewSection = ""
		if self.viewOptions is None:
			ViewSection = '&fields=' + ",".join(self.fields)
		else:
			ViewSection = '&view=' + URLEncode(self.viewOptions)
		self.ImportURL += ViewSection

		FilterSection = "&"
		if self.filterOptions is None:
			for key,value in self.filters.items():
				FilterSection += key + '=' + URLEncode(str(value)) + '&'
			FilterSection = FilterSection.rstrip('?&')
		else:
			FilterSection = "&filter="+URLEncode(self.filterOptions)
		self.ImportURL += FilterSection

		if self.comments is not None:
			self.ImportURL += '&comments=' + URLEncode(self.comments)
		self.OVCall = curl('POST',self.ImportURL)
		self.request = self.OVCall.request
		self.jsonData = self.OVCall.jsonData
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		else:
			if "error_message" in self.jsonData and len(self.jsonData["error_message"]) > 0:
				self.errors.append(self.jsonData["error_message"])
			if "warnings" in self.jsonData and len(self.jsonData["warnings"]) > 0:
				self.warnings.extend(self.jsonData["warnings"])
			if "process_id" in self.jsonData:
				self.processId = self.jsonData["process_id"]
			if "status" in self.jsonData:
				self.status = self.jsonData["status"]
		return self.processId

	def interrupt(self,ProcessID=None):
		if ProcessID is None:
			PID = self.processId
		else:
			PID = ProcessID
		self.ImportURL = "https://%s:%s@%s/api/v3/exports/runs/%d/interrupt"%(
			self.userName,
			self.password,
			self.URL
			)
		self.OVCall = curl('POST',self.ImportURL)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		else:
			self.processId = PID
		self.request = self.OVCall.request
		self.jsonData = self.OVCall.jsonData
		if "status" in self.jsonData:
			self.status = self.jsonData['status']

	def getProcessStatus(self,ProcessID=None):
		if ProcessID is None:
			PID = self.processId
		else:
			PID = ProcessID
		self.ImportURL = "https://%s:%s@%s/api/v3/exports/runs/%d"%(
			self.userName,
			self.password,
			self.URL,
			PID
			)
		self.OVCall = curl('GET',self.ImportURL)
		self.request = self.OVCall.request
		self.jsonData = self.OVCall.jsonData
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		if "status" in self.jsonData:
			self.status = self.jsonData['status']
		else:
			self.status = 'No Status'
		return self.status

	def getFile(self,ProcessID=None):
		if ProcessID is None:
			PID = self.processId
		else:
			PID = ProcessID
		self.ImportURL = "https://%s:%s@%s/api/v3/exports/runs/%d/file"%(
			self.userName,
			self.password,
			self.URL,
			PID
			)
		print self.ImportURL
		self.OVCall = curl('GET',self.ImportURL)
		self.request = self.OVCall.request
		self.jsonData = self.OVCall.jsonData
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
		else:
			self.content = self.request.content
		return self.content







class EMail(object):
	"""Made to simplify sending Email notifications in scripts.
	
	Attributes:
		server: the SSL SMTP server for the mail connection
		port: the port to conenct to- 465 by default
		tls: True if TLS is needed, else false.
		userName: the "From" and login to the SMTP server
		password: the password to conenct to the SMTP server
		to: array of email addresses to send the message to
		subject: subject of the message
		info: dictionary of inof to send in the message
		message: main message to send
		files: array of filename/paths to attach
	"""

	def __init__(self,SMTP={}):
		self.server = "mail.onevizion.com"
		self.port = 465
		self.tls = "False"
		self.userName = ""
		self.password = ""
		self.to = []
		self.cc = []
		self.subject = ""
		self.info = OrderedDict()
		self.message = ""
		self.body = ""
		self.files = []
		self.duration = 0
		if 'UserName' in SMTP and 'Password' in SMTP and 'Server' in SMTP:
			self.passwordData(SMTP)

	def passwordData(self,SMTP={}):
		if 'UserName' not in SMTP or 'Password' not in SMTP or 'Server' not in SMTP:
			raise ("UserName,Password,and Server are required in the PasswordData json")
		else:
			self.server = SMTP['Server']
			self.userName = SMTP['UserName']
			self.password = SMTP['Password']
		if 'Port' in SMTP:
			self.port = int(SMTP['Port'])
		if 'TLS' in SMTP:
			self.tls = SMTP['TLS']
		if 'To' in SMTP:
			if type(SMTP['To']) is list:
				self.to.extend(SMTP['To'])
			else:
				self.to.append(SMTP['To'])
		if 'CC' in SMTP:
			if type(SMTP['CC']) is list:
				self.cc.extend(SMTP['CC'])
			else:
				self.cc.append(SMTP['CC'])


	def sendmail(self):
		import mimetypes

		from optparse import OptionParser

		from email import encoders
		from email.message import Message
		from email.mime.audio import MIMEAudio
		from email.mime.base import MIMEBase
		from email.mime.image import MIMEImage
		from email.mime.multipart import MIMEMultipart
		from email.mime.text import MIMEText
		msg = MIMEMultipart()
		msg['To'] = ", ".join(self.to )
		msg['From'] = self.userName
		msg['Subject'] = self.subject

		body = self.message + "\n"

		for key,value in self.info.items():
			body = body + "\n\n" + key + ":"
			svalue = str(value)
			if "\n" in svalue:
				body = body + "\n" + svalue
			else:
				body = body + " " + svalue
		self.body = body
		
		part = MIMEText(body, 'plain')
		msg.attach(part)

		for file in self.files:
			ctype, encoding = mimetypes.guess_type(file)
			if ctype is None or encoding is not None:
				# No guess could be made, or the file is encoded (compressed), so
				# use a generic bag-of-bits type.
				ctype = 'application/octet-stream'
			maintype, subtype = ctype.split('/', 1)
			if maintype == 'text':
				fp = open(file)
				# Note: we should handle calculating the charset
				attachment = MIMEText(fp.read(), _subtype=subtype)
				fp.close()
			elif maintype == 'image':
				fp = open(file, 'rb')
				attachment = MIMEImage(fp.read(), _subtype=subtype)
				fp.close()
			elif maintype == 'audio':
				fp = open(file, 'rb')
				attachment = MIMEAudio(fp.read(), _subtype=subtype)
				fp.close()
			else:
				fp = open(file, 'rb')
				attachment = MIMEBase(maintype, subtype)
				attachment.set_payload(fp.read())
				fp.close()
				# Encode the payload using Base64
				encoders.encode_base64(attachment)
			# Set the filename parameter
			attachment.add_header('Content-Disposition', 'attachment', filename=file)
			msg.attach(attachment)



		before = datetime.datetime.utcnow()

		
		if self.tls in [True,1,"1","True","TRUE","true","yes","Yes","YES"]:
			send = smtplib.SMTP(self.server, int(self.port))
			#send.ehlo()
			send.starttls()
			#send.ehlo()
		else:
			send = smtplib.SMTP_SSL(self.server, self.port)
		send.login(str(self.userName), str(self.password))
		send.sendmail(str(self.userName),self.to, msg.as_string())
		send.quit()

		after = datetime.datetime.utcnow()
		delta = after - before
		self.duration = delta.total_seconds()


PasswordExample = """Password File required.  Example:
{
	"SMTP": {
		"UserName": "mgreene@onevizion.com",
		"Password": "IFIAJKAFJBJnfeN",
		"Server": "mail.onevizion.com",
		"Port": "465"
	},
	"trackor.onevizion.com": {
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



def GetPasswords(passwordFile):
	if not os.path.exists(passwordFile):
		print PasswordExample
		quit()

	with open(passwordFile,"rb") as PasswordFile:
		PasswordData = json.load(PasswordFile)
	return PasswordData

def CheckPasswords(PasswordData,TokenName,KeyList, OptionalList=[]):
	Missing = False
	msg = ''
	if TokenName not in PasswordData:
		Missing = True
	else:
		for key in KeyList:
			if key not in PasswordData[TokenName]:
				Missing = True
				break
	if Missing:
		msg = "Passwords.json section required:\n"
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



