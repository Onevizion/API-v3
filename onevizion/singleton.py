from onevizion.util import *
import os
import sys
import onevizion

class Singleton(object):
	""" Make sure this process is only running once.  It does a quiet quit() if it's already running.
		* May use any Lockfile name you like, default is ScriptName.lck.
		* May choose what happens if a process collision happens
			"silent" - exit with normal quit
			"error" - exit with error signal
			"none" - do nothing but set property to check, for custom things
		* May set custom Quit Message.

		This was mostly taken from the tendo library, releassed under the Python License allowing derivations
		https://github.com/pycontribs/tendo/blob/master/tendo/singleton.py
		My reason for creating this offshoot was because the tendo version forces any error code -1 exit,
		which does not work for my purposes.
	"""
	def __init__(self,LockFileName=None,QuitMode="silent",Msg="Previous process Still Running.  Quitting."):
		""" LockFileName - can be specified, or if left blank, it will default to ScriptName.lck
			QuitMode - determines how to respond to finding an already running process. Possible Options are:
				"silent" - exit silently with no error code.
				"error" - exit with error code -1
				"none" - set property and continue running
			Msg - Allows for a custom Message to be sent to console
		"""
		def Quit():
			"""Handle Quitting (or not) as specified
			"""
			if Msg is not None and Msg != "":
				Message(Msg)
			self.foundProcess = True
			if QuitMode.lower() == "silent":
				quit()
			elif QuitMode.lower() == "error":
				sys.exit(-1)


		self.initialized = False
		self.foundProcess = False
		self.platform = onevizion.Config["Platform"]
		if self.platform != 'win32':
			import fcntl
		# Choose Filename for Lock File
		if LockFileName is None:
			import __main__
			self.LockFileName = __main__.__file__[:-3]+".lck"
		else:
			self.LockFileName = LockFileName
		# Make Sure this script is not still running from last time before we run
		if self.platform == 'win32':
			try:
				# file already exists, we try to remove (in case previous
				# execution was interrupted)
				if os.path.exists(self.LockFileName):
					os.unlink(self.LockFileName)
				self.LockFile = os.open(
					self.LockFileName, os.O_CREAT | os.O_EXCL | os.O_RDWR)
			except OSError:
				type, e, tb = sys.exc_info()
				if e.errno == 13:
					Quit()
		else:  # non Windows
			import fcntl
			self.LockFile = open(self.LockFileName, 'w')
			self.LockFile.flush()
			try:
				fcntl.lockf(self.LockFile, fcntl.LOCK_EX | fcntl.LOCK_NB)
			except IOError:
				Quit()
		self.initialized = True

	def __del__(self):
		# Clean up File on Exit
		if not self.initialized:
			return
		try:
			if self.platform == 'win32':
				if hasattr(self, 'LockFile'):
					os.close(self.LockFileName)
					os.unlink(self.LockFileName)
			else:
				fcntl.lockf(self.LockFile, fcntl.LOCK_UN)
				# os.close(self.fp)
				if os.path.isfile(self.LockFileName):
					os.unlink(self.LockFileName)
		except Exception as e:
			Message("Unknown error: %s" % e)
			sys.exit(-1)
