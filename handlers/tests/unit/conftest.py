import uuid
from time import sleep

import boto3
import pytest
from ses_forwarder.ses_forwarder.DedupeSQS import DedupeSQS
from ses_forwarder.ses_forwarder.LookupDestination import LookupDestination
from ses_forwarder.ses_forwarder.S3Email import S3Email


@pytest.fixture()
def ddb_resource():
    return boto3.resource("dynamodb")


@pytest.fixture()
def dedupe_table(ddb_resource):
    table_name = uuid.uuid4().hex
    table = ddb_resource.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {"AttributeName": "message_id", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "message_id", "KeyType": "HASH"},
        ],
        BillingMode="PROVISIONED",
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    sleep(10)
    yield table_name
    table.delete()


@pytest.fixture()
def lookup_table(ddb_resource):
    table_name = uuid.uuid4().hex
    table = ddb_resource.create_table(
        TableName=table_name,
        AttributeDefinitions=[
            {"AttributeName": "email#domain", "AttributeType": "S"},
            {"AttributeName": "destination", "AttributeType": "S"},
        ],
        KeySchema=[
            {"AttributeName": "email#domain", "KeyType": "HASH"},
            {"AttributeName": "destination", "KeyType": "RANGE"},
        ],
        BillingMode="PROVISIONED",
        ProvisionedThroughput={"ReadCapacityUnits": 5, "WriteCapacityUnits": 5},
    )
    sleep(10)
    yield table_name
    table.delete()


@pytest.fixture()
def dedupe_sqs(dedupe_table):
    return DedupeSQS(dedupe_table, "message_id")


@pytest.fixture()
def lookup_email(lookup_table):
    return LookupDestination(lookup_table, "email#domain", "destination")


@pytest.fixture()
def s3_client():
    return boto3.client("s3")


@pytest.fixture()
def bucket(s3_client):
    # Create bucket
    bucket = f"pytest-{uuid.uuid4().hex}"
    response = s3_client.create_bucket(Bucket=bucket)
    yield response["ResponseMetadata"]["HTTPHeaders"]["location"][1:]
    s3 = boto3.resource("s3")
    s3.Bucket(bucket).objects.all().delete()
    s3_client.delete_bucket(Bucket=bucket)


@pytest.fixture
def s3_email(s3_client, bucket):
    # upload example email
    key = f"pytest-{uuid.uuid4().hex}"
    with open("handlers/tests/events/test_email.txt", "rb") as f:
        s3_client.put_object(Body=f, Bucket=bucket, Key=key)

    return S3Email(bucket, key)


@pytest.fixture()
def sqs_client():
    return boto3.client("sqs")


@pytest.fixture()
def sqs_queue(sqs_client):
    queue_name = f"pytest-{uuid.uuid4().hex}"
    response = sqs_client.create_queue(QueueName=queue_name)
    yield response["QueueUrl"]
    sqs_client.delete_queue(QueueUrl=response["QueueUrl"])
