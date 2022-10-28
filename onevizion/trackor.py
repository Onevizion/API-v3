import requests
import json
from datetime import datetime
from onevizion.util import *
from onevizion.curl import curl
from onevizion.httpbearer import HTTPBearerAuth
from onevizion.EMail import EMail
import onevizion

class Trackor(object):
	"""Wrapper for calling the Onvizion API for Trackors.  You can Delete, Read, Update or Create new
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

	def __init__(self, trackorType = "", URL = "", userName="", password="", paramToken=None, isTokenAuth=False):
		self.TrackorType = trackorType
		self.URL = URL
		self.userName = userName
		self.password = password
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl()
		self.request = None

		if paramToken is not None:
			if self.URL == "":
				self.URL = onevizion.Config["ParameterData"][paramToken]['url']
			if self.userName == "":
				self.userName = onevizion.Config["ParameterData"][paramToken]['UserName']
			if self.password == "":
				self.password = onevizion.Config["ParameterData"][paramToken]['Password']

		self.URL = getUrlContainingScheme(self.URL)

		if isTokenAuth:
			self.auth = HTTPBearerAuth(self.userName, self.password)
		else:
			self.auth = requests.auth.HTTPBasicAuth(self.userName, self.password)

	def delete(self,trackorId):
		""" Delete a Trackor instance.  Must pass a trackorId, the unique DB number.
		"""
		FilterSection = "trackor_id=" + str(trackorId)

		URL = "{URL}/api/v3/trackor_types/{TrackorType}/trackors?{FilterSection}".format(URL=self.URL, TrackorType=self.TrackorType, FilterSection=FilterSection)
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('DELETE',URL,auth=self.auth)
		Message(URL,2)
		Message("Deletes completed in {Duration} seconds.".format(Duration=self.OVCall.duration),1)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
			TraceTag="{TimeStamp}:".format(TimeStamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
			self.TraceTag = TraceTag
			onevizion.Config["Trace"][TraceTag+"-URL"] =  URL
			try:
				TraceMessage("Status Code: {StatusCode}".format(StatusCode=self.OVCall.request.status_code),0,TraceTag+"-StatusCode")
				TraceMessage("Reason: {Reason}".format(Reason=self.OVCall.request.reason),0,TraceTag+"-Reason")
				TraceMessage("Body:\n{Body}".format(Body=self.OVCall.request.text),0,TraceTag+"-Body")
			except Exception as e:
				TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(self.OVCall.errors,indent=2)),0,TraceTag+"-Errors")
			onevizion.Config["Error"]=True
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request




	def read(self,
		trackorId=None,
		filterOptions=None,
		filters={},
		search=None,
		viewOptions=None,
		fields=[],
		sort={},
		page=None,
		perPage=1000
		):
		""" Retrieve some field data from a set of Trackor instances. List of Trackors must be
			identified either by trackorId or filterOptions, and data fields to be retieved must be
			identified either by viewOptions or a list of fields.

			fields is an array of strings that are the Configured Field Names.
		"""

		URL = "{Website}/api/v3/trackor_types/{TrackorType}/trackors".format(
			Website=self.URL,
			TrackorType=self.TrackorType
			)
		Method='GET'

		FilterSection = ""
		SearchBody = {}
		if trackorId is None:
			if filterOptions is None:
				if search is None:
					#Filtering based on "filters" fields
					for key,value in filters.items():
						FilterSection = FilterSection + key + '=' + URLEncode(str(value)) + '&'
					FilterSection = FilterSection.rstrip('?&')
				else:
					#Filtering based on Search Criteria
					URL += "/search"
					SearchBody = {"data": search}
					Method='POST'
			else:
				#Filtering basd on filterOptions
				FilterSection = "filter="+URLEncode(filterOptions)
		else:
			#Filtering for specific TrackorID
			URL = "{Website}/api/v3/trackors/{TrackorID}".format(
				Website=self.URL,
				TrackorID=str(trackorId)
				)

		if len(FilterSection) == 0:
			ViewSection = ""
		else:
			ViewSection = "&"
		if viewOptions is None:
			ViewSection += 'fields=' + ",".join(fields)
		else:
			ViewSection += 'view=' + URLEncode(viewOptions)

		SortSection=""
		for key,value in sort.items():
			SortSection=SortSection+","+key+":"+value
		if len(SortSection)>0:
			SortSection="&sort="+URLEncode(SortSection.lstrip(','))

		PageSection=""
		if page is not None:
			PageSection = "&page="+str(page)+"&per_page="+str(perPage)

		URL += "?"+FilterSection+ViewSection+SortSection+PageSection

		self.errors = []
		self.jsonData = {}
		self.OVCall = curl(Method,URL,auth=self.auth,**SearchBody)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(URL,2)
		Message(json.dumps(SearchBody,indent=2),2)
		Message("{TrackorType} read completed in {Duration} seconds.".format(
			TrackorType=self.TrackorType,
			Duration=self.OVCall.duration
			),1)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
			TraceTag="{TimeStamp}:".format(TimeStamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
			self.TraceTag = TraceTag
			onevizion.Config["Trace"][TraceTag+"-URL"] = URL
			onevizion.Config["Trace"][TraceTag+"-PostBody"] = json.dumps(SearchBody,indent=2)
			try:
				TraceMessage("Status Code: {StatusCode}".format(StatusCode=self.OVCall.request.status_code),0,TraceTag+"-StatusCode")
				TraceMessage("Reason: {Reason}".format(Reason=self.OVCall.request.reason),0,TraceTag+"-Reason")
				TraceMessage("Body:\n{Body}".format(Body=self.OVCall.request.text),0,TraceTag+"-Body")
			except Exception as e:
				TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(self.OVCall.errors,indent=2)),0,TraceTag+"-Errors")
			onevizion.Config["Error"]=True


	def update(self, trackorId=None, filters={}, fields={}, parents={}, charset=""):
		""" Update data in a list of fields for a Trackor instance.
			"trackorId" is the direct unique identifier in the databse for the record.  Use this or Filters.
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
				CompoundField = {}
				for skey,svalue in value.items():
					CompoundField[skey] = JSONEndValue(svalue)
				FieldsSection[key] = CompoundField
			else:
				FieldsSection[key] = JSONEndValue(value)

		ParentsSection = []
		Parentx={}
		for key, value in parents.items():
			Parentx["trackor_type"] = key
			FilterPart = {}
			for fkey,fvalue in value.items():
				FilterPart[fkey]=JSONEndValue(fvalue)
			Parentx["filter"] = FilterPart
			ParentsSection.append(Parentx)

		if len(FieldsSection) > 0:
			JSONObj["fields"] = FieldsSection
		if len(ParentsSection) > 0:
			JSONObj["parents"] = ParentsSection
		JSON = json.dumps(JSONObj)

		# Build up the filter to find the unique Tackor instance
		if trackorId is None:
			Filter = '?'
			for key,value in filters.items():
				Filter = Filter + key + '=' + URLEncode(str(value)) + '&'
			Filter = Filter.rstrip('?&')
			URL = "{Website}/api/v3/trackor_types/{TrackorType}/trackors{Filter}".format(
					Website=self.URL,
					TrackorType=self.TrackorType,
					Filter=Filter
					)
		else:
			URL = "{Website}/api/v3/trackors/{TrackorID}".format(
					Website=self.URL,
					TrackorID=trackorId
					)
			JSON = json.dumps(FieldsSection)

		Headers = {'content-type': 'application/x-www-form-urlencoded'}
		if charset != "":
			Headers['charset'] = charset
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('PUT',URL, data=JSON, headers=Headers, auth=self.auth)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(URL,2)
		Message(json.dumps(JSONObj,indent=2),2)
		Message("{TrackorType} update completed in {Duration} seconds.".format(
			TrackorType=self.TrackorType,
			Duration=self.OVCall.duration
			),1)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
			TraceTag="{TimeStamp}:".format(TimeStamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
			self.TraceTag = TraceTag
			onevizion.Config["Trace"][TraceTag+"-URL"] = URL
			onevizion.Config["Trace"][TraceTag+"-PostBody"] = json.dumps(JSONObj,indent=2)
			try:
				TraceMessage("Status Code: {StatusCode}".format(StatusCode=self.OVCall.request.status_code),0,TraceTag+"-StatusCode")
				TraceMessage("Reason: {Reason}".format(Reason=self.OVCall.request.reason),0,TraceTag+"-Reason")
				TraceMessage("Body:\n{Body}".format(Body=self.OVCall.request.text),0,TraceTag+"-Body")
			except Exception as e:
				TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(self.OVCall.errors,indent=2)),0,TraceTag+"-Errors")
			onevizion.Config["Error"]=True


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
				CompoundField = {}
				for skey,svalue in value.items():
					CompoundField[skey] = JSONEndValue(svalue)
				FieldsSection[key] = CompoundField
			else:
				FieldsSection[key] = JSONEndValue(value)

		ParentsSection = []
		Parentx={}
		for key, value in parents.items():
			Parentx["trackor_type"] = key
			FilterPart = {}
			for fkey,fvalue in value.items():
				FilterPart[fkey]=JSONEndValue(fvalue)
			Parentx["filter"] = FilterPart
			ParentsSection.append(Parentx)

		if len(FieldsSection) > 0:
			JSONObj["fields"] = FieldsSection
		if len(ParentsSection) > 0:
			JSONObj["parents"] = ParentsSection
		JSON = json.dumps(JSONObj)

		URL = "{URL}/api/v3/trackor_types/{TrackorType}/trackors".format(URL=self.URL, TrackorType=self.TrackorType)

		Headers = {'content-type': 'application/json'}
		if charset != "":
			Headers['charset'] = charset
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('POST',URL, data=JSON, headers=Headers, auth=self.auth)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(URL,2)
		Message(json.dumps(JSONObj,indent=2),2)
		Message("{TrackorType} create completed in {Duration} seconds.".format(
			TrackorType=self.TrackorType,
			Duration=self.OVCall.duration
			),1)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
			TraceTag="{TimeStamp}:".format(TimeStamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
			self.TraceTag = TraceTag
			onevizion.Config["Trace"][TraceTag+"-URL"] = URL
			onevizion.Config["Trace"][TraceTag+"-PostBody"] = json.dumps(JSONObj,indent=2)
			try:
				TraceMessage("Status Code: {StatusCode}".format(StatusCode=self.OVCall.request.status_code),0,TraceTag+"-StatusCode")
				TraceMessage("Reason: {Reason}".format(Reason=self.OVCall.request.reason),0,TraceTag+"-Reason")
				TraceMessage("Body:\n{Body}".format(Body=self.OVCall.request.text),0,TraceTag+"-Body")
			except Exception as e:
				TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(self.OVCall.errors,indent=2)),0,TraceTag+"-Errors")
			onevizion.Config["Error"]=True


	def assignWorkplan(self,trackorId, workplanTemplate, name=None, startDate=None, finishDate=None):
		""" Assign a Workplan to a given Trackor Record.

			trackorID: the system ID for the particular Trackor record that this is being assigned to.
			workplanTemplate: the name of the Workplan Template to assign
			name: Name given to the newly created Workplan instance, by default it is the WPTemplate name
			startDate: if given will set the Start Date of the Workplan and calculate baseline dates
			finishDate: if given will place the finish of the Workplan and backwards calculate dates.
		"""

		URL = "{website}/api/v3/trackors/{trackor_id}/assign_wp?workplan_template={workplan_template}".format(
				website=self.URL,
				trackor_id=trackorId,
				workplan_template=workplanTemplate
				)

		if name is not None:
			URL += "&"+URLEncode(name)

		if startDate is not None:
			if isinstance(startDate, (datetime,datetime.date)):
				dt = startDate.strftime('%Y-%m-%d')
			else:
				dt = str(startDate)
			URL += "&"+URLEncode(dt)

		if finishDate is not None:
			if isinstance(finishDate, (datetime,datetime.date)):
				dt = finishDate.strftime('%Y-%m-%d')
			else:
				dt = str(finishDate)
			URL += "&"+URLEncode(dt)

		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('POST',URL,auth=self.auth)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(URL,2)
		Message("{TrackorType} assign workplan completed in {Duration} seconds.".format(
			TrackorType=self.TrackorType,
			Duration=self.OVCall.duration
			),1)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
			TraceTag="{TimeStamp}:".format(TimeStamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
			self.TraceTag = TraceTag
			onevizion.Config["Trace"][TraceTag+"-URL"] = URL
			try:
				TraceMessage("Status Code: {StatusCode}".format(StatusCode=self.OVCall.request.status_code),0,TraceTag+"-StatusCode")
				TraceMessage("Reason: {Reason}".format(Reason=self.OVCall.request.reason),0,TraceTag+"-Reason")
				TraceMessage("Body:\n{Body}".format(Body=self.OVCall.request.text),0,TraceTag+"-Body")
			except Exception as e:
				TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(self.OVCall.errors,indent=2)),0,TraceTag+"-Errors")
			onevizion.Config["Error"]=True


	def GetFile(self, trackorId=None, fieldName=None, blobDataId=None):
		""" Get a File from a particular Trackor record's particular Configured field

			trackorID: the system ID for the particular Trackor record that this is being assigned to.
			fieldName: should be the Configured Field Name, not the Label.
			blobDataID: the blob_data_id from the blob_data table which may or may not be the current file in a field.

			Use (trackorId and fieldName) or use (blobDataId).  Other combinations are not supported.
		"""

		def get_filename_from_cd(cd):
			"""
			Get filename from content-disposition
			"""
			if not cd:
				return None
			import re
			fname = re.findall("filename[\*]*=(?:UTF-8'')*(.+)", cd)
			if len(fname) == 0:
				return None
			return fname[0]

		self.errors = []
		self.jsonData = {}

		# check parameters and set URL
		if trackorId and fieldName:
			URL = "{Website}/api/v3/trackor/{TrackorID}/file/{ConfigFieldName}".format(
					Website=self.URL,
					TrackorID=trackorId,
					ConfigFieldName=fieldName
					)
			tmpFileName = str(trackorId)+fieldName+".tmp"
		elif blobDataId:
			URL = "{Website}/api/v3/files/{BlobDataID}".format(
					Website=self.URL,
					BlobDataID=blobDataId
					)
			tmpFileName = str(blobDataId)+".tmp"
		else:
			self.errors.append('Bad parameters.  Use (trackorId and fieldName) or use (blobDataId)')
			return None

		before = datetime.utcnow()
		try:
			# NOTE the stream=True parameter
			self.request = requests.get(URL, stream=True, auth=self.auth,allow_redirects=True)
			with open(tmpFileName, 'wb') as f:
				for chunk in self.request.iter_content(chunk_size=1024):
					if chunk: # filter out keep-alive new chunks
						f.write(chunk)
						#f.flush() commented by recommendation from J.F.Sebastian
		except Exception as e:
			self.errors.append(str(e))
		else:
			if self.request.status_code not in range(200,300):
				self.errors.append(str(self.request.status_code)+" = "+self.request.reason)
		after = datetime.utcnow()
		delta = after - before
		self.duration = delta.total_seconds()

		Message(URL,2)
		Message("{TrackorType} get file completed in {Duration} seconds.".format(
			TrackorType=self.TrackorType,
			Duration=self.duration
			),1)
		if len(self.errors) > 0:
			TraceTag="{TimeStamp}:".format(TimeStamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
			self.TraceTag = TraceTag
			onevizion.Config["Trace"][TraceTag+"-URL"] = URL
			try:
				TraceMessage("Status Code: {StatusCode}".format(StatusCode=self.request.status_code),0,TraceTag+"-StatusCode")
				TraceMessage("Reason: {Reason}".format(Reason=self.request.reason),0,TraceTag+"-Reason")
				TraceMessage("Body:\n{Body}".format(Body=self.request.text),0,TraceTag+"-Body")
			except Exception as e:
				pass
				TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(self.errors,indent=2)),0,TraceTag+"-Errors")
			onevizion.Config["Error"]=True

		# return the name of the fiel that was downloaded.
		newFileName = get_filename_from_cd(self.request.headers.get('content-disposition'))
		if newFileName is not None and len(newFileName) > 0:
			os.rename(tmpFileName,newFileName)
			return newFileName
		else:
			return tmpFileName



	def UploadFile(self, trackorId, fieldName, fileName, newFileName=None):
		""" Get a File from a particular Trackor record's particular Configured field

			trackorID: the system ID for the particular Trackor record that this is being assigned to.
			fieldName: should be the Configured Field Name, not the Label.
			fileName: path and file name to file you want to upload
			newFileName: Optional, rename file when uploading.
		"""

		URL = "{Website}/api/v3/trackor/{TrackorID}/file/{ConfigFieldName}".format(
				Website=self.URL,
				TrackorID=trackorId,
				ConfigFieldName=fieldName
				)
		if newFileName is not None:
			URL += "?file_name="+URLEncode(newFileName)
			File = {'file': (os.path.basename(newFileName), open(fileName, 'rb'))}
		else:
			URL += "?file_name="+URLEncode(os.path.basename(fileName))
			File = {'file': (os.path.basename(fileName), open(fileName, 'rb'))}

		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('POST',URL,auth=self.auth,files=File)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(URL,2)
		Message("FileName: {FileName}".format(FileName=fileName),2)
		Message("{TrackorType} upload file completed in {Duration} seconds.".format(
			TrackorType=self.TrackorType,
			Duration=self.OVCall.duration
			),1)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
			TraceTag="{TimeStamp}:".format(TimeStamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
			self.TraceTag = TraceTag
			onevizion.Config["Trace"][TraceTag+"-URL"] = URL
			onevizion.Config["Trace"][TraceTag+"-FileName"] = fileName
			try:
				TraceMessage("Status Code: {StatusCode}".format(StatusCode=self.OVCall.request.status_code),0,TraceTag+"-StatusCode")
				TraceMessage("Reason: {Reason}".format(Reason=self.OVCall.request.reason),0,TraceTag+"-Reason")
				TraceMessage("Body:\n{Body}".format(Body=self.OVCall.request.text),0,TraceTag+"-Body")
			except Exception as e:
				TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(self.OVCall.errors,indent=2)),0,TraceTag+"-Errors")
			onevizion.Config["Error"]=True
