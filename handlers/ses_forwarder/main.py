import json
import logging
import os
import re
from time import time

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from ses_forwarder.DedupeSQS import DedupeSQS
from ses_forwarder.S3Email import S3Email
from ses_forwarder.utils import Key, Status

DedupeSQS = DedupeSQS(os.environ["DEDUPE_TABLE"], Key.HASH_KEY.value)
SQS_CLIENT = boto3.resource("sqs")

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


class ProcessingError(Exception):
    pass


def update_sqs_dynamodb(item: dict, status: Status):
    """
    Update the given DynamoDB item's consumption count, status, and updated timestamp

    Args:
        item (dict): the DynamoDB item to be updated, which includes the message ID
        status (Status): the new status to assign to the DynamoDB item

    Raises:
        ProcessingError: [description]
    """
    LAMBDA_TIMEOUT = int(os.environ["LAMBDA_TIMEOUT"])
    LOGGER.info(
        f"Incrementing item consumption count and setting item status to {status}"
    )
    item[Key.CONSUMPTION_COUNT.value] += 1
    item[Key.STATUS.value] = status.value
    item[Key.UPDATED.value] = int(time())

    condition_expression = None
    if status == Status.IN_PROGRESS:
        # status == IN_PROGRESS and updated < time() - lambda_timeout
        condition_expression = Attr(Key.STATUS.value).eq(
            Status.IN_PROGRESS.value
        ) & Attr(Key.UPDATED.value).lt(int(time() - LAMBDA_TIMEOUT))
    elif status == Status.COMPLETE:
        condition_expression = Attr(Key.STATUS.value).eq(Status.IN_PROGRESS.value)

    try:
        DedupeSQS.update_item(item, condition_expression)
    except ClientError as err:
        if status == Status.IN_PROGRESS:
            raise ProcessingError(err)


def process_sns(message: dict):
    """
    Process the SNS message from SQS to send out the email

    Args:
        message (dict): the SNS messsage contained within the SQS record
    """
    bucket = message["receipt"]["action"]["bucketName"]
    key = message["receipt"]["action"]["objectKey"]

    s3_email = S3Email(bucket, key)

    s3_email.extract_headers()
    response = s3_email.send_email()

    response["ResponseMetadata"]["HTTPStatusCode"] == 200


def delete_sqs(queue_arn: str, receipt_handle: str):
    """
    Delete record from the given sqs queue

    Raises:
        err: error occurred during attempt
    """
    LOGGER.info(f"Deleting record {receipt_handle} from {queue_arn}")
    try:
        queue_name = queue_arn.split(":")[-1]
        queue = SQS_CLIENT.get_queue_by_name(QueueName=queue_name)
        message = SQS_CLIENT.Message(queue.url, receipt_handle)
        message.delete()
    except Exception as err:
        LOGGER.error(err)
        raise err


def handler(event: dict, context):
    """
    Lambda entry point method processing messages consumed from SQS

    Args:
        event (dict): the event consumed from SQS
        context ([type]): the context of the event trigger
    """

    LOGGER.debug(f"Event received {json.dumps(event)}")

    for record in event["Records"]:
        message_id = record["messageId"]
        sqs_arn = record["eventSourceARN"]
        receipt_handle = record["receiptHandle"]

        item = DedupeSQS.get_item(message_id)

        # check if sqs record has already been processed
        if item and item[Key.STATUS.value] == Status.COMPLETE.value:
            LOGGER.info(
                f"Corresponding DynamoDB table item with message ID {message_id} marked COMPLETE."
            )
            delete_sqs(sqs_arn, receipt_handle)
            continue
        elif item and item[Key.STATUS.value] == Status.IN_PROGRESS.value:
            update_sqs_dynamodb(item, Status.IN_PROGRESS)
        elif not item:
            LOGGER.info(f"Creating a new DynamoDB item with message ID {message_id}")
            item = DedupeSQS.create_item(message_id)

        # process the sns message within the sqs record
        message = json.loads(record["body"])
        process_sns(json.loads(message["Message"]))

        # sqs record processing is complete
        update_sqs_dynamodb(item, Status.COMPLETE)

        # delete record from the queue
        delete_sqs(sqs_arn, receipt_handle)
