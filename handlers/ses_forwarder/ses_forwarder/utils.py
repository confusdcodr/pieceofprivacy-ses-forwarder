from enum import Enum


class LookupKey(Enum):
    ITEMS = "Items"
    ITEM = "Item"
    HASH_KEY = "email#domain"
    RANGE_KEY = "destination"


class DedupeKey(Enum):
    ITEM = "Item"
    STATUS = "status"
    UPDATED = "updated"
    HASH_KEY = "message_id"
    CONSUMPTION_COUNT = "consumption_count"


class Status(Enum):
    COMPLETE = "COMPLETE"
    IN_PROGRESS = "IN_PROGRESS"
