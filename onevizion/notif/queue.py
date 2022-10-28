import requests
from onevizion.util import *
from onevizion.curl import curl
from onevizion.httpbearer import HTTPBearerAuth
from onevizion.notif.queuerecord import NotifQueueRecord
from onevizion.notif.queuestatus import NotifQueueStatus
import onevizion

class NotifQueue:
	"""Wrapper for calling the Onvizion API for Notification Queue. You can get a Notifications Queue, 
		update the status of a notification queue record, add new attempt 

	Attributes:
		serviceId: ID of the Notification Service
		URL: a string representing the website's main URL for instance "trackor.onevizion.com".
		userName: the username or the OneVizion API Security Token Access Key that is used to login to the system
		password: the password or the OneVizion API Security Token Secret Key that is used to gain access to the system

	Exception can be thrown for methods:
		getNotifQueue,
		updateNotifQueueRecStatusById,
		addNewAttempt
	"""

	def __init__(self, serviceId, URL="", userName="", password="", paramToken=None, isTokenAuth=False):
		self._serviceId = serviceId
		self._URL = URL
		self._userName = userName
		self._password = password
		self._headers = {'content-type': 'application/json'}

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


	def getNotifQueue(self):
		URL = "{URL}/api/internal/notif/queue?service_id={ServiceID}".format(URL=self._URL, ServiceID=self._serviceId)
		OVCall = curl('GET', URL, headers=self._headers, auth=self._auth)
		if len(OVCall.errors) > 0:
			raise Exception(OVCall.errors)
		return OVCall.jsonData

	def updateNotifQueueRecStatusById(self, notifQueueRecId, status):
		URL = "{URL}/api/internal/notif/queue/{notifQueueRecId}/update_status?status={status}".format(URL=self._URL, notifQueueRecId=notifQueueRecId, status=status)
		OVCall = curl('PATCH', URL, headers=self._headers, auth=self._auth)
		if len(OVCall.errors) > 0:
			raise Exception(OVCall.errors)

	def addNewAttempt(self, notifQueueRecId, errorMessage):
		URL = "{URL}/api/internal/notif/queue/{notifQueueRecId}/attempts?error_code={errorMessage}".format(URL=self._URL, notifQueueRecId=notifQueueRecId, errorMessage=errorMessage)
		OVCall = curl('POST', URL, headers=self._headers, auth=self._auth)
		if len(OVCall.errors) > 0:
			raise Exception(OVCall.errors)

	def updateNotifQueueRecStatus(self, notifQueueRec):
		self.updateNotifQueueRecStatusById(notifQueueRec.notifQueueId, notifQueueRec.status)
