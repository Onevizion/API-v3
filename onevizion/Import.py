import requests
import json
from datetime import datetime
from onevizion.util import *
from onevizion.curl import curl
from onevizion.httpbearer import HTTPBearerAuth
from onevizion.EMail import EMail
import onevizion

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
		incremental=None,
		paramToken=None,
		isTokenAuth=False
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
		if self.URL != None and self.userName != None and self.password != None and self.impSpecId != None and self.file != None:
			self.run()

	def run(self):
		if self.isTokenAuth:
			self.auth = HTTPBearerAuth(self.userName, self.password)
		else:
			self.auth = requests.auth.HTTPBasicAuth(self.userName, self.password)
		self.ImportURL = "{URL}/api/v3/imports/{ImpSpecID}/run?action={Action}".format(
			URL=self.URL,
			ImpSpecID=self.impSpecId,
			Action=self.action
			)
		if self.comments is not None:
			self.ImportURL += '&comments=' + URLEncode(self.comments)
		if self.incremental is not None:
			self.ImportURL += '&is_incremental=' + str(self.incremental)
		self.ImportFile = {'file': (os.path.basename(self.file), open(self.file,'rb'))}
		self.OVCall = curl('POST',self.ImportURL,files=self.ImportFile,auth=self.auth)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(self.ImportURL,2)
		Message("FileName: {FileName}".format(FileName=self.ImportFile),2)
		Message("Import Send completed in {Duration} seconds.".format(Duration=self.OVCall.duration),1)
		TraceTag="{TimeStamp}:{FileName}:".format(TimeStamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'),FileName=self.file)
		self.TraceTag = TraceTag
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
			onevizion.Config["Trace"][TraceTag+"-URL"] = self.ImportURL
			onevizion.Config["Trace"][TraceTag+"-FileName"] = self.ImportFile
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
				onevizion.Config["Trace"][TraceTag+"-URL"] = self.ImportURL
				onevizion.Config["Trace"][TraceTag+"-FileName"] = self.ImportFile
				TraceMessage("Eror Message: {Error}".format(Error=self.jsonData["error_message"]),0,TraceTag+"-ErrorMessage")
				onevizion.Config["Error"]=True
			if "warnings" in self.jsonData and len(self.jsonData["warnings"]) > 0:
				self.warnings.extend(self.jsonData["warnings"])
				onevizion.Config["Trace"][TraceTag+"-URL"] = self.ImportURL
				onevizion.Config["Trace"][TraceTag+"-FileName"] = self.ImportFile
				TraceMessage("Eror Message: {Error}".format(Error=self.jsonData["warnings"]),0,TraceTag+"-Warnings")
			if "process_id" in self.jsonData:
				self.processId = self.jsonData["process_id"]
				self.status = self.jsonData["status"]
				Message("Success!  ProcessID: {ProcID}".format(ProcID=self.processId),1)

	def interrupt(self,ProcessID=None):
		if ProcessID is None:
			PID = self.processId
		else:
			PID = ProcessID
		if self.isTokenAuth:
			self.auth = HTTPBearerAuth(self.userName, self.password)
		else:
			self.auth = requests.auth.HTTPBasicAuth(self.userName, self.password)
		self.ImportURL = "{URL}/api/v3/imports/runs/{ProcID}/interrupt".format(
			URL=self.URL,
			ProcID=PID
			)
		self.OVCall = curl('POST',self.ImportURL,auth=self.auth)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(self.ImportURL,2)
		Message("Interupt Process completed in {Duration} seconds.".format(Duration=self.OVCall.duration),1)
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
			Message("Successful Interrupt  ProcessID: {ProcID}".format(ProcID=self.processId),1)

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

		if self.isTokenAuth:
			self.auth = HTTPBearerAuth(self.userName, self.password)
		else:
			self.auth = requests.auth.HTTPBasicAuth(self.userName, self.password)
		self.ImportURL = "{URL}/api/v3/imports/runs".format(
			URL=self.URL
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

		self.OVCall = curl('GET',self.ImportURL,auth=self.auth)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(self.ImportURL,2)
		Message("Get Process Data completed in {Duration} seconds.".format(Duration=self.OVCall.duration),1)
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
		Message("Status: {Status}".format(Status=self.status),1)

		return self.jsonData
