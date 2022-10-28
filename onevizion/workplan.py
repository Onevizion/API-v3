import requests
import json
from datetime import datetime
from onevizion.util import *
from onevizion.curl import curl
from onevizion.httpbearer import HTTPBearerAuth
from onevizion.EMail import EMail
import onevizion

class WorkPlan(object):
	"""Wrapper for calling the OneVizion API for WorkPlans.  You can Read or Update
		WorkPlan instances with the like named methods.

	Attributes:
		URL: A string representing the website's main URL for instance "trackor.onevizion.com".
		userName: the username used to login to the system
		password: the password used to gain access to the system

		errors: array of any errors encounterd
		OVCall: the requests object of call to the web api
		jsonData: the json data converted to python array
	"""

	def __init__(self, URL = "", userName="", password="", paramToken=None, isTokenAuth=False):
		self.URL = URL
		self.userName = userName
		self.password = password
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl()
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

	def read(self, workplanId = None, workplanTemplate = "", trackorType = "", trackorId = None):
		""" Retrieve some data about a particular WorkPlan.WorkPlan must be
			identified either by workplanId or by a WorkPlanTemplate, TrackorType, and TrackorID
		"""
		FilterSection = ""
		if workplanId is None:
			#?wp_template=Augment%20Workplan&trackor_type=SAR&trackor_id=1234
			FilterSection = "?wp_template={WPTemplate}&trackor_type={TrackorType}&trackor_id={TrackorID}".format(
				WPTemplate=URLEncode(workplanTemplate),
				TrackorType=URLEncode(trackorType),
				TrackorID=trackorId
				)
		else:
			#1234
			FilterSection = str(workplanId)

		URL = "{URL}/api/v3/wps/{FilterSection}".format(URL=self.URL, FilterSection=FilterSection)
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('GET',URL,auth=self.auth)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(URL,2)
		Message("Workplan read completed in {Duration} seconds.".format(Duration=self.OVCall.duration),1)
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
