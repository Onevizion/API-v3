import requests
import json
from datetime import datetime

class curl(object):
	"""Wrapper for requests.request() that will handle Error trapping and try to give JSON for calling.
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
		if not (url_lower.startswith('http://') or url_lower.startswith('https://')):
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

		self.sentUrl = self.url
		self.sentArgs = self.args
		before = datetime.utcnow()

		# Retry logic for transient failures
		attempt = 0
		last_exception = None

		while attempt <= self.max_retries:
			try:
				# Use session if provided, otherwise use requests module
				if self.session:
					self.request = self.session.request(self.method, self.url, **self.args)
				else:
					self.request = requests.request(self.method, self.url, **self.args)

				# Check if response indicates success or permanent failure
				if self.request.status_code in range(200, 300):
					# Success - parse JSON and exit
					try:
						self.jsonData = json.loads(self.request.text)
					except Exception as err:
						pass
					break
				elif self.request.status_code in range(400, 500):
					# 4xx = client error (permanent) - don't retry
					reason = self.request.reason if self.request.reason else "Unknown"
					self.errors.append(str(self.request.status_code)+" = "+reason+"\n"+str(self.request.text))
					break
				elif self.request.status_code >= 500:
					# 5xx = server error (transient) - retry
					if attempt < self.max_retries:
						import time
						# Close failed response before retrying
						if self.request:
							self.request.close()
						delay = self.retry_backoff * (2 ** attempt)  # Exponential backoff
						time.sleep(delay)
						attempt += 1
						continue
					else:
						# Max retries reached
						reason = self.request.reason if self.request.reason else "Unknown"
						self.errors.append(str(self.request.status_code)+" = "+reason+"\n"+str(self.request.text))
						break

			except (requests.ConnectionError, requests.Timeout) as e:
				# Network errors (transient) - retry
				last_exception = e
				if attempt < self.max_retries:
					import time
					delay = self.retry_backoff * (2 ** attempt)
					time.sleep(delay)
					attempt += 1
					continue
				else:
					# Max retries reached
					self.errors.append(str(e))
					break

			except Exception as e:
				# Other errors - don't retry
				self.errors.append(str(e))
				break

			attempt += 1

		after = datetime.utcnow()
		delta = after - before
		self.duration = delta.total_seconds()

		# Close the final response to free connection resources
		if self.request:
			self.request.close()

