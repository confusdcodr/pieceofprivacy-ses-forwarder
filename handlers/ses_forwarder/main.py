import json
import logging
import os
import re
from time import time

import boto3
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
from ses_forwarder.LookupDestination import LookupDestination
from ses_forwarder.S3Email import S3Email
from ses_forwarder.utils import LookupKey, Status

LookupDestination = LookupDestination(
    os.environ["LOOKUP_TABLE"], LookupKey.HASH_KEY.value, LookupKey.RANGE_KEY.value
)
SQS_CLIENT = boto3.resource("sqs")

LOGGER = logging.getLogger()
LOGGER.setLevel(logging.INFO)


class ProcessingError(Exception):
    pass

def process_sns(message: dict):
    """
    Process the SNS message from SQS to send out the email

    Args:
        message (dict): the SNS messsage contained within the SQS record
    """
    bucket = message["receipt"]["action"]["bucketName"]
    key = message["receipt"]["action"]["objectKey"]

    s3_email = S3Email(bucket, key)

    orig_to_domain = s3_email.orig_to.split("@")[1]

    destinations = LookupDestination.lookup_destination(s3_email.orig_to)

    # if destination(s) are already defined then add them to the email
    if destinations:
        for destination in destinations:
            s3_email.add_forward_to(destination["destination"])
    # if destination(s) aren't defined, lookup the catch all destination
    else:
        catch_all = LookupDestination.lookup_destination(f"*@{orig_to_domain}")
        s3_email.add_forward_to(catch_all[0]["destination"])

    # send email
    response = s3_email.send_email()

    return response


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


def main(event: dict):
    """
    Lambda entry point method processing messages consumed from SQS

    Args:
        event (dict): the event consumed from SQS
    """
    LOGGER.debug(f"Event received {json.dumps(event)}")

    for record in event["Records"]:
        sqs_arn = record["eventSourceARN"]
        receipt_handle = record["receiptHandle"]

        # process the sns message within the sqs record
        message = json.loads(record["body"])
        response = process_sns(json.loads(message["Message"]))

        if response["ResponseMetadata"]["HTTPStatusCode"] == 200:
            # delete record from the queue
            delete_sqs(sqs_arn, receipt_handle)


def handler(event: dict, context):
    main(event)


if __name__ == "__main__":
    # quick mechanism to debug broken emails
    sns_message = {
        "receipt": {"action": {"bucketName": "[bucket]", "objectKey": "[key]"}}
    }

    process_sns(sns_message)
