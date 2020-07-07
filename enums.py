from enum import Enum


class Success(Enum):
    early = 1  # wait_time must be adjusted up
    late = -1  # wait_time must be adjusted down
    success = 0  # wait_time does not need to be adjusted
    pending = 2  # not yet known whether successful


class Actor(Enum):
    model = 0
    player = 1
