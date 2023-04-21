import smtplib
from datetime import datetime
import base64
from collections import OrderedDict
from onevizion.util import *
import onevizion


class EMail(object):
	"""Made to simplify sending Email notifications in scripts.

	Attributes:
		server: the SSL SMTP server for the mail connection
		port: the port to conenct to- 465 by default
		security: None, SSL, or STARTTLS
		tls: True if TLS is needed, else false.  Provided for Backwards compatibility
		userName: the "From" and login to the SMTP server
		sender: can specify a from address that is different from userName
		password: the password to conenct to the SMTP server
		to: array of email addresses to send the message to
		subject: subject of the message
		info: dictionary of info to send in the message
		message: main message to send
		files: array of filename/paths to attach
	"""

	def __init__(self,SMTP={}):
		self.server = "mail.onevizion.com"
		self.port = 587
		self.security = "STARTTLS"
		self.tls = "False"
		self.userName = ""
		self.password = ""
		self.sender = ""
		self.to = []
		self.cc = []
		self.subject = ""
		self.info = OrderedDict()
		self.message = ""
		self.body = ""
		self.files = []
		self.duration = 0
		if SMTP == {}:
			if onevizion.Config["SMTPToken"] is not None:
				SMTP = onevizion.Config["ParameterData"][onevizion.Config["SMTPToken"]]
				#self.parameterData(onevizion.Config["ParameterData"][SMTP])
		if 'UserName' in SMTP and 'Password' in SMTP and 'Server' in SMTP:
			self.parameterData(SMTP)

	def passwordData(self,SMTP={}):
		self.parameterData(SMTP)

	def parameterData(self,SMTP={}):
		"""This allows you to pass the SMTP type object from a PasswordData.  Should be a Dictionary.

		Possible Attributes(Dictionary Keys) are:
			UserName: UserName for SMTP server login (required)
			Password: Password for SMTP login (required)
			Server: SMTP server to connect (required)
			Port: Port for server to connect, default 587
			Security: Security Type, can be STARTTLS, SSL, None.
			To: Who to send the email to.  Can be single email address as string , or list of strings
			CC: CC email, can be single email adress as sting, or a list of strings.
		"""
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
			self.security = 'STARTTLS'
		if 'Security' in SMTP:
			self.security = SMTP['Security']
		if 'From' in SMTP:
			self.sender = SMTP['From']
		else:
			self.sender = SMTP['UserName']
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
		"""Main work body, sends email with preconfigured attributes
		"""
		import mimetypes

		from optparse import OptionParser

		from email import encoders
		#from email.message import Message
		from email.mime.audio import MIMEAudio
		from email.mime.base import MIMEBase
		from email.mime.image import MIMEImage
		from email.mime.multipart import MIMEMultipart
		from email.mime.text import MIMEText
		msg = MIMEMultipart()
		msg['To'] = ", ".join(self.to )
		if self.sender != '':
			msg['From'] = self.sender
		else:
			msg['From'] = self.userName
			self.sender = self.userName
		msg['Subject'] = self.subject

		body = self.message + "\n"

		for key,value in self.info.items():
			body = body + "\n\n" + key + ":"
			if isinstance(value, basestring):
				svalue = value.encode('ascii', 'ignore').decode('ascii', 'ignore')
			else:
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



		before = datetime.utcnow()
		Message("Sending Email...",1)
		Message("To: {ToList}".format(ToList=msg['To']),2)
		Message("From: {From}".format(From=msg['From']),2)
		Message("Subject: {Subject}".format(Subject=msg['Subject']),2)
		Message("Body:\n{Body}".format(Body=self.body),2)

		if self.security.upper() in ['STARTTLS','TLS']:
			send = smtplib.SMTP(self.server, int(self.port))
			send.starttls()
		elif self.security.upper() in ['SSL','SSL/TLS']:
			send = smtplib.SMTP_SSL(self.server, self.port)
		else:
			send = smtplib.SMTP(self.server, int(self.port))
		send.login(str(self.userName), str(self.password))
		send.sendmail(str(self.sender),self.to, msg.as_string())
		send.quit()

		after = datetime.utcnow()
		delta = after - before
		self.duration = delta.total_seconds()
		Message("Sent Mail in {Duration} seconds.".format(Duration=self.duration),1)
