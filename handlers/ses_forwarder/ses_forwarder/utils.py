from enum import Enum


class Key(Enum):
    CONSUMPTION_COUNT = "consumption_count"
    ITEM = "Item"
    HASH_KEY = "message_id"
    STATUS = "status"
    UPDATED = "updated"


class Status(Enum):
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETE = "COMPLETE"
