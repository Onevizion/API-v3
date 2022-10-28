from enum import Enum

class NotifQueueStatus(Enum):
	BUILDING = 0
	NOT_SENT = 1
	SENDING = 2
	FAIL_WILL_RETRY = 3
	FAIL = 4
	SUCCESS = 5
