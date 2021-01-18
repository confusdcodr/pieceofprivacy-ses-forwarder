import logging
from time import time

from boto3 import resource
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError

from .utils import Key, Status

LOGGER = logging.getLogger()

LOGGER.setLevel(logging.INFO)


class DedupeSQS:
    def __init__(self, table_name: str, hash_key: str):
        LOGGER.info(
            f"Setting up DynamoDB resource for table '{table_name}' with hash key '{hash_key}'"
        )
        dynamodb = resource("dynamodb")

        try:
            self.hash_key = hash_key
            self.table = dynamodb.Table(name=table_name)
        except ClientError as err:
            LOGGER.error(err)
            raise err

    def create_item(self, message_id) -> dict:
        item = {
            Key.HASH_KEY.value: message_id,
            Key.CONSUMPTION_COUNT.value: 1,
            Key.STATUS.value: Status.IN_PROGRESS.value,
            Key.UPDATED.value: int(time()),
        }

        condition_expression = Attr(Key.HASH_KEY.value).not_exists()

        self.update_item(item, condition_expression)
        return item

    def get_item(self, partition_key_value: str) -> dict:
        LOGGER.info(
            f"Querying table '{self.table.table_name}' for item with hash value '{partition_key_value}'"
        )
        try:
            response = self.table.get_item(
                Key={self.hash_key: partition_key_value}, ConsistentRead=True
            )

            if Key.ITEM.value in response:
                return response[Key.ITEM.value]
        except ClientError as err:
            LOGGER.error(err)
            raise err

    def update_item(self, item: dict, condition_expression: Attr = None) -> dict:
        try:
            hash_value = item[self.hash_key]

            LOGGER.info(
                f"Putting item with hash value '{hash_value}' into table '{self.table}'"
            )
            return self.table.put_item(
                Item=item, ConditionExpression=condition_expression
            )
        except (ClientError, KeyError) as err:
            LOGGER.error(err)
            raise err
