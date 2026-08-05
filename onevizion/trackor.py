"""Trackor API wrapper for CRUD operations on trackor instances.

This module provides the Trackor class for creating, reading, updating, and
deleting trackor instances, as well as uploading/downloading files and assigning
workplans.

Example:
    >>> from onevizion import Trackor
    >>>
    >>> # Initialize with credentials
    >>> t = Trackor(
    ...     trackorType="PROJECT",
    ...     URL="https://my.onevizion.com",
    ...     userName="user",
    ...     password="pass"
    ... )
    >>>
    >>> # Read a trackor by ID
    >>> t.read(trackorId=12345, fields=["TRACKOR_KEY", "PROJECT_NAME"])
    >>> print(t.jsonData)
    >>>
    >>> # Update trackor fields
    >>> t.update(
    ...     trackorId=12345,
    ...     fields={"PROJECT_NAME": "Updated Name", "DESCRIPTION": "New desc"}
    ... )
    >>>
    >>> # Create a new trackor
    >>> t.create(
    ...     fields={"PROJECT_NAME": "New Project"},
    ...     parents={"PROGRAM": {"PROGRAM_KEY": "PROG-001"}}
    ... )
    >>>
    >>> # Upload a file
    >>> t.UploadFile(trackorId=12345, fieldName="F_FILE", fileName="/path/to/file.pdf")
    >>>
    >>> # Download a file
    >>> filename = t.GetFile(trackorId=12345, fieldName="F_FILE")

For parameter-based authentication:
    >>> import onevizion
    >>> onevizion.Config["ParameterData"] = {...}  # Load from JSON file
    >>> t = Trackor(trackorType="PROJECT", paramToken="my.onevizion.com")
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json
from datetime import datetime

import requests

import onevizion
from onevizion.curl import curl
from onevizion.httpbearer import HTTPBearerAuth
from onevizion.util import *


class Trackor(object):
	"""Wrapper for calling the OneVizion API for Trackors. Supports CRUD operations,
	file uploads/downloads, and workplan assignment.

	Attributes:
		trackorType: The name of the TrackorType being changed.
		URL: A string representing the website's main URL for instance "trackor.onevizion.com".
		userName: the username used to login to the system
		password: the password used to gain access to the system

		errors: array of any errors encounterd
		OVCall: the requests object of call to the web api
		jsonData: the json data converted to python array
	"""

	def __init__(self, trackorType = "", URL = "", userName="", password="", paramToken=None, isTokenAuth=False, max_file_size=None):
		self.TrackorType = trackorType
		self.URL = URL
		self.userName = userName
		self.password = password
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl()
		self.request = None
		self.max_file_size = max_file_size  # Optional max file size in bytes (None = no limit)

		if paramToken is not None:
			if self.URL == "":
				self.URL = onevizion.Config["ParameterData"][paramToken]['url']
			if self.userName == "":
				self.userName = onevizion.Config["ParameterData"][paramToken]['UserName']
			if self.password == "":
				self.password = onevizion.Config["ParameterData"][paramToken]['Password']
			if 'isTokenAuth' in onevizion.Config["ParameterData"][paramToken]:
				isTokenAuth = onevizion.Config["ParameterData"][paramToken]['isTokenAuth']

		# Validate URL protocol before transformation (security check)
		if self.URL:
			url_lower = str(self.URL).lower()
			# If URL already has a protocol, ensure it's http or https
			# Check for : before any / (which would indicate a protocol)
			colon_pos = url_lower.find(':')
			slash_pos = url_lower.find('/')
			if colon_pos != -1 and (slash_pos == -1 or colon_pos < slash_pos) and not url_lower.startswith(('http://', 'https://')):
				self.errors.append("URL protocol must be http:// or https://. Got: {url}".format(url=self.URL))

		self.URL = getUrlContainingScheme(self.URL)

		if isTokenAuth:
			self.auth = HTTPBearerAuth(self.userName, self.password)
		else:
			self.auth = requests.auth.HTTPBasicAuth(self.userName, self.password)

		# Validate other inputs
		self._validate_inputs()

	def _validate_inputs(self):
		"""Validate inputs for security and correctness.

		Errors are appended to self.errors.
		"""
		# Validate max_file_size (must be positive or None)
		if self.max_file_size is not None:
			try:
				size_val = int(self.max_file_size)
				if size_val <= 0:
					self.errors.append("Max file size must be positive. Got: {size}".format(size=self.max_file_size))
			except (TypeError, ValueError):
				self.errors.append("Max file size must be an integer. Got: {size}".format(size=self.max_file_size))

	def _validate_file_size_from_path(self, file_path):
		"""Validate file size from path against max_file_size limit.

		Returns True if valid or no limit set, False otherwise.
		Errors are appended to self.errors.
		"""
		if self.max_file_size is None:
			return True
		try:
			file_size = os.path.getsize(file_path)
			if file_size > self.max_file_size:
				self.errors.append(
					"File size ({size} bytes) exceeds maximum allowed size ({max} bytes)".format(
						size=file_size,
						max=self.max_file_size
					)
				)
				return False
			return True
		except OSError as e:
			self.errors.append("Cannot determine file size: {err}".format(err=str(e)))
			return False

	def _validate_file_size_from_headers(self, content_length):
		"""Validate file size from Content-Length header against max_file_size limit.

		Returns True if valid or no limit set, False otherwise.
		Errors are appended to self.errors.
		"""
		if self.max_file_size is None:
			return True
		if content_length > self.max_file_size:
			self.errors.append(
				"File size ({size} bytes) exceeds maximum allowed size ({max} bytes)".format(
					size=content_length,
					max=self.max_file_size
				)
			)
			return False
		return True

	def _safe_close_response(self):
		"""Safely close response, ignoring errors."""
		if self.request:
			try:
				self.request.close()
			except Exception:
				pass

	def _safe_remove_file(self, file_path):
		"""Safely remove file, ignoring errors."""
		try:
			if os.path.exists(file_path):
				os.remove(file_path)
		except Exception:
			pass

	def _build_fields_section(self, fields):
		"""Build fields section for API request from fields dict.

		Handles both simple values and compound (dict) field values.
		Returns dict suitable for JSON serialization.
		"""
		fields_section = {}
		for key, value in fields.items():
			if isinstance(value, dict):
				compound_field = {}
				for skey, svalue in value.items():
					compound_field[skey] = JSONEndValue(svalue)
				fields_section[key] = compound_field
			else:
				fields_section[key] = JSONEndValue(value)
		return fields_section

	def _build_parents_section(self, parents):
		"""Build parents section for API request from parents dict.

		Converts dict of TrackorType: {field: value} to list format.
		Returns list suitable for JSON serialization.
		"""
		parents_section = []
		for trackor_type, filter_dict in parents.items():
			parent_obj = {
				"trackor_type": trackor_type,
				"filter": {fkey: JSONEndValue(fvalue) for fkey, fvalue in filter_dict.items()}
			}
			parents_section.append(parent_obj)
		return parents_section

	def _execute_api_call(self, method, url, log_level=2, extra_data=None, **curl_kwargs):
		"""Execute API call with standardized error handling and logging.

		Args:
			method: HTTP method (GET, POST, PUT, DELETE, etc.)
			url: Target URL
			log_level: Message log level (default 2)
			extra_data: Optional dict of extra data to log on error
			**curl_kwargs: Additional arguments to pass to curl

		Returns:
			True if successful (no errors), False otherwise
		"""
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl(method, url, auth=self.auth, **curl_kwargs)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(url, log_level)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
			self.TraceTag = LogErrorToTrace(self.OVCall, url, extra_data=extra_data)
			return False
		return True

	def delete(self,trackorId):
		""" Delete a Trackor instance.  Must pass a trackorId, the unique DB number.
		"""
		FilterSection = "trackor_id=" + str(trackorId)
		URL = "{URL}/api/v3/trackor_types/{TrackorType}/trackors?{FilterSection}".format(
			URL=self.URL, TrackorType=self.TrackorType, FilterSection=FilterSection)

		self._execute_api_call('DELETE', URL)
		Message("Deletes completed in {Duration} seconds.".format(Duration=self.OVCall.duration),1)




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
			self.TraceTag = LogErrorToTrace(self.OVCall, URL, post_body=SearchBody)


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

		# Build JSON package from fields and parents
		JSONObj = {}
		FieldsSection = self._build_fields_section(fields)
		ParentsSection = self._build_parents_section(parents)

		if FieldsSection:
			JSONObj["fields"] = FieldsSection
		if ParentsSection:
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

		Headers = {'content-type': 'application/json'}
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
			self.TraceTag = LogErrorToTrace(self.OVCall, URL, post_body=JSONObj)


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

		# Build JSON package from fields and parents
		JSONObj = {}
		FieldsSection = self._build_fields_section(fields)
		ParentsSection = self._build_parents_section(parents)

		if FieldsSection:
			JSONObj["fields"] = FieldsSection
		if ParentsSection:
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
			self.TraceTag = LogErrorToTrace(self.OVCall, URL, post_body=JSONObj)


	def assignWorkplan(self, trackorId, workplanTemplate, name=None, isActive=False, startDate=None, finishDate=None):
		""" Assign a Workplan to a given Trackor Record.

			trackorID: the system ID for the particular Trackor record that this is being assigned to.
			workplanTemplate: the name of the Workplan Template to assign
			name: Name given to the newly created Workplan instance, by default it is the WPTemplate name
			isActive: Makes Workplan active if True, otherwise False. The default value is False.
			startDate: if given will set the Start Date of the Workplan and calculate baseline dates
			finishDate: if given will place the finish of the Workplan and backwards calculate dates.
		"""

		URL = "{website}/api/v3/trackors/{trackor_id}/assign_wp?workplan_template={workplan_template}&is_active={is_active}".format(
				website=self.URL,
				trackor_id=trackorId,
				workplan_template=URLEncode(workplanTemplate),
				is_active=isActive
				)

		if name is not None:
			URL += "&name="+URLEncode(name)

		if startDate is not None:
			if isinstance(startDate, datetime):
				dt = startDate.strftime('%Y-%m-%d')
			else:
				dt = str(startDate)
			URL += "&proj_start_date="+URLEncode(dt)

		if finishDate is not None:
			if isinstance(finishDate, datetime):
				dt = finishDate.strftime('%Y-%m-%d')
			else:
				dt = str(finishDate)
			URL += "&proj_finish_date="+URLEncode(dt)

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
			self.TraceTag = LogErrorToTrace(self.OVCall, URL)


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
			fname = re.findall(r"filename[\*]*=(?:UTF-8'')*(.+)", cd)
			if len(fname) == 0:
				return None
			return fname[0]

		self.errors = []
		self.jsonData = {}

		# Validate and check parameters
		try:
			if trackorId and fieldName:
				URL = "{Website}/api/v3/trackor/{TrackorID}/file/{ConfigFieldName}".format(
						Website=self.URL,
						TrackorID=str(trackorId),
						ConfigFieldName=str(fieldName)
						)
				tmpFileName = str(trackorId)+str(fieldName)+".tmp"
			elif blobDataId:
				URL = "{Website}/api/v3/files/{BlobDataID}".format(
						Website=self.URL,
						BlobDataID=str(blobDataId)
						)
				tmpFileName = str(blobDataId)+".tmp"
			else:
				self.errors.append(
					"Invalid parameters for GetFile. "
					"Must provide either (trackorId AND fieldName) or (blobDataId). "
					"Got: trackorId={}, fieldName={}, blobDataId={}".format(
						repr(trackorId), repr(fieldName), repr(blobDataId)
					)
				)
				return None
		except (TypeError, ValueError) as e:
			self.errors.append("Invalid parameter types for GetFile: {}".format(str(e)))
			return None

		before = utcnow()
		try:
			self.request = requests.get(URL, stream=True, auth=self.auth, allow_redirects=True, timeout=300.0)

			# Validate file size if limit is set and Content-Length is available
			if 'content-length' in self.request.headers:
				content_length = int(self.request.headers['content-length'])
				if not self._validate_file_size_from_headers(content_length):
					self._safe_close_response()
					return None

			# Check HTTP status before writing
			if self.request.status_code not in range(200,300):
				reason = self.request.reason if self.request.reason else "Unknown"
				self.errors.append(str(self.request.status_code)+" = "+reason)
			else:
				# Download to file
				with open(tmpFileName, 'wb') as f:
					for chunk in self.request.iter_content(chunk_size=1024):
						if chunk:  # filter out keep-alive new chunks
							f.write(chunk)

		except Exception as e:
			self.errors.append(str(e))
			self._safe_remove_file(tmpFileName)
		finally:
			self._safe_close_response()
		after = utcnow()
		delta = after - before
		self.duration = delta.total_seconds()

		Message(URL,2)
		Message("{TrackorType} get file completed in {Duration} seconds.".format(
			TrackorType=self.TrackorType,
			Duration=self.duration
			),1)
		if len(self.errors) > 0:
			TraceTag="{TimeStamp}:".format(TimeStamp=utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
			self.TraceTag = TraceTag
			onevizion.Config["Trace"][TraceTag+"-URL"] = URL
			try:
				TraceMessage("Status Code: {StatusCode}".format(StatusCode=self.request.status_code),0,TraceTag+"-StatusCode")
				TraceMessage("Reason: {Reason}".format(Reason=self.request.reason),0,TraceTag+"-Reason")
				TraceMessage("Body:\n{Body}".format(Body=self.request.text),0,TraceTag+"-Body")
			except Exception:
				TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(self.errors,indent=2)),0,TraceTag+"-Errors")
			onevizion.Config["Error"]=True
			return None  # Return None on error

		# return the name of the file that was downloaded
		if self.request and hasattr(self.request, 'headers'):
			newFileName = get_filename_from_cd(self.request.headers.get('content-disposition'))
			if newFileName is not None and len(newFileName) > 0:
				os.rename(tmpFileName,newFileName)
				return newFileName
		return tmpFileName



	def UploadFile(self, trackorId, fieldName, fileName, newFileName=None):
		""" Upload a file to a particular Trackor record's particular Configured field

			trackorId: the system ID for the particular Trackor record that this is being assigned to.
			fieldName: should be the Configured Field Name, not the Label.
			fileName: path and file name to file you want to upload
			newFileName: Optional, rename file when uploading.
		"""

		FilePath = fileName
		FileName = newFileName if newFileName else os.path.basename(FilePath)

		# Validate file size if limit is set
		if not self._validate_file_size_from_path(FilePath):
			return

		Message("FilePath: {FilePath}".format(FilePath=FilePath),2)

		with open(FilePath, 'rb') as BinaryStream:
			self.UploadFileByFileContents(trackorId=trackorId, fieldName=fieldName, fileName=FileName, fileContents=BinaryStream)


	def UploadFileByFileContents(self, trackorId, fieldName, fileName, fileContents):
		""" Upload a file to a particular Trackor record's particular Configured field

			trackorID: the system ID for the particular Trackor record that this is being assigned to.
			fieldName: should be the Configured Field Name, not the Label.
			fileName: name of the file you want to upload.
			fileContents: byte string or BufferedReader of the file you want to upload.
		"""

		URL = "{Website}/api/v3/trackor/{TrackorID}/file/{ConfigFieldName}".format(
				Website=self.URL,
				TrackorID=trackorId,
				ConfigFieldName=fieldName
				)

		URL += "?file_name=" + URLEncode(fileName)
		File = {'file': (fileName, fileContents)}

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
			self.TraceTag = LogErrorToTrace(self.OVCall, URL, extra_data={"FileName": fileName})
