class NotifQueueRecord:

	def __init__(self, jsonObject):
		self.notifQueueId = jsonObject['notifQueueId']
		self.userId = jsonObject['userId']
		self.sender = jsonObject['sender']
		self.toAddress = jsonObject['toAddress']
		self.cc = jsonObject['cc']
		self.bcc = jsonObject['bcc']
		self.subj = jsonObject['subj']
		self.replyTo = jsonObject['replyTo']
		self.createdTs = jsonObject['createdTs']
		self.status = jsonObject['status']
		self.msg = jsonObject['msg']
		self.html = jsonObject['html']
		self.blobDataIds = jsonObject['blobDataIds']

