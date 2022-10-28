from onevizion.util import *
from abc import ABC, abstractmethod
from onevizion.integration.log import IntegrationLog
from onevizion.integration.loglevel import LogLevel
from onevizion.notif.queue import NotifQueue
from onevizion.notif.queuerecord import NotifQueueRecord
from onevizion.notif.queuestatus import NotifQueueStatus
import time

class NotificationService(ABC):
	"""Wrapper for getting records from the notification queue and sending them somewhere.
		It is an abstract class whose 'sendNotification' method you must implement.

	Attributes:
		serviceId: ID of the Notification Service
		processId: the system processId
		URL: a string representing the website's main URL for instance "trackor.onevizion.com".
		userName: the username or the OneVizion API Security Token Access Key that is used to login to the system
		password: the password or the OneVizion API Security Token Secret Key that is used to gain access to the system
		logLevel: log level name (Info, Warning, Error, Debug) for logging integration actions
		maxAttempts: the number of attempts to send message 
		nextAttemptDelay: the delay in seconds before the next message sending after an unsuccessful attempt

	Exceptions are processed, written to the log and an exception is thrown for methods:
		_convertNotifQueueJsonToList,
		_prepareNotifQueue
	"""

	def __init__(self, serviceId, processId, URL="", userName="", password="", paramToken=None, isTokenAuth=False, logLevel="", maxAttempts=1, nextAttemptDelay=30):
		self._notifQueue = NotifQueue(serviceId, URL, userName, password, paramToken, isTokenAuth)
		self._maxAttempts = maxAttempts or 1
		self._nextAttemptDelay = nextAttemptDelay or 30
		self._integrationLog = IntegrationLog(processId, URL, userName, password, paramToken, isTokenAuth, logLevel)

	def start(self):
		self._integrationLog.add(LogLevel.INFO, "Starting Integration")
		attempts = 0

		self._integrationLog.add(LogLevel.INFO, "Receiving Notif Queue")
		notifQueueJson = self._notifQueue.getNotifQueue()
		self._integrationLog.add(LogLevel.DEBUG, "Notif Queue json data", str(notifQueueJson))

		try:
			notifQueue = self._convertNotifQueueJsonToList(notifQueueJson)
		except Exception as e:
			self._integrationLog.add(LogLevel.ERROR, "Can't convert Notif Queue json data to list", str(e))
			raise Exception("Can't convert Notif Queue json data to list") #from e

		preparedNotifQueue = []
		try:
			preparedNotifQueue = self._prepareNotifQueue(notifQueue)
		except Exception as e:
			self._integrationLog.add(LogLevel.ERROR, "Can't prepare Notif Queue to send", str(e))
			raise Exception("Can't prepare Notif Queue to send") #from e

		self._integrationLog.add(LogLevel.INFO, "Notif Queue size: [{}]".format(len(preparedNotifQueue)))

		while len(preparedNotifQueue) > 0 and attempts < self._maxAttempts:
			if attempts > 0:
				self._integrationLog.add(LogLevel.INFO, "Attempt Number [{}]".format(attempts + 1))

			for notifQueueRec in preparedNotifQueue:
				self._integrationLog.add(LogLevel.INFO,
											  "Sending Notif Queue Record with id = [{}]".format(
												  notifQueueRec.notifQueueId))
				notifQueueRec.status = NotifQueueStatus.SENDING.name
				self._notifQueue.updateNotifQueueRecStatus(notifQueueRec)

				try:
					self.sendNotification(notifQueueRec)
				except Exception as e:
					self._notifQueue.addNewAttempt(notifQueueRec.notifQueueId, str(e))
					self._integrationLog.add(LogLevel.ERROR,
												  "Can't send Notif Queue Record with id = [{}]".format(
													  notifQueueRec.notifQueueId),
												  str(e))

					if attempts + 1 == self._maxAttempts:
						notifQueueRec.status = NotifQueueStatus.FAIL.name
					else:
						notifQueueRec.status = NotifQueueStatus.FAIL_WILL_RETRY.name

				else:
					notifQueueRec.status = NotifQueueStatus.SUCCESS.name

				self._notifQueue.updateNotifQueueRecStatus(notifQueueRec)

			preparedNotifQueue = list(
				filter(lambda rec: rec.status != NotifQueueStatus.SUCCESS.name, preparedNotifQueue))
			attempts += 1

			if len(preparedNotifQueue) > 0 and self._maxAttempts > attempts:
				self._integrationLog.add(LogLevel.WARNING,
											  "Can't send [{0}] notifications. Next try in [{1}] seconds".format(
												  len(preparedNotifQueue),
												  self._nextAttemptDelay))
				time.sleep(self._nextAttemptDelay)

		if len(preparedNotifQueue) > 0:
			self._integrationLog.add(LogLevel.ERROR,
										  "Can't send [{}] notifications. All attempts have been exhausted.".format(
											  len(preparedNotifQueue)))

		self._integrationLog.add(LogLevel.INFO, "Integration has been completed")

	@staticmethod
	def _convertNotifQueueJsonToList(jsonData):
		notifQueue = []
		for jsonObj in jsonData:
			notifQueue.append(NotifQueueRecord(jsonObj))
		return notifQueue

	@abstractmethod
	def sendNotification(self, notifQueueRecord):
		"""Send notifications anywhere. You must implement this in your integration. 
			"notifQueueRecord": record from the notification queue. An instance of the NotifQueueRecord class
		"""
		pass

	def _prepareNotifQueue(self, notifQueue):
		return notifQueue
