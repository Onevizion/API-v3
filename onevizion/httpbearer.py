import requests
import urllib
import smtplib

class HTTPBearerAuth(requests.auth.AuthBase):
	"""Wrapper to create the header needed for authentication using a token

	Attributes:
		ovAccessKey: OneVizion Access Key
		ovSecretKey: OneVizion Secret Key
	"""

	def __init__(self, ovAccessKey, ovSecretKey):
		self.accessKey = ovAccessKey
		self.secretKey = ovSecretKey

	def __call__(self, r):
		r.headers['Authorization'] = 'Bearer ' + self.accessKey + ':' + self.secretKey
		return r
