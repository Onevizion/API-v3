import requests
import json
from datetime import datetime
from onevizion.util import *
from onevizion.curl import curl
from onevizion.httpbearer import HTTPBearerAuth
from onevizion.EMail import EMail
import onevizion

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
		comments=None,
		paramToken=None,
		isTokenAuth=False
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
		self.isTokenAuth = isTokenAuth
		if paramToken is not None:
			if self.URL is None:
				self.URL = onevizion.Config["ParameterData"][paramToken]['url']
			if self.userName is None:
				self.userName = onevizion.Config["ParameterData"][paramToken]['UserName']
			if self.password is None:
				self.password = onevizion.Config["ParameterData"][paramToken]['Password']

		self.URL = getUrlContainingScheme(self.URL)

		# If all info is filled out, go ahead and run the query.
		if self.URL is not None and self.userName is not None and self.password is not None and self.trackorType is not None and (self.viewOptions is not None or len(self.fields)>0 or self.fileFields is not None) and (self.filterOptions is not None or len(self.filters)>0):
			self.run()

	def run(self):
		if self.isTokenAuth:
			self.auth = HTTPBearerAuth(self.userName, self.password)
		else:
			self.auth = requests.auth.HTTPBasicAuth(self.userName, self.password)
		self.ImportURL = "{URL}/api/v3/exports/{TrackorType}/run?export_mode={ExportMode}&delivery={Delivery}".format(
			URL=self.URL,
			TrackorType=self.trackorType,
			ExportMode=self.exportMode,
			Delivery=self.delivery
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
		self.OVCall = curl('POST',self.ImportURL,auth=self.auth)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(self.ImportURL,2)
		Message("Run Export completed in {Duration} seconds.".format(Duration=self.OVCall.duration),1)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
			TraceTag="{TimeStamp}:".format(TimeStamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
			self.TraceTag = TraceTag
			onevizion.Config["Trace"][TraceTag+"-URL"] = self.ImportURL
			try:
				TraceMessage("Status Code: {StatusCode}".format(StatusCode=self.OVCall.request.status_code),0,TraceTag+"-StatusCode")
				TraceMessage("Reason: {Reason}".format(Reason=self.OVCall.request.reason),0,TraceTag+"-Reason")
				TraceMessage("Body:\n{Body}".format(Body=self.OVCall.request.text),0,TraceTag+"-Body")
			except Exception as e:
				TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(self.OVCall.errors,indent=2)),0,TraceTag+"-Errors")
			onevizion.Config["Error"]=True
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
		if self.isTokenAuth:
			self.auth = HTTPBearerAuth(self.userName, self.password)
		else:
			self.auth = requests.auth.HTTPBasicAuth(self.userName, self.password)
		self.ImportURL = "{URL}/api/v3/exports/runs/{ProcID}/interrupt".format(
			URL=self.URL,
			ProcID=PID
			)
		self.OVCall = curl('POST',self.ImportURL,auth=self.auth)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(self.ImportURL,2)
		Message("Get Interupt Export completed in {Duration} seconds.".format(Duration=self.OVCall.duration),1)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
			TraceTag="{TimeStamp}:".format(TimeStamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
			self.TraceTag = TraceTag
			onevizion.Config["Trace"][TraceTag+"-URL"] = self.ImportURL
			try:
				TraceMessage("Status Code: {StatusCode}".format(StatusCode=self.OVCall.request.status_code),0,TraceTag+"-StatusCode")
				TraceMessage("Reason: {Reason}".format(Reason=self.OVCall.request.reason),0,TraceTag+"-Reason")
				TraceMessage("Body:\n{Body}".format(Body=self.OVCall.request.text),0,TraceTag+"-Body")
			except Exception as e:
				TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(self.OVCall.errors,indent=2)),0,TraceTag+"-Errors")
			onevizion.Config["Error"]=True
		else:
			self.processId = PID
		if "status" in self.jsonData:
			self.status = self.jsonData['status']

	def getProcessStatus(self,ProcessID=None):
		if ProcessID is None:
			PID = self.processId
		else:
			PID = ProcessID
		if self.isTokenAuth:
			self.auth = HTTPBearerAuth(self.userName, self.password)
		else:
			self.auth = requests.auth.HTTPBasicAuth(self.userName, self.password)
		self.ImportURL = "{URL}/api/v3/exports/runs/{ProcID}".format(
			URL=self.URL,
			ProcID=PID
			)
		self.OVCall = curl('GET',self.ImportURL,auth=self.auth)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(self.ImportURL,2)
		Message("Get Process Status for Export completed in {Duration} seconds.".format(Duration=self.OVCall.duration),1)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
			TraceTag="{TimeStamp}:".format(TimeStamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
			self.TraceTag = TraceTag
			onevizion.Config["Trace"][TraceTag+"-URL"] = self.ImportURL
			try:
				TraceMessage("Status Code: {StatusCode}".format(StatusCode=self.OVCall.request.status_code),0,TraceTag+"-StatusCode")
				TraceMessage("Reason: {Reason}".format(Reason=self.OVCall.request.reason),0,TraceTag+"-Reason")
				TraceMessage("Body:\n{Body}".format(Body=self.OVCall.request.text),0,TraceTag+"-Body")
			except Exception as e:
				TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(self.OVCall.errors,indent=2)),0,TraceTag+"-Errors")
			onevizion.Config["Error"]=True
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
		if self.isTokenAuth:
			self.auth = HTTPBearerAuth(self.userName, self.password)
		else:
			self.auth = requests.auth.HTTPBasicAuth(self.userName, self.password)
		self.ImportURL = "{URL}/api/v3/exports/runs/{ProcID}/file".format(
			URL=self.URL,
			ProcID=PID
			)

		self.OVCall = curl('GET',self.ImportURL,auth=self.auth)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(self.ImportURL,2)
		Message("Get File for Export completed in {Duration} seconds.".format(Duration=self.OVCall.duration),1)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
			TraceTag="{TimeStamp}:".format(TimeStamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
			onevizion.Config["Trace"][TraceTag+"-URL"] = self.ImportURL
			try:
				TraceMessage("Status Code: {StatusCode}".format(StatusCode=self.OVCall.request.status_code),0,TraceTag+"-StatusCode")
				TraceMessage("Reason: {Reason}".format(Reason=self.OVCall.request.reason),0,TraceTag+"-Reason")
				TraceMessage("Body:\n{Body}".format(Body=self.OVCall.request.text),0,TraceTag+"-Body")
			except Exception as e:
				TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(self.OVCall.errors,indent=2)),0,TraceTag+"-Errors")
			onevizion.Config["Error"]=True
		else:
			self.content = self.request.content
		return self.content
