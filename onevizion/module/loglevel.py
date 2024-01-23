from enum import Enum
class LogLevel(Enum):
	"""Enum contains possible log levels, as well as a static method to get the log level by name.

	In method 'getLogLevelByName' an exception is thrown if the log level is not found.
	"""
	
	ERROR = (0, "Error")
	WARNING = (1, "Warning")
	INFO = (2, "Info")
	DEBUG = (3, "Debug")

	def __init__(self, logLevelId, logLevelName):
		self.logLevelId = logLevelId
		self.logLevelName = logLevelName
	
	@staticmethod
	def getLogLevelByName(ovLogLevelName):
		for logLevel in list(LogLevel):
			if logLevel.logLevelName.upper() == ovLogLevelName.upper():
				return logLevel
		raise Exception("Cannot find the log level called '{}'".format(ovLogLevelName))
