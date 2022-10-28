import requests
import json
from datetime import datetime
from onevizion.util import *
from onevizion.curl import curl
from onevizion.httpbearer import HTTPBearerAuth
from onevizion.EMail import EMail
import onevizion

class Task(object):

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

	def read(self, taskId = None, workplanId=None, orderNumber=None):
		""" Retrieve some data about a particular WorkPlan Tasks. Tasks must be
			identified either by workplanId, workplanId and orderNumber or by a taskId
		"""
		if taskId is not None:
			URL = "{URL}/api/v3/tasks/{TaskID}".format(URL=self.URL, TaskID=taskId)
		elif orderNumber is not None:
			URL = "{URL}/api/v3/tasks?workplan_id={WorkPlanID}&order_number={OrderNumber}".format(URL=self.URL, WorkPlanID=workplanId, OrderNumber=orderNumber)
		else:
			URL = "{URL}/api/v3/wps/{WorkPlanID}/tasks".format(URL=self.URL, WorkPlanID=workplanId)

		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('GET',URL,auth=self.auth)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(URL,2)
		Message("Task read completed in {Duration} seconds.".format(Duration=self.OVCall.duration),1)
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


	def update(self, taskId, fields={}, dynamicDates=[]):

		if len(dynamicDates)>0:
			fields['dynamic_dates'] = dynamicDates

		JSON = json.dumps(fields)

		URL = "{URL}/api/v3/tasks/{TaskID}".format(URL=self.URL, TaskID=taskId)
		#payload = open('temp_payload.json','rb')
		Headers = {'content-type': 'application/x-www-form-urlencoded'}
		self.errors = []
		self.jsonData = {}
		self.OVCall = curl('PUT',URL, data=JSON, headers=Headers, auth=self.auth)
		self.jsonData = self.OVCall.jsonData
		self.request = self.OVCall.request

		Message(URL,2)
		Message(json.dumps(fields,indent=2),2)
		Message("Task update completed in {Duration} seconds.".format(Duration=self.OVCall.duration),1)
		if len(self.OVCall.errors) > 0:
			self.errors.append(self.OVCall.errors)
			TraceTag="{TimeStamp}:".format(TimeStamp=datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S.%f'))
			self.TraceTag = TraceTag
			onevizion.Config["Trace"][TraceTag+"-URL"] = URL
			onevizion.Config["Trace"][TraceTag+"-PostBody"] = json.dumps(fields,indent=2)
			try:
				TraceMessage("Status Code: {StatusCode}".format(StatusCode=self.OVCall.request.status_code),0,TraceTag+"-StatusCode")
				TraceMessage("Reason: {Reason}".format(Reason=self.OVCall.request.reason),0,TraceTag+"-Reason")
				TraceMessage("Body:\n{Body}".format(Body=self.OVCall.request.text),0,TraceTag+"-Body")
			except Exception as e:
				TraceMessage("Errors:\n{Errors}".format(Errors=json.dumps(self.OVCall.errors,indent=2)),0,TraceTag+"-Errors")
			onevizion.Config["Error"]=True
