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
import time

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

	def __init__(self, method='GET', url=None, timeout=300.0, max_retries=0, retry_backoff=1.0, session=None, **kwargs):
		self.method = method
		self.url = url
		self.params = None
		self.data = None
		self.headers = None
		self.cookies = None
		self.files = None
		self.auth = None
		self.timeout = timeout  # Default 300s (5min) to prevent infinite hangs
		self.max_retries = max_retries  # Number of retries for transient failures
		self.retry_backoff = retry_backoff  # Base delay for exponential backoff
		self.session = session  # Optional requests.Session() for connection pooling
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

	def _validate_inputs(self):
		"""Validate inputs for security and correctness.

		Returns True if validation passes, False otherwise.
		Errors are appended to self.errors.
		"""
		# Validate URL
		if not self.url:
			self.errors.append("URL is required and cannot be empty")
			return False

		# Validate URL protocol (security: prevent javascript:, file:, data: etc.)
		url_lower = str(self.url).lower()
		if not url_lower.startswith(('http://', 'https://')):
			self.errors.append("URL protocol must be http:// or https://. Got: {url}".format(url=self.url))
			return False

		# Validate HTTP method
		valid_methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
		if self.method.upper() not in valid_methods:
			self.errors.append("Invalid HTTP method: {method}. Must be one of: {valid}".format(
				method=self.method,
				valid=', '.join(valid_methods)
			))
			return False

		# Validate timeout (must be positive)
		if self.timeout is not None:
			try:
				timeout_val = float(self.timeout)
				if timeout_val <= 0:
					self.errors.append("Timeout must be positive. Got: {timeout}".format(timeout=self.timeout))
					return False
			except (TypeError, ValueError):
				self.errors.append("Timeout must be a number. Got: {timeout}".format(timeout=self.timeout))
				return False

		# Validate max_retries (must be non-negative)
		if self.max_retries is not None:
			try:
				retries_val = int(self.max_retries)
				if retries_val < 0:
					self.errors.append("Max retries must be non-negative. Got: {retries}".format(retries=self.max_retries))
					return False
			except (TypeError, ValueError):
				self.errors.append("Max retries must be an integer. Got: {retries}".format(retries=self.max_retries))
				return False

		return True

	def runQuery(self):
		# Clear previous errors and jsonData
		self.errors = []
		self.jsonData = {}

		# Validate inputs before making request
		if not self._validate_inputs():
			# Validation failed, errors already set
			return

		# Build args dictionary from instance attributes
		for attr in ('params', 'data', 'headers', 'cookies', 'files', 'auth',
		             'timeout', 'allow_redirects', 'proxies', 'hooks', 'stream',
		             'verify', 'cert', 'json'):
			self.setArg(attr, getattr(self, attr))

		self.sentUrl = self.url
		self.sentArgs = self.args
		before = utcnow()

		# Retry logic for transient failures
		attempt = 0

		while attempt <= self.max_retries:
			try:
				# Use session if provided, otherwise use requests module
				requester = self.session if self.session else requests
				self.request = requester.request(self.method, self.url, **self.args)

				# Check if response indicates success or permanent failure
				if self.request.status_code in range(200, 300):
					# Success - parse JSON and exit
					try:
						self.jsonData = json.loads(self.request.text)
					except Exception:
						pass
					break
				if self.request.status_code in range(300, 400):
					# 3xx redirect - either handled by requests or error if allow_redirects=False
					# Treat as permanent failure (should have been auto-handled)
					self._append_http_error()
					break
				if self.request.status_code in range(400, 500):
					# 4xx = client error (permanent) - don't retry
					self._append_http_error()
					break
				if self.request.status_code >= 500:
					# 5xx = server error (transient) - retry
					if attempt < self.max_retries:
						# Close failed response before retrying
						if self.request:
							self.request.close()
						self._sleep_with_backoff(attempt)
						attempt += 1
						continue
					# Max retries reached
					self._append_http_error()
					break

			except (requests.ConnectionError, requests.Timeout) as e:
				# Network errors (transient) - retry
				if attempt < self.max_retries:
					self._sleep_with_backoff(attempt)
					attempt += 1
					continue
				# Max retries reached
				self.errors.append(str(e))
				break

			except Exception as e:
				# Other errors - don't retry
				self.errors.append(str(e))
				break

		after = utcnow()
		delta = after - before
		self.duration = delta.total_seconds()

		# Close the final response to free connection resources
		if self.request:
			self.request.close()

	def _append_http_error(self):
		"""Append HTTP error message from response."""
		reason = self.request.reason if self.request.reason else "Unknown"
		self.errors.append(str(self.request.status_code)+" = "+reason+"\n"+str(self.request.text))

	def _sleep_with_backoff(self, attempt):
		"""Sleep with exponential backoff."""
		delay = self.retry_backoff * (2 ** attempt)
		time.sleep(delay)

