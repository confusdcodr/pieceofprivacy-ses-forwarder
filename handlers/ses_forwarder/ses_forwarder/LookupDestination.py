import logging
from time import time
from typing import List

from boto3 import resource
from boto3.dynamodb.conditions import Attr, Key
from botocore.exceptions import ClientError

from .utils import LookupKey, Status

LOGGER = logging.getLogger()

LOGGER.setLevel(logging.INFO)


class LookupDestination:
    def __init__(self, table_name: str, hash_key: str, range_key: str):
        LOGGER.info(
            f"Setting up DynamoDB resource for table '{table_name}' with hash key '{hash_key}' and range key '{range_key}'"
        )
        dynamodb = resource("dynamodb")

        try:
            self.hash_key = hash_key
            self.range_key = range_key
            self.table = dynamodb.Table(name=table_name)
        except ClientError as err:
            LOGGER.error(err)
            raise err

    def lookup_destination(self, partition_key_value: str) -> dict:
        LOGGER.info(
            f"Querying table '{self.table.table_name}' for item with hash value '{partition_key_value}'"
        )
        try:
            response = self.table.query(
                KeyConditionExpression=Key(self.hash_key).eq(partition_key_value),
                ConsistentRead=True,
            )

            if LookupKey.ITEMS.value in response:
                return response[LookupKey.ITEMS.value]
        except ClientError as err:
            LOGGER.error(err)
            raise err

    def add_destination(self, item: dict) -> dict:
        try:
            hash_value = item[self.hash_key]

            LOGGER.info(
                f"Putting item with hash value '{hash_value}' into table '{self.table}'"
            )
            response = self.table.put_item(
                Item=item,
                ReturnValues="ALL_OLD",
            )

            return response
        except (ClientError, KeyError) as err:
            LOGGER.error(err)
            raise err
