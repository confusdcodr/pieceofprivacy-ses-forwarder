import json
import uuid
from pprint import pprint

import boto3
import pytest
import ses_forwarder.main as handler


def test_delete_sqs(sqs_client, sqs_queue):
    """
    Ensure that you can delete a message from the sqs queue
    """
    # add message to the queue
    sqs_client.send_message(QueueUrl=sqs_queue, MessageBody="example message")

    # retrieve the message from the queue
    queue_message = sqs_client.receive_message(
        QueueUrl=sqs_queue, MaxNumberOfMessages=1
    )
    receipt_handle = queue_message["Messages"][0]["ReceiptHandle"]

    # get the queue_arn
    queue_attributes = sqs_client.get_queue_attributes(
        QueueUrl=sqs_queue, AttributeNames=["QueueArn"]
    )
    queue_arn = queue_attributes["Attributes"]["QueueArn"]

    response = handler.delete_sqs(queue_arn, receipt_handle)
    assert response is None


def test_handler(
    monkeypatch,
    s3_client,
    bucket,
    sqs_client,
    sqs_queue,
):
    """
    Ensure that the handler can take a received message and send an email
    """
    # setup environment variables
    monkeypatch.setenv("LAMBDA_TIMEOUT", "60")
    monkeypatch.setenv("MAIL_SENDER", "from@pieceofprivacy.com")
    monkeypatch.setenv("MAIL_RECIPIENT", "to@pieceofprivacy.com")

    # put example email into the s3 bucket
    key = f"pytest-{uuid.uuid4().hex}"
    with open("handlers/tests/events/test_email.txt", "rb") as f:
        s3_client.put_object(Body=f, Bucket=bucket, Key=key)

    # add message to the queue
    sqs_client.send_message(QueueUrl=sqs_queue, MessageBody="example message")

    # retrieve the message from the queue
    queue_message = sqs_client.receive_message(QueueUrl=sqs_queue)
    receipt_handle = queue_message["Messages"][0]["ReceiptHandle"]
    message_id = queue_message["Messages"][0]["MessageId"]

    # get the queue_arn
    queue_attributes = sqs_client.get_queue_attributes(
        QueueUrl=sqs_queue, AttributeNames=["QueueArn"]
    )
    queue_arn = queue_attributes["Attributes"]["QueueArn"]

    # construct message type for handler
    message = {"receipt": {"action": {"bucketName": bucket, "objectKey": key}}}

    body = {"Message": json.dumps(message)}

    event = {
        "Records": [
            {
                "messageId": message_id,
                "receiptHandle": receipt_handle,
                "eventSourceARN": queue_arn,
                "body": json.dumps(body),
            }
        ]
    }

    response = handler.handler(event, None)
    assert response is None
