"""Low-level HTTP wrapper with automatic error handling and JSON parsing.

This module provides the curl class, a thin wrapper around requests.request()
that adds consistent error handling, automatic JSON parsing, and duration tracking.

The curl class is used internally by all OneVizion API classes (Trackor, Import,
Export, etc.) to make HTTP requests. It automatically:
    - Captures and stores errors in the errors list
    - Parses JSON responses when available
    - Tracks request duration
    - Applies default timeout (300s) to prevent infinite hangs
    - Records the sent URL and arguments for debugging

Example:
    >>> from onevizion import curl
    >>> c = curl('GET', 'https://api.example.com/data', auth=('user', 'pass'))
    >>> if len(c.errors) == 0:
    ...     print(c.jsonData)
    ... else:
    ...     print("Error:", c.errors)

Note:
    Most users should use higher-level classes like Trackor or Import rather
    than curl directly. This class is primarily for internal use and advanced
    custom integrations.
"""
from __future__ import absolute_import, division, print_function, unicode_literals

import json

import requests

from onevizion.util import utcnow


class curl(object):
	"""Wrapper for requests.request() that handles error trapping and JSON parsing.
	If URL is passed on Instantiation, it will automatically run, else, it will wait for you to set
	properties, then run it with runQuery() command.  Erors should be trapped and put into "errors" array.
	If JSON is returned, it will be put into "data" as per json.loads

	Attributes:
		method: GET, PUT, POST, PATCH, DELETE methods for HTTP call
		url: URL to send the request
		**kwargs:  any other arguments to send to the request
	"""

	def __init__(self, method='GET', url=None, timeout=300.0, **kwargs):
		self.method = method
		self.url = url
		self.params = None
		self.data = None
		self.headers = None
		self.cookies = None
		self.files = None
		self.auth = None
		self.timeout = timeout  # Default 300s (5min) to prevent infinite hangs
		self.allow_redirects = True
		self.proxies = None
		self.hooks = None
		self.stream = None
		self.verify = None
		self.cert = None
		self.json = None
		self.request = None
		self.errors = []
		self.jsonData = {}
		self.args = {}
		self.duration = None
		self.sentUrl = None
		self.sentArgs = None
		for key, value in kwargs.items():
			self.args[key] = value
			setattr(self, key, value)

		if self.url is not None:
			self.runQuery()



	def setArg(self, key, value):
		if value is not None:
			self.args[key] = value

	def runQuery(self):
		self.setArg('params', self.params)
		self.setArg('data', self.data)
		self.setArg('headers', self.headers)
		self.setArg('cookies', self.cookies)
		self.setArg('files', self.files)
		self.setArg('auth', self.auth)
		self.setArg('timeout', self.timeout)
		self.setArg('allow_redirects', self.allow_redirects)
		self.setArg('proxies', self.proxies)
		self.setArg('hooks', self.hooks)
		self.setArg('stream', self.stream)
		self.setArg('verify', self.verify)
		self.setArg('cert', self.cert)
		self.setArg('json', self.json)

		self.errors = []
		self.jsonData = {}
		self.sentUrl = self.url
		self.sentArgs = self.args
		before = utcnow()
		try:
			self.request = requests.request(self.method, self.url, **self.args)
		except Exception as e:
			self.errors.append(str(e))
		else:
			if self.request.status_code not in range(200,300):
				self.errors.append(str(self.request.status_code)+" = "+self.request.reason+"\n"+str(self.request.text))
			try:
				self.jsonData = json.loads(self.request.text)
			except Exception:
				pass
		after = utcnow()
		delta = after - before
		self.duration = delta.total_seconds()
